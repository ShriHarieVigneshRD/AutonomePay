import logging
import time
import uuid
from datetime import datetime
from statistics import mean
from typing import Any

try:
    from langsmith import traceable
except ImportError:  # langsmith is optional

    def traceable(*_args, **_kwargs):
        def decorator(func):
            return func

        return decorator


from sqlalchemy.orm import Session

from app.agents.graph import autonomepay_graph
from app.agents.state import build_initial_state
from app.core.config import settings
from app.core.database import EvaluationBatch, EvaluationRun, SessionLocal
from app.evals.dataset import generate_50_synthetic_cases, score_case
from app.evals.judge import evaluate_rag_triad

logger = logging.getLogger(__name__)


def run_guardrail_status(run: EvaluationRun) -> str:
    if run.adversarial_intercepted:
        return "ADVERSARIAL_INTERCEPTED"
    return "POLICY_BREACH_CORRECTED" if run.policy_breach else "PASSED"


def create_batch(db: Session, total_cases: int = 50) -> EvaluationBatch:
    count = db.query(EvaluationBatch).count()
    batch = EvaluationBatch(
        batch_id=f"batch_{uuid.uuid4().hex[:12]}",
        name=f"Run #{count + 1} ({datetime.now().strftime('%d %b %H:%M')})",
        status="RUNNING",
        total_cases=total_cases,
        completed_cases=0,
    )
    db.add(batch)
    db.commit()
    return batch


def compute_kpis(runs: list[EvaluationRun]) -> dict[str, Any]:
    """Every figure is measured from stored runs; None means "not measured" (e.g. pre-upgrade rows)."""
    latencies = [float(r.latency_ms) for r in runs if r.latency_ms is not None]
    faithfulness = [float(r.rag_faithfulness) for r in runs if r.rag_faithfulness is not None]
    scored = [r for r in runs if r.passed is not None]
    return {
        "total_invoiced": round(sum(float(r.invoice_amount or 0) for r in runs), 2),
        "total_recovered": round(sum(float(r.link_amount or 0) for r in runs), 2),
        "links_issued": sum(1 for r in runs if r.link_amount),
        "policy_breaches": sum(1 for r in runs if r.policy_breach),
        "adversarial_intercepts": sum(1 for r in runs if r.adversarial_intercepted),
        "rag_faithfulness_pct": round(mean(faithfulness) * 100, 1) if faithfulness else None,
        "avg_latency_ms": round(mean(latencies), 1) if latencies else None,
        "tokens_used": sum(r.tokens_used or 0 for r in runs),
        "pass_rate_pct": round(100 * sum(1 for r in scored if r.passed) / len(scored), 1) if scored else None,
    }


def _langsmith_url() -> str | None:
    """URL of the LangSmith run for this case, when tracing is on (never fabricated)."""
    if not settings.langsmith_enabled:
        return None
    try:
        from langsmith.run_helpers import get_current_run_tree

        run = get_current_run_tree()
        return run.get_url() if run else None
    except Exception:
        logger.debug("LangSmith run URL unavailable", exc_info=True)
        return None


def mark_interrupted_batches() -> None:
    """Batches still RUNNING at startup were killed with the previous process."""
    with SessionLocal() as db:
        for batch in db.query(EvaluationBatch).filter(EvaluationBatch.status == "RUNNING"):
            batch.status = "INTERRUPTED"
        db.commit()


