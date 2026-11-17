import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.graph import autonomepay_graph
from app.agents.state import build_initial_state
from app.api.schemas import ChatRequest, ChatResponse
from app.core.database import Customer, Invoice, Merchant, get_db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def handle_chat_turn(payload: ChatRequest, db: Session = Depends(get_db)):
    merchant = db.get(Merchant, payload.merchant_id)
    customer = db.get(Customer, payload.customer_id)
    invoice = db.get(Invoice, payload.invoice_id)

    initial_state = build_initial_state(
        session_id=f"chat_{payload.customer_id}_{payload.invoice_id}",
        messages=payload.messages,
        merchant_id=payload.merchant_id,
        merchant_name=merchant.name if merchant else payload.merchant_id.title(),
        customer_id=payload.customer_id,
        customer_name=customer.name if customer else "Customer",
        invoice_id=payload.invoice_id,
        original_amount=float(invoice.original_amount) if invoice else 299.00,
        failure_code=invoice.failure_code if invoice else "INSUFFICIENT_FUNDS",
    )

    try:
        final_state = autonomepay_graph.invoke(initial_state)
    except Exception as e:
        logger.exception("Agent execution failed")
        raise HTTPException(status_code=500, detail=f"Agent execution error: {e}") from e

    return ChatResponse(
        final_response=final_state.get("final_response", ""),
        guardrail_status=final_state.get("guardrail_status", "PASSED"),
        guardrail_violations=final_state.get("guardrail_violations", []),
        retrieved_policy_chunks=final_state.get("retrieved_policy_chunks", []),
        proposed_offer=final_state.get("proposed_offer", {}),
        razorpay_payload=final_state.get("razorpay_payload"),
        latency_ms=final_state.get("latency_ms", 120.0),
        token_spend=150,
    )
