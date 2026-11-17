from typing import Any, TypedDict


class AutonomeState(TypedDict):
    # LangGraph drops keys that are not declared here.
    session_id: str | None
    messages: list[dict[str, str]]
    merchant_id: str
    merchant_name: str
    customer_id: str
    customer_name: str
    invoice_id: str
    original_amount: float
    failure_code: str
    customer_intent: str
    retrieved_policy_chunks: list[str]
    retrieved_sources: list[dict[str, Any]]
    guardrail_status: str
    guardrail_violations: list[str]
    guardrail_checks: list[dict[str, str]]
    proposed_offer: dict[str, Any]
    razorpay_payload: dict[str, Any] | None
    final_response: str
    action: str
    step: str
    latency_ms: float
    tokens_used: int
    benchmark: bool  # benchmark turns wait out LLM rate limits; live chat falls back at once
    reply_source: dict[str, Any]  # who wrote final_response: {"by": ai|rulebook|guardrail, ...}


def build_initial_state(
    *,
    session_id: str,
    messages: list[dict[str, str]],
    merchant_id: str,
    merchant_name: str,
    customer_id: str,
    customer_name: str,
    invoice_id: str,
    original_amount: float,
    failure_code: str,
    benchmark: bool = False,
) -> AutonomeState:
    return {
        "session_id": session_id,
        "messages": messages,
        "merchant_id": merchant_id,
        "merchant_name": merchant_name,
        "customer_id": customer_id,
        "customer_name": customer_name,
        "invoice_id": invoice_id,
        "original_amount": original_amount,
        "failure_code": failure_code,
        "customer_intent": "",
        "retrieved_policy_chunks": [],
        "retrieved_sources": [],
        "guardrail_status": "PASSED",
        "guardrail_violations": [],
        "guardrail_checks": [],
        "proposed_offer": {},
        "razorpay_payload": None,
        "final_response": "",
        "action": "",
        "step": "INIT",
        "latency_ms": 0.0,
        "tokens_used": 0,
        "benchmark": benchmark,
        "reply_source": {},
    }
