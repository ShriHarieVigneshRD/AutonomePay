"""AutonomePay payments MCP server.

Exposes Razorpay payment-link tools over the Model Context Protocol. Tool names and result
shapes mirror Razorpay's official MCP server (amounts in paise, `id`, `short_url`, `status`),
so the agent's MCP client can talk to either one.

- With real Razorpay keys the tools call the Razorpay API (test or live mode).
- Without them they run a sandbox: links are stored in the payment_links table and point at
  the app's own /pay/<id> page, where a payment can be simulated.

Run standalone over stdio:  python -m app.payments.mcp_server
"""

import uuid
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from app.core.config import settings
from app.core.database import PaymentLink, SessionLocal, utcnow
from app.payments.razorpay import RazorpayClient

server = MCPServer(
    "autonomepay-payments",
    instructions="Create and look up Razorpay payment links. Amounts are in paise (INR × 100).",
)
_razorpay = RazorpayClient()


def _link_json(link: PaymentLink) -> dict[str, Any]:
    paise = round(float(link.amount_inr) * 100)
    return {
        "id": link.link_id,
        "short_url": link.short_url,
        "status": link.status,
        "amount": paise,
        "amount_paid": round(float(link.amount_paid_inr or 0) * 100),
        "currency": "INR",
        "description": link.description,
        "notes": {"sandbox": True},
    }


@server.tool(description="Create a Razorpay payment link. `amount` is in paise (₹279.00 = 27900).")
def create_payment_link(
    amount: int,
    description: str,
    currency: str = "INR",
    reference_id: str | None = None,
    customer_name: str | None = None,
    customer_email: str | None = None,
    customer_contact: str | None = None,
) -> dict[str, Any]:
    if amount <= 0:
        raise ToolError("amount must be a positive number of paise")
    if currency != "INR":
        raise ToolError("only INR is supported")

    if _razorpay.client:
        result = _razorpay.create_payment_link(
            amount_in_inr=amount / 100,
            description=description,
            reference_id=reference_id or uuid.uuid4().hex,
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_contact,
        )
        if not result["success"]:
            raise ToolError(result["error"])
        return {
            "id": result["payment_link_id"],
            "short_url": result["short_url"],
            "status": result["status"],
            "amount": amount,
            "amount_paid": 0,
            "currency": "INR",
            "description": description,
        }

    link_id = f"plink_sbx_{uuid.uuid4().hex}"
    with SessionLocal() as db:
        link = PaymentLink(
            link_id=link_id,
            amount_inr=amount / 100,
            short_url=f"{settings.PUBLIC_APP_URL.rstrip('/')}/pay/{link_id}",
            status="created",
            sandbox=True,
            description=description,
            created_at=utcnow(),
        )
        db.add(link)
        db.commit()
        return _link_json(link)


@server.tool(description="Fetch a payment link's current status and amount paid.")
def fetch_payment_link(payment_link_id: str) -> dict[str, Any]:
    if payment_link_id.startswith("plink_sbx_") or not _razorpay.client:
        with SessionLocal() as db:
            link = db.get(PaymentLink, payment_link_id)
            if not link:
                raise ToolError(f"payment link {payment_link_id} not found")
            return _link_json(link)
    result = _razorpay.fetch_payment_link(payment_link_id)
    if not result["success"]:
        raise ToolError(result["error"])
    return {
        "id": payment_link_id,
        "status": result["status"],
        "amount_paid": round(result["amount_paid_inr"] * 100),
    }


if __name__ == "__main__":
    server.run()
