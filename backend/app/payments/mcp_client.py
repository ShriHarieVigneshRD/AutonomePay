"""The agent's MCP client for payment tools.

RAZORPAY_MCP_MODE picks the server:
- embedded (default): AutonomePay's own MCP server (app.payments.mcp_server), connected in-process.
- remote:  Razorpay's hosted MCP server (RAZORPAY_MCP_URL) with Basic auth from the Razorpay keys.
- stdio:   any MCP server launched as a subprocess (RAZORPAY_MCP_COMMAND), e.g. Razorpay's binary.

Every mode speaks real MCP (initialize → tools/call); results are normalised to one dict shape.
"""

import base64
import json
import logging
import os
import shlex
from typing import Any

import anyio
from mcp.client.client import Client
from mcp.client.stdio import StdioServerParameters
from mcp.client.streamable_http import streamable_http_client
from mcp.shared._httpx_utils import create_mcp_http_client  # public in __all__, private module path

from app.core.config import settings

logger = logging.getLogger(__name__)


class PaymentToolError(RuntimeError):
    pass


def _client() -> Client:
    mode = settings.RAZORPAY_MCP_MODE
    if mode == "remote":
        token = base64.b64encode(
            f"{settings.RAZORPAY_KEY_ID}:{settings.RAZORPAY_KEY_SECRET}".encode()
        ).decode()
        http = create_mcp_http_client(headers={"Authorization": f"Basic {token}"})
        return Client(streamable_http_client(settings.RAZORPAY_MCP_URL, http_client=http))
    if mode == "stdio":
        command, *args = shlex.split(settings.RAZORPAY_MCP_COMMAND)
        env = {
            **os.environ,
            "RAZORPAY_KEY_ID": settings.RAZORPAY_KEY_ID,
            "RAZORPAY_KEY_SECRET": settings.RAZORPAY_KEY_SECRET,
        }
        return Client(StdioServerParameters(command=command, args=args, env=env))
    from app.payments.mcp_server import server  # embedded: imported lazily to avoid a cycle

    return Client(server)


def _result_data(result: Any) -> dict[str, Any]:
    text = "".join(getattr(part, "text", "") for part in result.content)
    if result.is_error:
        raise PaymentToolError(text or "tool error")
    if isinstance(result.structured_content, dict):
        return result.structured_content
    return json.loads(text)


async def _call(tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    # shortcut: one MCP session per call (cheap in-process); keep a long-lived session if remote latency matters.
    async with _client() as client:
        result = await client.call_tool(tool, arguments)
    return _result_data(result)  # raise outside the session so errors aren't wrapped in an ExceptionGroup


async def _list() -> list[str]:
    async with _client() as client:
        return [tool.name for tool in (await client.list_tools()).tools]


def call_tool(tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Synchronous tool call (the agent graph runs in worker threads without an event loop)."""
    return anyio.run(_call, tool, arguments)


def list_tools() -> list[str]:
    return anyio.run(_list)


def create_payment_link(
    amount_in_inr: float,
    description: str,
    reference_id: str,
    customer_name: str | None = None,
    customer_email: str | None = None,
    customer_phone: str | None = None,
) -> dict[str, Any]:
    """Create a link via MCP and return the agent's payload shape (never raises)."""
    base = {"tool": "create_payment_link", "transport": f"mcp:{settings.RAZORPAY_MCP_MODE}"}
    arguments: dict[str, Any] = {
        "amount": round(amount_in_inr * 100),
        "currency": "INR",
        "description": description,
        "reference_id": reference_id[:40],
    }
    contact = {
        "customer_name": customer_name,
        # Never pass demo placeholders to a real gateway (it would notify them).
        "customer_email": customer_email
        if customer_email and not customer_email.endswith("@example.com")
        else None,
        "customer_contact": customer_phone,
    }
    arguments.update({k: v for k, v in contact.items() if v})
    try:
        data = call_tool("create_payment_link", arguments)
    except Exception as e:
        logger.warning("create_payment_link via MCP failed: %s", e)
        return {
            **base,
            "success": False,
            "amount_in_inr": round(amount_in_inr, 2),
            "error": "Payment link could not be created.",
        }
    link_id = data.get("id", "")
    return {
        **base,
        "success": True,
        "payment_link_id": link_id,
        "short_url": data.get("short_url"),
        "status": data.get("status", "created"),
        "amount_in_inr": data.get("amount", 0) / 100,
        "sandbox": link_id.startswith("plink_sbx_"),
        "description": description,
    }


def fetch_payment_link(link_id: str) -> dict[str, Any]:
    data = call_tool("fetch_payment_link", {"payment_link_id": link_id})
    return {
        "payment_link_id": link_id,
        "status": data.get("status", "created"),
        "amount_paid_inr": (data.get("amount_paid") or 0) / 100,
        "transport": f"mcp:{settings.RAZORPAY_MCP_MODE}",
    }
