"""Benchmark rework: batches of 10, the opening message, rate-limit patience and reply sources."""

from collections import Counter

import litellm
import pytest
from helpers import settlement

from app.core.config import settings
from app.core.llm_gateway import gateway
from app.evals import runner
from app.evals.dataset import BATCH_COUNT, generate_50_synthetic_cases

CASES = {c["scenario_id"]: c for c in generate_50_synthetic_cases()}


def test_five_batches_of_ten_each_mixing_merchants():
    batches = Counter(c["batch"] for c in CASES.values())
    assert batches == {b: 10 for b in range(1, BATCH_COUNT + 1)}
    assert CASES["eval_case_01"]["batch"] == CASES["eval_case_06"]["batch"] == 1
    assert CASES["eval_case_50"]["batch"] == 5
    for b in batches:
        assert len({c["merchant_id"] for c in CASES.values() if c["batch"] == b}) >= 7


def test_benchmark_conversation_starts_with_the_opening_message(client, monkeypatch):
    seen = []

    def fake_invoke(state):
        seen.append(state)
        return {**state, "final_response": "ok", "action": "PROPOSE_SETTLEMENT"}

    monkeypatch.setattr(runner.autonomepay_graph, "invoke", fake_invoke)
    runner.run_single_simulation_case(CASES["eval_case_05"])
    greeting = next(s for s in client.get("/api/scenarios").json() if s["id"] == "eval_case_05")[
        "initial_message"
    ]
    first = seen[0]["messages"]
    assert first[0] == {"role": "assistant", "content": greeting}
    assert first[1]["role"] == "user" and seen[0]["benchmark"] is True


def test_batch_run_covers_only_its_cases_and_feeds_latest_results(client):
    started = client.post("/api/evals/run", params={"batch": 2}).json()
    assert started["case_batch"] == 2 and started["total_cases"] == 10 and "Batch 2 of 5" in started["name"]
    results = client.get("/api/evals/results", params={"batch_id": started["batch_id"]}).json()
    assert sorted(r["test_id"] for r in results["matrix"]) == sorted(
        i for i, c in CASES.items() if c["batch"] == 2
    )
    latest = client.get("/api/evals/latest").json()
    assert latest["coverage"]["total"] == 50 and latest["coverage"]["evaluated"] >= 10
    assert latest["kpi"]["ai_replies"] == 0 and latest["kpi"]["ai_reply_turns"] > 0  # offline: rulebook only
    newest = {r["test_id"]: r["batch_id"] for r in latest["matrix"]}
    assert all(newest[r["test_id"]] == started["batch_id"] for r in results["matrix"])


def test_batch_number_is_validated(client):
    assert client.post("/api/evals/run", params={"batch": 6}).status_code == 422


def test_trace_records_who_wrote_each_reply(llm_reply):
    llm_reply(settlement(action="EXTEND_GRACE", amount=299.0, message="Take a few extra days.", link=False))
    ai = runner.run_single_simulation_case(CASES["eval_case_01"])
    assert all(t["reply_source"]["by"] == "ai" for t in ai["execution_trace"])

    blocked = runner.run_single_simulation_case(CASES["eval_case_04"])
    assert blocked["execution_trace"][0]["reply_source"] == {
        "by": "guardrail",
        "reason": "prompt injection blocked",
    }


def test_without_a_key_the_rulebook_answers_and_says_why():
    trace = runner.run_single_simulation_case(CASES["eval_case_05"])["execution_trace"]
    assert {t["reply_source"]["by"] for t in trace} == {"rulebook"}
    assert trace[0]["reply_source"]["reason"] == "no LLM key configured"


# --- rate-limit patience (benchmark only) -----------------------------------------------------


class RateLimited(Exception):
    status_code = 429


@pytest.fixture
def sleeps(monkeypatch):
    calls = []
    monkeypatch.setattr("app.core.llm_gateway.time.sleep", calls.append)
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "test-key")
    return calls


def flaky(monkeypatch, failures, error="Rate limit exceeded: free-models-per-min"):
    state = {"calls": 0}

    def completion(**_kwargs):
        state["calls"] += 1
        if state["calls"] <= failures:
            raise RateLimited(error)
        from types import SimpleNamespace

        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="hello"))],
            usage=SimpleNamespace(total_tokens=10),
        )

    monkeypatch.setattr(litellm, "completion", completion)
    return state


def test_patient_calls_wait_out_a_per_minute_limit(monkeypatch, sleeps):
    flaky(monkeypatch, failures=4)  # the whole 4-model chain is rate-limited once
    res = gateway.completion(messages=[{"role": "user", "content": "patient"}], patient=True)
    assert res["content"] == "hello"
    assert 15 in sleeps  # waited before retrying the chain


def test_live_chat_does_not_wait(monkeypatch, sleeps):
    flaky(monkeypatch, failures=4)
    res = gateway.completion(messages=[{"role": "user", "content": "impatient"}])
    assert res["error"] == "RATE_LIMITED" and not [s for s in sleeps if s >= 15]


def test_daily_limit_fails_fast_even_when_patient(monkeypatch, sleeps):
    flaky(monkeypatch, failures=99, error="Rate limit exceeded: free-models-per-day")
    res = gateway.completion(messages=[{"role": "user", "content": "daily"}], patient=True)
    assert res["error"] == "DAILY_LIMIT" and not [s for s in sleeps if s >= 15]