@traceable(name="autonomepay_multi_turn_simulation")
def run_single_simulation_case(case: dict[str, Any], batch_id: str | None = None) -> dict[str, Any]:
    """Play one scripted multi-turn dialogue through the agent graph and store the run."""
    dialogue = case.get("dialogue_script", [])
    merchant_id = case.get("merchant_id", "hotstar")
    scenario_id = case.get("scenario_id", "eval_01")
    scenario_type = case.get("scenario_type", "HOTSTAR_BUDGET_FRICTION")

    messages: list[dict[str, str]] = []
    execution_trace = []
    final_state: dict[str, Any] = {}
    tokens_used = 0
    retrieved: list[str] = []  # passages from every turn, for the case's `source` expectation

    for turn_idx, user_turn in enumerate(dialogue, start=1):
        messages.append({"role": "user", "content": user_turn})
        initial_state = build_initial_state(
            session_id=f"eval_{batch_id or 'batch'}_{scenario_id}_{uuid.uuid4().hex[:6]}",
            messages=list(messages),
            merchant_id=merchant_id,
            merchant_name=merchant_id.replace("_", " ").title(),
            customer_id=case.get("customer_id", "cust_test"),
            customer_name="Test Customer",
            invoice_id=case.get("invoice_id", "inv_test"),
            original_amount=case.get("original_amount", 299.00),
            failure_code=case.get("failure_code", "INSUFFICIENT_FUNDS"),
        )

        start_t = time.time()
        final_state = autonomepay_graph.invoke(initial_state)
        elapsed = round((time.time() - start_t) * 1000, 2)

        tokens_used += final_state.get("tokens_used", 0)
        retrieved += final_state.get("retrieved_policy_chunks", [])
        bot_response = final_state.get("final_response", "")
        messages.append({"role": "assistant", "content": bot_response})
        execution_trace.append(
            {
                "turn": turn_idx,
                "user": user_turn,
                "agent": bot_response,
                "guardrail_status": final_state.get("guardrail_status"),
                "action": final_state.get("action"),
                "sources": [s["source"] for s in final_state.get("retrieved_sources", [])],
                "latency_ms": elapsed,
            }
        )

    triad = evaluate_rag_triad(
        query=dialogue[-1] if dialogue else "",
        retrieved_chunks=final_state.get("retrieved_policy_chunks", []),
        response_text=final_state.get("final_response", ""),
        proposed_offer=final_state.get("proposed_offer", {}),
    )
    payload = final_state.get("razorpay_payload") or {}
    recovered = float(payload.get("amount_in_inr", 0.0)) if payload.get("success") else 0.0
    guard_status = final_state.get("guardrail_status", "PASSED")
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    langsmith_trace_url = _langsmith_url()
    avg_latency = round(mean(t["latency_ms"] for t in execution_trace), 2) if execution_trace else None

    with SessionLocal() as db:
        db.add(
            EvaluationRun(
                run_id=run_id,
                batch_id=batch_id,
                test_id=scenario_id,
                scenario_type=scenario_type,
                total_turns=len(dialogue),
                rag_context_relevance=triad["rag_context_relevance"],
                rag_faithfulness=triad["rag_faithfulness"],
                rag_answer_relevance=triad["rag_answer_relevance"],
                policy_breach=(guard_status == "POLICY_BREACH_CORRECTED"),
                adversarial_intercepted=(guard_status == "ADVERSARIAL_INTERCEPTED"),
                final_agent_outcome=final_state.get("step", "COMPLETED"),
                amount_recovered=recovered,
                langsmith_trace_url=langsmith_trace_url,
                execution_trace=execution_trace,
                invoice_amount=case.get("original_amount"),
                link_amount=recovered or None,
                latency_ms=avg_latency,
                tokens_used=tokens_used,
                final_action=final_state.get("action"),
                expected_action=case.get("expected_action"),
                passed=score_case(case, final_state, retrieved) if "expected" in case else None,
            )
        )
        db.commit()

    return {
        "run_id": run_id,
        "batch_id": batch_id,
        "scenario_id": scenario_id,
        "merchant_id": merchant_id,
        "scenario_type": scenario_type,
        "turns": len(dialogue),
        "guardrail_status": guard_status,
        "rag_triad": triad,
        "recovered_inr": recovered,
        "langsmith_trace_url": langsmith_trace_url,
        "execution_trace": execution_trace,
    }


def execute_batch_evaluation_job(batch_id: str) -> None:
    """Background worker: run every benchmark case for a batch, updating progress as it goes."""
    cases = generate_50_synthetic_cases()
    with SessionLocal() as db:
        batch = db.get(EvaluationBatch, batch_id)
        if not batch:
            return
        batch.total_cases = len(cases)
        db.commit()

    for idx, case in enumerate(cases, start=1):
        try:
            run_single_simulation_case(case, batch_id=batch_id)
        except Exception:
            logger.exception("Case %s failed in batch %s", case.get("scenario_id"), batch_id)
        with SessionLocal() as db:
            batch = db.get(EvaluationBatch, batch_id)
            if batch:
                batch.completed_cases = idx
                db.commit()

    with SessionLocal() as db:
        batch = db.get(EvaluationBatch, batch_id)
        if batch:
            runs = db.query(EvaluationRun).filter(EvaluationRun.batch_id == batch_id).all()
            batch.status = "COMPLETED"
            batch.kpis = compute_kpis(runs)
            db.commit()
