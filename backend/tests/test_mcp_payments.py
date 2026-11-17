"""N1: payment tools over the Model Context Protocol."""

import json
from types import SimpleNamespace

import pytest
from helpers import chat_body, settlement

from app.core.database import PaymentLink, SessionLocal
from app.payments import mcp_client


def test_tools_are_discovered_over_mcp():
    assert set(mcp_client.list_tools()) >= {"create_payment_link", "fetch_payment_link"}


def test_create_and_fetch_a_sandbox_link_over_mcp():
    created = mcp_client.create_payment_link(279.0, "test", "inv-1")
    assert created["success"] and created["sandbox"]
    assert created["transport"] == "mcp:embedded"
    assert created["amount_in_inr"] == 279.0
    fetched = mcp_client.fetch_payment_link(created["payment_link_id"])
    assert fetched["status"] == "created" and fetched["amount_paid_inr"] == 0


def test_tool_errors_become_a_failed_payload_not_an_exception():
    result = mcp_client.create_payment_link(0, "zero", "inv-1")
    assert result["success"] is False and "short_url" not in result
    with pytest.raises(mcp_client.PaymentToolError):
        mcp_client.fetch_payment_link("plink_sbx_missing")


def test_agent_issues_links_through_mcp_and_records_them(client, llm_reply):
    llm_reply(settlement())
    body = client.post("/api/chat", json={**chat_body("Yes, send the link"), "session_id": "mcp-test"}).json()
    payload = body["razorpay_payload"]
    assert payload["tool"] == "create_payment_link" and payload["transport"] == "mcp:embedded"
    with SessionLocal() as db:
        link = db.get(PaymentLink, payload["payment_link_id"])
        assert link.invoice_id == "inv_hotstar_101"
        assert link.session_id == "chat_mcp-test"
        assert float(link.amount_inr) == 279.0


def test_official_server_text_results_are_normalised():
    # Razorpay's MCP server answers with the API's JSON as text content.
    api_json = {
        "id": "plink_ABC",
        "short_url": "https://rzp.io/rzp/abc",
        "status": "created",
        "amount": 27900,
    }
    result = SimpleNamespace(
        is_error=False, structured_content=None, content=[SimpleNamespace(text=json.dumps(api_json))]
    )
    assert mcp_client._result_data(result) == api_json
    error = SimpleNamespace(
        is_error=True, structured_content=None, content=[SimpleNamespace(text="Bad request")]
    )
    with pytest.raises(mcp_client.PaymentToolError, match="Bad request"):
        mcp_client._result_data(error)
