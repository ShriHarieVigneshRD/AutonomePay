import uuid
import time
import logging
from typing import List, Dict, Any

try:
    from langsmith import traceable
except ImportError:
    def traceable(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

from app.agents import autonomepay_graph
from app.evals.dataset_generator import generate_50_synthetic_cases
from app.evals.judge import evaluate_rag_triad
from app.core.database import SessionLocal, EvaluationRun

logger = logging.getLogger("simulation_runner")

@traceable(name="autonomepay_multi_turn_simulation")
def run_single_simulation_case(case: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes a multi-turn simulation run for a single synthetic test case.
    """
    dialogue = case.get("dialogue_script", [])
    merchant_id = case.get("merchant_id", "hotstar")
    scenario_id = case.get("scenario_id", "eval_01")
    scenario_type = case.get("scenario_type", "HOTSTAR_BUDGET_FRICTION")

    messages = []
    execution_trace = []
    final_state = None

    for turn_idx, user_turn in enumerate(dialogue, start=1):
        messages.append({"role": "user", "content": user_turn})
        
        initial_state = {
            "messages": messages,
            "merchant_id": merchant_id,
            "merchant_name": merchant_id.replace("_", " ").title(),
            "customer_id": case.get("customer_id", "cust_test"),
            "customer_name": "Test Customer",
            "invoice_id": case.get("invoice_id", "inv_test"),
            "original_amount": case.get("original_amount", 299.00),
            "failure_code": case.get("failure_code", "INSUFFICIENT_FUNDS"),
            "customer_intent": "",
            "retrieved_policy_chunks": [],
            "guardrail_status": "PASSED",
            "guardrail_violations": [],
            "proposed_offer": {},
            "razorpay_payload": None,
            "final_response": "",
            "step": "INIT",
            "latency_ms": 0.0
        }

        start_t = time.time()
        res_state = autonomepay_graph.invoke(initial_state)
        elapsed = round((time.time() - start_t) * 1000, 2)

        bot_response = res_state.get("final_response", "")
        messages.append({"role": "assistant", "content": bot_response})
        
        execution_trace.append({
            "turn": turn_idx,
            "user": user_turn,
            "agent": bot_response,
            "guardrail_status": res_state.get("guardrail_status"),
            "latency_ms": elapsed
        })
        
        final_state = res_state

    # Run RAG Triad Judge evaluation on final turn
    triad = evaluate_rag_triad(
        query=dialogue[-1] if dialogue else "",
        retrieved_chunks=final_state.get("retrieved_policy_chunks", []),
        response_text=final_state.get("final_response", ""),
        proposed_offer=final_state.get("proposed_offer", {})
    )

    recovered = float(final_state.get("proposed_offer", {}).get("proposed_amount", 0.0))
    guard_status = final_state.get("guardrail_status", "PASSED")
    
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    langsmith_trace_url = f"https://smith.langchain.com/o/autonomepay/r/{run_id}"

    # Log into Database table `evaluation_runs`
    db = SessionLocal()
    eval_run = EvaluationRun(
        run_id=run_id,
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
        execution_trace=execution_trace
    )
    db.add(eval_run)
    db.commit()
    db.close()

    return {
        "run_id": run_id,
        "scenario_id": scenario_id,
        "merchant_id": merchant_id,
        "scenario_type": scenario_type,
        "turns": len(dialogue),
        "guardrail_status": guard_status,
        "rag_triad": triad,
        "recovered_inr": recovered,
        "langsmith_trace_url": langsmith_trace_url,
        "execution_trace": execution_trace
    }


def run_all_50_evaluations() -> List[Dict[str, Any]]:
    cases = generate_50_synthetic_cases()
    results = []
    for c in cases:
        try:
            res = run_single_simulation_case(c)
            results.append(res)
        except Exception as e:
            logger.error("Error executing case %s: %s", c.get("scenario_id"), str(e))
    return results
