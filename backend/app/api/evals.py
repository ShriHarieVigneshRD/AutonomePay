from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from app.api.scenarios import get_all_50_formatted_scenarios
from app.core.database import EvaluationBatch, EvaluationRun, get_db
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


@router.post("/evals/sync-langsmith")
def sync_langsmith():
    return sync_dataset_to_langsmith()


@router.get("/evals/batches")
def get_all_batches(db: Session = Depends(get_db)):
    batches = db.query(EvaluationBatch).order_by(EvaluationBatch.created_at.desc()).all()
    if not batches:
        # Existing behaviour: an empty database runs a first benchmark synchronously.
        execute_batch_evaluation_job(create_batch(db).batch_id)
        batches = db.query(EvaluationBatch).order_by(EvaluationBatch.created_at.desc()).all()
    return [{**_batch_summary(b), "kpis": b.kpis} for b in batches]


@router.post("/evals/run")
def trigger_batch_evals(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    batch = create_batch(db)
    background_tasks.add_task(execute_batch_evaluation_job, batch.batch_id)
    return {
        "batch_id": batch.batch_id,
        "name": batch.name,
        "status": "RUNNING",
        "total_cases": 50,
        "completed_cases": 0,
    }


@router.get("/evals/results")
def get_eval_results(batch_id: str | None = Query(None), db: Session = Depends(get_db)):
    target_batch = db.get(EvaluationBatch, batch_id) if batch_id else None
    if not target_batch:
        target_batch = db.query(EvaluationBatch).order_by(EvaluationBatch.created_at.desc()).first()
    if not target_batch:
        new_batch_id = create_batch(db).batch_id
        execute_batch_evaluation_job(new_batch_id)
        db.expire_all()
        target_batch = db.get(EvaluationBatch, new_batch_id)
    assert target_batch is not None

    runs = db.query(EvaluationRun).filter(EvaluationRun.batch_id == target_batch.batch_id).all()
    greetings = {s["id"]: s["initial_message"] for s in get_all_50_formatted_scenarios()}
    matrix = [
        {
            "run_id": r.run_id,
            "test_id": r.test_id,
            "scenario_type": r.scenario_type,
            "turns": r.total_turns,
            "outcome": r.final_agent_outcome,
            "guardrail_status": run_guardrail_status(r),
            "rag_faithfulness": float(r.rag_faithfulness or 1.0),
            "recovered_inr": float(r.amount_recovered or 0.0),
            "langsmith_trace_url": r.langsmith_trace_url,
            "initial_message": greetings.get(r.test_id, ""),
            "execution_trace": r.execution_trace,
        }
        for r in runs
    ]
    return {
        "batch": _batch_summary(target_batch),
        "kpi": target_batch.kpis or compute_kpis(runs),
        "matrix": matrix,
    }
