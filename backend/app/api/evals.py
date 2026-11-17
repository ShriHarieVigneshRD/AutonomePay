from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.api.scenarios import get_all_50_formatted_scenarios
from app.core.database import EvaluationBatch, EvaluationRun, get_db
from app.evals.dataset import BATCH_COUNT, generate_50_synthetic_cases
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
        "case_batch": b.case_batch,
        "code_version": b.code_version,
    }


def _float(value) -> float | None:
    return float(value) if value is not None else None


def _matrix(runs: list[EvaluationRun], db: Session) -> list[dict]:
    greetings = {s["id"]: s["initial_message"] for s in get_all_50_formatted_scenarios(db)}
    return [
        {
            "run_id": r.run_id,
            "batch_id": r.batch_id,
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


@router.post("/evals/sync-langsmith", dependencies=[Depends(require_admin)])
def sync_langsmith():
    return sync_dataset_to_langsmith()


@router.get("/evals/batches")
def get_all_batches(db: Session = Depends(get_db)):
    batches = db.query(EvaluationBatch).order_by(EvaluationBatch.created_at.desc()).all()
    return [{**_batch_summary(b), "kpis": b.kpis} for b in batches]


@router.post("/evals/run", dependencies=[Depends(require_admin)])
def trigger_batch_evals(
    background_tasks: BackgroundTasks,
    batch: int | None = Query(None, ge=1, le=BATCH_COUNT, description="Case batch 1-5; omit for all cases"),
    db: Session = Depends(get_db),
):
    if db.query(EvaluationBatch).filter(EvaluationBatch.status == "RUNNING").first():
        raise HTTPException(status_code=409, detail="A benchmark run is already in progress.")
    cases = [c for c in generate_50_synthetic_cases() if batch in (None, c["batch"])]
    run = create_batch(db, total_cases=len(cases), case_batch=batch)
    background_tasks.add_task(execute_batch_evaluation_job, run.batch_id)
    return {**_batch_summary(run), "status": "RUNNING"}


@router.get("/evals/latest")
def get_latest_results(db: Session = Depends(get_db)):
    """The most recent result for every case, across all runs: the scorecard batches build up."""
    latest: dict[str, EvaluationRun] = {}
    for r in (
        db.query(EvaluationRun).filter(EvaluationRun.batch_id.isnot(None)).order_by(EvaluationRun.created_at)
    ):
        latest[r.test_id] = r
    runs = list(latest.values())
    batch_ids = {r.batch_id for r in runs}
    batches = db.query(EvaluationBatch).filter(EvaluationBatch.batch_id.in_(batch_ids)).all() if runs else []
    return {
        "kpi": compute_kpis(runs),
        "matrix": _matrix(runs, db),
        "coverage": {"evaluated": len(runs), "total": len(generate_50_synthetic_cases())},
        "code_versions": sorted({b.code_version for b in batches if b.code_version}),
        "running": db.query(EvaluationBatch).filter(EvaluationBatch.status == "RUNNING").count() > 0,
    }


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
    matrix = _matrix(runs, db)
    kpi = (
        target_batch.kpis if target_batch.status == "COMPLETED" and target_batch.kpis else compute_kpis(runs)
    )
    return {"batch": _batch_summary(target_batch), "kpi": kpi, "matrix": matrix}
