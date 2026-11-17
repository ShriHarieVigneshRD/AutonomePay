from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.api.scenarios import get_all_50_formatted_scenarios
from app.core.database import EvaluationBatch, EvaluationRun, get_db
from app.evals.dataset import generate_50_synthetic_cases
from app.evals.langsmith_sync import sync_dataset_to_langsmith
from app.evals.runner import compute_kpis, create_batch, execute_batch_evaluation_job, run_guardrail_status

router = APIRouter()


def _batch_summary(b: EvaluationBatch) -> dict:
    return {
        "batch_id": b.batch_id,
        "name": b.name,
        "status": b.status,
        "total_cases": b.total_cases,
        "completed_cases": b.completed_cases,
        "created_at": b.created_at.isoformat() if b.created_at else None,
    }


def _float(value) -> float | None:
    return float(value) if value is not None else None


@router.post("/evals/sync-langsmith", dependencies=[Depends(require_admin)])
def sync_langsmith():
    return sync_dataset_to_langsmith()


@router.get("/evals/batches")
def get_all_batches(db: Session = Depends(get_db)):
    batches = db.query(EvaluationBatch).order_by(EvaluationBatch.created_at.desc()).all()
    return [{**_batch_summary(b), "kpis": b.kpis} for b in batches]


@router.post("/evals/run", dependencies=[Depends(require_admin)])
def trigger_batch_evals(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if db.query(EvaluationBatch).filter(EvaluationBatch.status == "RUNNING").first():
        raise HTTPException(status_code=409, detail="A benchmark run is already in progress.")
    batch = create_batch(db, total_cases=len(generate_50_synthetic_cases()))
    background_tasks.add_task(execute_batch_evaluation_job, batch.batch_id)
    return {**_batch_summary(batch), "status": "RUNNING"}


@router.get("/evals/results")
def get_eval_results(batch_id: str | None = Query(None), db: Session = Depends(get_db)):
    if batch_id:
        target_batch = db.get(EvaluationBatch, batch_id)
        if not target_batch:
            raise HTTPException(status_code=404, detail="Benchmark run not found.")
    else:
        target_batch = db.query(EvaluationBatch).order_by(EvaluationBatch.created_at.desc()).first()
        if not target_batch:
            raise HTTPException(status_code=404, detail="No benchmark runs yet.")

    runs = db.query(EvaluationRun).filter(EvaluationRun.batch_id == target_batch.batch_id).all()
    greetings = {s["id"]: s["initial_message"] for s in get_all_50_formatted_scenarios(db)}
    matrix = [
        {
            "run_id": r.run_id,
            "test_id": r.test_id,
            "scenario_type": r.scenario_type,
            "turns": r.total_turns,
            "outcome": r.final_agent_outcome,
            "final_action": r.final_action,
            "expected_action": r.expected_action,
            "passed": r.passed,
            "guardrail_status": run_guardrail_status(r),
            "rag_faithfulness": float(r.rag_faithfulness or 0.0),
            "invoice_inr": _float(r.invoice_amount),
            "recovered_inr": float(r.link_amount or 0.0),
            "latency_ms": _float(r.latency_ms),
            "tokens_used": r.tokens_used,
            "langsmith_trace_url": r.langsmith_trace_url,
            "initial_message": greetings.get(r.test_id, ""),
            "execution_trace": r.execution_trace,
        }
        for r in sorted(runs, key=lambda r: r.test_id)
    ]
    kpi = (
        target_batch.kpis if target_batch.status == "COMPLETED" and target_batch.kpis else compute_kpis(runs)
    )
    return {"batch": _batch_summary(target_batch), "kpi": kpi, "matrix": matrix}
