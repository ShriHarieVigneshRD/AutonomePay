"""N7: payment status over MCP and the sandbox checkout."""

from helpers import NOTION, chat_body, settlement

from app.core.database import Invoice, PaymentLink, SessionLocal


def issue_link(client, llm_reply, ids=None, amount=279.0, **kwargs):
    llm_reply(settlement(amount=amount, message=f"Your amount is INR {amount:,.2f}.", **kwargs))
    body = chat_body("Yes, send the link", ids=ids) if ids else chat_body("Yes, send the link")
    return client.post("/api/chat", json=body).json()["razorpay_payload"]


def test_status_is_checked_over_mcp(client, llm_reply):
    link = issue_link(client, llm_reply)
    status = client.get(f"/api/payments/{link['payment_link_id']}").json()
    assert status["status"] == "created" and status["sandbox"] is True
    assert status["amount_inr"] == 279.0 and status["merchant_name"] == "Disney+ Hotstar"


def test_simulated_payment_marks_the_invoice_recovered(client, llm_reply):
    with SessionLocal() as db:
        before = float(db.get(Invoice, "inv_hotstar_101").recovered_amount or 0)
    link = issue_link(client, llm_reply)
    paid = client.post(f"/api/payments/{link['payment_link_id']}/simulate-payment").json()
    assert paid["status"] == "paid" and paid["amount_paid_inr"] == 279.0 and paid["paid_at"]
    assert paid["invoice_recovered_inr"] == before + 279.0
    # idempotent: paying again changes nothing
    again = client.post(f"/api/payments/{link['payment_link_id']}/simulate-payment").json()
    assert again["invoice_recovered_inr"] == before + 279.0
    assert client.get(f"/api/payments/{link['payment_link_id']}").json()["status"] == "paid"


def test_first_instalment_is_a_partial_recovery(client, llm_reply):
    greeting = {"role": "assistant", "content": "Hello Rohan"}
    llm_reply(
        settlement(
            action="MILESTONE_SPLIT",
            amount=7500.0,
            message="Pay INR 7,500.00 now.",
            split_amounts=[7500.0, 7500.0],
        )
    )
    body = client.post("/api/chat", json=chat_body("Yes, set it up", ids=NOTION, greeting=greeting)).json()
    paid = client.post(f"/api/payments/{body['razorpay_payload']['payment_link_id']}/simulate-payment").json()
    assert paid["invoice_status"] == "PARTIALLY_RECOVERED"


def test_unknown_links_404_and_live_links_cannot_be_simulated(client):
    assert client.get("/api/payments/plink_nope").status_code == 404
    with SessionLocal() as db:
        db.add(
            PaymentLink(link_id="plink_live_1", amount_inr=100, short_url="https://rzp.io/x", sandbox=False)
        )
        db.commit()
    assert client.post("/api/payments/plink_live_1/simulate-payment").status_code == 403
