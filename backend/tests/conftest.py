"""Shared fixtures. Forces a fully offline, deterministic environment.

The env overrides below run before any `app` import so the real keys in
backend/.env are never used by tests (env vars take precedence over .env).
"""

import json
import os
import pathlib
import tempfile
from types import SimpleNamespace

import pytest

_TMP = pathlib.Path(tempfile.mkdtemp(prefix="autonomepay-tests-"))
os.environ.update(
    {
        "DATABASE_URL": f"sqlite:///{(_TMP / 'test.db').as_posix()}",
        "OPENROUTER_API_KEY": "",
        "RAZORPAY_KEY_ID": "rzp_test_mock12345",
        "RAZORPAY_KEY_SECRET": "mock_secret",
        "LANGCHAIN_API_KEY": "",
        "LANGSMITH_API_KEY": "",
        "LANGCHAIN_TRACING_V2": "false",
        "LANGSMITH_TRACING": "false",
        "MAX_SESSION_TOKEN_BUDGET": "6000",
        "CHAT_RATE_LIMIT_PER_MIN": "100000",
        "ADMIN_TOKEN": "",
        "RAZORPAY_MCP_MODE": "embedded",
        "PUBLIC_APP_URL": "http://localhost:5173",
    }
)

import litellm  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core import llm_gateway as gateway_module  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.main import app  # noqa: E402


def _offline(**_kwargs):
    raise RuntimeError("network disabled in tests")


# Patched at import time (not in a fixture) so module/session fixtures are offline too.
litellm.completion = _offline


@pytest.fixture(autouse=True)
def clean_gateway():
    """Every test starts with a clean gateway cache and token counters."""
    gateway_module.gateway.semantic_cache.clear()
    gateway_module.gateway.session_token_usage.clear()


@pytest.fixture
def llm_reply(monkeypatch):
    """Make the LLM return a fixed payload (dict → JSON string, str → raw text)."""

    def _set(payload, tokens=100):
        content = payload if isinstance(payload, str) else json.dumps(payload)

        def fake_completion(**kwargs):
            fake_completion.calls.append(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
                usage=SimpleNamespace(total_tokens=tokens),
            )

        fake_completion.calls = []
        monkeypatch.setattr(litellm, "completion", fake_completion)
        monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "test-key")  # gateway skips the LLM without a key
        return fake_completion

    return _set


@pytest.fixture(scope="session", autouse=True)
def database():
    """Tables and seed data exist for every test, even ones that never start the app."""
    from app.core.database import init_db

    init_db()


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c
