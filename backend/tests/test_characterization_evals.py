"""Characterisation tests for the benchmark pipeline (F17–F21)."""

import pytest


@pytest.fixture(scope="module")
def completed_batch(client):
    # TestClient runs BackgroundTasks before returning, so the batch is finished here.
    res = client.post("/api/evals/run")
    assert res.status_code == 200
    started = res.json()
    assert started["status"] == "RUNNING" and started["total_cases"] == 50
    assert started["name"].startswith("Run #")
    return started["batch_id"]


def test_f17_f18_batch_listed_as_completed(client, completed_batch):
    batches = client.get("/api/evals/batches").json()
    batch = next(b for b in batches if b["batch_id"] == completed_batch)
    assert batch["status"] == "COMPLETED"
    assert batch["completed_cases"] == batch["total_cases"] == 50
    assert {"kpis", "created_at", "name"} <= batch.keys()


def test_f18_batches_newest_first(client, completed_batch):
    second = client.post("/api/evals/run").json()["batch_id"]
    ids = [b["batch_id"] for b in client.get("/api/evals/batches").json()]
    assert ids.index(second) < ids.index(completed_batch)


def test_f19_f20_results_matrix_and_kpis(client, completed_batch):
    data = client.get(f"/api/evals/results?batch_id={completed_batch}").json()
    assert data["batch"]["batch_id"] == completed_batch
    kpi = data["kpi"]
    assert {"total_invoiced", "total_recovered", "policy_breaches", "adversarial_intercepts",
            "rag_faithfulness_pct", "avg_latency_ms"} <= kpi.keys()  # fmt: skip
    assert kpi["adversarial_intercepts"] >= 1
    matrix = data["matrix"]
    assert len(matrix) == 50
    for row in matrix:
        assert {"run_id", "test_id", "scenario_type", "turns", "outcome", "guardrail_status",
                "rag_faithfulness", "recovered_inr", "initial_message", "execution_trace"} <= row.keys()  # fmt: skip
        assert 0 <= row["rag_faithfulness"] <= 1
        assert len(row["execution_trace"]) == row["turns"]
        assert {"turn", "user", "agent", "guardrail_status", "latency_ms"} <= row["execution_trace"][0].keys()
    adversarial = next(r for r in matrix if r["test_id"] == "eval_case_04")
    assert adversarial["guardrail_status"] == "ADVERSARIAL_INTERCEPTED"


def test_f19_results_default_to_latest_batch(client, completed_batch):
    latest = client.get("/api/evals/batches").json()[0]["batch_id"]
    assert client.get("/api/evals/results").json()["batch"]["batch_id"] == latest


def test_f21_langsmith_sync_local_mode(client):
    body = client.post("/api/evals/sync-langsmith").json()
    assert body["status"] == "LOCAL_MODE"
    assert body["total_examples"] == 50


def test_n5_every_case_is_scored_against_an_expectation(client, completed_batch):
    data = client.get(f"/api/evals/results?batch_id={completed_batch}").json()
    assert all(row["passed"] is not None and row["expected_action"] for row in data["matrix"])
    assert data["kpi"]["pass_rate_pct"] == 100.0  # the offline policy engine meets every expectation
    escalation = next(
        r for r in data["matrix"] if r["scenario_type"] == "RAZORPAYX_HUMAN_ESCALATION" and r["turns"] == 3
    )
    assert escalation["final_action"] == "HUMAN_ESCALATION" and escalation["recovered_inr"] == 0


def test_n5_scoring_rejects_wrong_action_or_link():
    from app.evals.dataset import generate_50_synthetic_cases, score_case

    notion = next(c for c in generate_50_synthetic_cases() if c["scenario_id"] == "eval_case_02")
    split = {
        "action": "MILESTONE_SPLIT",
        "razorpay_payload": {"success": True},
        "proposed_offer": {"proposed_amount": 7500},
    }
    assert score_case(notion, split)
    assert not score_case(notion, {**split, "action": "PROPOSE_SETTLEMENT"})
    assert not score_case(notion, {**split, "razorpay_payload": None})
    assert not score_case(
        notion, {**split, "proposed_offer": {"proposed_amount": 15000}}
    )  # not the approved half
