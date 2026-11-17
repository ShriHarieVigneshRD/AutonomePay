from typing import Any

from pydantic import BaseModel


class ChatRequest(BaseModel):
    merchant_id: str = "hotstar"
    customer_id: str = "cust_hotstar_01"
    invoice_id: str = "inv_hotstar_101"
    messages: list[dict[str, str]]


class ChatResponse(BaseModel):
    final_response: str
    guardrail_status: str
    guardrail_violations: list[str]
    retrieved_policy_chunks: list[str]
    proposed_offer: dict[str, Any]
    razorpay_payload: dict[str, Any] | None
    latency_ms: float
    token_spend: int = 120
