from typing import Any, TypedDict


class AutonomeState(TypedDict):
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
    guardrail_status: str
    guardrail_violations: list[str]
    proposed_offer: dict[str, Any]
    razorpay_payload: dict[str, Any] | None
    final_response: str
    step: str
    latency_ms: float


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
        "guardrail_status": "PASSED",
        "guardrail_violations": [],
        "proposed_offer": {},
        "razorpay_payload": None,
        "final_response": "",
        "step": "INIT",
        "latency_ms": 0.0,
    }
