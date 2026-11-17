from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

ID_PATTERN = r"^[A-Za-z0-9_.-]{1,64}$"


class ChatMessage(BaseModel):
    # Only the customer and the agent speak; clients cannot inject system instructions.
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    merchant_id: str = Field("hotstar", pattern=ID_PATTERN)
    customer_id: str = Field("cust_hotstar_01", pattern=ID_PATTERN)
    invoice_id: str = Field("inv_hotstar_101", pattern=ID_PATTERN)
    session_id: str | None = Field(
        None, pattern=ID_PATTERN, description="One id per conversation (token budget)."
    )
    messages: list[ChatMessage] = Field(min_length=1, max_length=40)

    @model_validator(mode="after")
    def _ends_with_customer(self) -> "ChatRequest":
        if self.messages[-1].role != "user":
            raise ValueError("the last message must be from the user")
        return self


class GuardrailCheck(BaseModel):
    id: str
    label: str
    status: Literal["passed", "corrected", "blocked", "skipped"]
    detail: str


class ChatResponse(BaseModel):
    final_response: str
    guardrail_status: str
    guardrail_violations: list[str]
    guardrail_checks: list[GuardrailCheck] = []
    retrieved_policy_chunks: list[str]
    proposed_offer: dict[str, Any]
    razorpay_payload: dict[str, Any] | None
    action: str | None = None
    step: str | None = None
    customer_intent: str | None = None
    latency_ms: float
    token_spend: int = 0
