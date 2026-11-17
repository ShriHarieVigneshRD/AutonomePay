"""Bookkeeping for issued payment links (all modes) and their settlement."""

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.core.database import Invoice, PaymentLink, SessionLocal, utcnow


def record_issued_link(payload: dict[str, Any], invoice_id: str, session_id: str | None) -> None:
    """Attach a newly created link to its invoice and conversation. Sandbox links already exist."""
    with SessionLocal() as db:
        link = db.get(PaymentLink, payload["payment_link_id"]) or PaymentLink(
            link_id=payload["payment_link_id"],
            amount_inr=payload["amount_in_inr"],
            short_url=payload["short_url"],
            status=payload.get("status", "created"),
            sandbox=bool(payload.get("sandbox")),
            description=payload.get("description"),
            created_at=utcnow(),
        )
        link.invoice_id = invoice_id
        link.session_id = session_id
        db.add(link)
        invoice = db.get(Invoice, invoice_id)
        if invoice:
            invoice.razorpay_payment_link = payload["short_url"]
        db.commit()


def mark_paid(db: Session, link: PaymentLink, amount_paid_inr: float) -> None:
    """Record a payment against the link and the invoice it settles. Idempotent; caller commits."""
    if link.status == "paid":
        return
    paid = Decimal(str(amount_paid_inr))
    link.status = "paid"
    link.amount_paid_inr = paid
    link.paid_at = utcnow()
    invoice = db.get(Invoice, link.invoice_id) if link.invoice_id else None
    if invoice:
        recovered = (invoice.recovered_amount or Decimal(0)) + paid
        invoice.recovered_amount = recovered
        invoice.current_status = (
            "RECOVERED" if recovered >= invoice.original_amount else "PARTIALLY_RECOVERED"
        )
