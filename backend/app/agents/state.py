from typing import TypedDict, List, Dict, Any, Optional

class AutonomeState(TypedDict):
    messages: List[Dict[str, str]]
    merchant_id: str
    merchant_name: str
    customer_id: str
    customer_name: str
    invoice_id: str
    original_amount: float
    failure_code: str
    customer_intent: str
    retrieved_policy_chunks: List[str]
    guardrail_status: str
    guardrail_violations: List[str]
    proposed_offer: Dict[str, Any]
    razorpay_payload: Optional[Dict[str, Any]]
    final_response: str
    step: str
    latency_ms: float
