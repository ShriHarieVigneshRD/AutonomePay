from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db, Merchant, Customer, Invoice
from app.agents import autonomepay_graph

router = APIRouter()

class ChatRequest(BaseModel):
    merchant_id: str = "hotstar"
    customer_id: str = "cust_hotstar_01"
    invoice_id: str = "inv_hotstar_101"
    messages: List[Dict[str, str]]

class ChatResponse(BaseModel):
    final_response: str
    guardrail_status: str
    guardrail_violations: List[str]
    retrieved_policy_chunks: List[str]
    proposed_offer: Dict[str, Any]
    razorpay_payload: Optional[Dict[str, Any]]
    latency_ms: float
    token_spend: int = 120

@router.post("/chat", response_model=ChatResponse)
def handle_chat_turn(payload: ChatRequest, db: Session = Depends(get_db)):
    merchant = db.query(Merchant).filter(Merchant.merchant_id == payload.merchant_id).first()
    customer = db.query(Customer).filter(Customer.customer_id == payload.customer_id).first()
    invoice = db.query(Invoice).filter(Invoice.invoice_id == payload.invoice_id).first()

    merchant_name = merchant.name if merchant else payload.merchant_id.title()
    customer_name = customer.name if customer else "Customer"
    original_amount = float(invoice.original_amount) if invoice else 299.00
    failure_code = invoice.failure_code if invoice else "INSUFFICIENT_FUNDS"

    initial_state = {
        "session_id": f"chat_{payload.customer_id}_{payload.invoice_id}",
        "messages": payload.messages,
        "merchant_id": payload.merchant_id,
        "merchant_name": merchant_name,
        "customer_id": payload.customer_id,
        "customer_name": customer_name,
        "invoice_id": payload.invoice_id,
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
        "latency_ms": 0.0
    }

    try:
        final_state = autonomepay_graph.invoke(initial_state)
        return ChatResponse(
            final_response=final_state.get("final_response", ""),
            guardrail_status=final_state.get("guardrail_status", "PASSED"),
            guardrail_violations=final_state.get("guardrail_violations", []),
            retrieved_policy_chunks=final_state.get("retrieved_policy_chunks", []),
            proposed_offer=final_state.get("proposed_offer", {}),
            razorpay_payload=final_state.get("razorpay_payload"),
            latency_ms=final_state.get("latency_ms", 120.0),
            token_spend=150
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution error: {str(e)}")
