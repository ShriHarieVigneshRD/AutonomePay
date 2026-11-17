"""N7: payment-link status (checked over MCP) and the sandbox checkout."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import chat_rate_limit
from app.core.database import Invoice, Merchant, PaymentLink, get_db
from app.payments import mcp_client
from app.payments.ledger import mark_paid

logger = logging.getLogger(__name__)
router = APIRouter()


def _link_view(db: Session, link: PaymentLink) -> dict:
    invoice = db.get(Invoice, link.invoice_id) if link.invoice_id else None
    merchant = db.get(Merchant, invoice.merchant_id) if invoice and invoice.merchant_id else None
    return {
        "link_id": link.link_id,
        "status": link.status,
        "sandbox": link.sandbox,
        "short_url": link.short_url,
        "amount_inr": float(link.amount_inr),
        "amount_paid_inr": float(link.amount_paid_inr or 0),
        "description": link.description,
        "paid_at": link.paid_at.isoformat() if link.paid_at else None,
        "invoice_id": link.invoice_id,
        "merchant_name": merchant.name if merchant else None,
        "invoice_status": invoice.current_status if invoice else None,
        "invoice_recovered_inr": float(invoice.recovered_amount or 0) if invoice else None,
    }


def _get_link(db: Session, link_id: str) -> PaymentLink:
    link = db.get(PaymentLink, link_id)
    if not link:
        raise HTTPException(status_code=404, detail="Payment link not found.")
    return link


@router.get("/payments/{link_id}", dependencies=[Depends(chat_rate_limit)])
def payment_status(link_id: str, db: Session = Depends(get_db)):
    link = _get_link(db, link_id)
    if link.status != "paid":
        try:
            remote = mcp_client.fetch_payment_link(link_id)
        except Exception as e:
            logger.warning("Status check for %s failed: %s", link_id, e)
            raise HTTPException(status_code=502, detail="Could not reach the payment provider.") from e
        if remote["status"] == "paid":
            mark_paid(db, link, remote["amount_paid_inr"] or float(link.amount_inr))
        elif remote["status"] != link.status:
            link.status = remote["status"]
        db.commit()
    return _link_view(db, link)


@router.post("/payments/{link_id}/simulate-payment", dependencies=[Depends(chat_rate_limit)])
def simulate_payment(link_id: str, db: Session = Depends(get_db)):
    link = _get_link(db, link_id)
    if not link.sandbox:
        raise HTTPException(status_code=403, detail="Only sandbox links can be paid by simulation.")
    mark_paid(db, link, float(link.amount_inr))
    db.commit()
    return _link_view(db, link)
