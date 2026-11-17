import logging
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.graph import autonomepay_graph
from app.agents.state import build_initial_state
from app.api.deps import chat_rate_limit
from app.api.schemas import ChatRequest, ChatResponse
from app.core.database import Customer, Invoice, Merchant, get_db

logger = logging.getLogger(__name__)
router = APIRouter()


def load_case(db: Session, merchant_id: str, customer_id: str, invoice_id: str):
    merchant = db.get(Merchant, merchant_id)
    customer = db.get(Customer, customer_id)
    invoice = db.get(Invoice, invoice_id)
    if not merchant or not customer or not invoice:
        raise HTTPException(status_code=404, detail="Unknown merchant, customer or invoice.")
    if invoice.merchant_id != merchant.merchant_id or invoice.customer_id != customer.customer_id:
        raise HTTPException(
            status_code=404, detail="This invoice does not belong to that customer and merchant."
        )
    return merchant, customer, invoice


def run_turn(
    merchant: Merchant, customer: Customer, invoice: Invoice, messages: list[dict[str, str]], session_id: str
) -> ChatResponse:
    """One agent turn over the full history; shared by /chat and /conversations."""
    initial_state = build_initial_state(
        session_id=session_id,
        messages=messages,
        merchant_id=merchant.merchant_id,
        merchant_name=merchant.name,
        customer_id=customer.customer_id,
        customer_name=customer.name,
        invoice_id=invoice.invoice_id,
        original_amount=float(invoice.original_amount),
        failure_code=invoice.failure_code,
    )
    started = time.perf_counter()
    try:
        final_state = autonomepay_graph.invoke(initial_state)
    except Exception as e:
        error_id = uuid.uuid4().hex[:8]
        logger.exception("Agent execution failed (error id %s)", error_id)
        raise HTTPException(
            status_code=500, detail=f"The agent hit an internal error (ref {error_id})."
        ) from e

    return ChatResponse(
        final_response=final_state["final_response"],
        guardrail_status=final_state["guardrail_status"],
        guardrail_violations=final_state["guardrail_violations"],
        guardrail_checks=final_state.get("guardrail_checks", []),
        retrieved_policy_chunks=final_state["retrieved_policy_chunks"],
        proposed_offer=final_state["proposed_offer"],
        razorpay_payload=final_state["razorpay_payload"],
        action=final_state.get("action"),
        step=final_state.get("step"),
        customer_intent=final_state.get("customer_intent"),
        latency_ms=round((time.perf_counter() - started) * 1000, 2),
        token_spend=final_state.get("tokens_used", 0),
    )


@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(chat_rate_limit)])
def handle_chat_turn(payload: ChatRequest, db: Session = Depends(get_db)):
    """Stateless turn: the client sends the whole history. Prefer /conversations, where the server keeps it."""
    merchant, customer, invoice = load_case(db, payload.merchant_id, payload.customer_id, payload.invoice_id)
    return run_turn(
        merchant,
        customer,
        invoice,
        [m.model_dump() for m in payload.messages],
        # Budget is per conversation; clients without a session id get a fresh budget per request.
        session_id=f"chat_{payload.session_id or uuid.uuid4().hex}",
    )
