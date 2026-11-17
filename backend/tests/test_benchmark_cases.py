"""The benchmark cases are data, so they are tested too: no repeats, valid expectations, real sources."""

from collections import Counter

import pytest

from app.core.catalog import get_merchant_rules, load_catalog
from app.core.database import SessionLocal
from app.evals.dataset import generate_50_synthetic_cases, score_case
from app.evals.retrieval_eval import is_relevant
from app.guardrails.offer_guard import ACTIONS, run_post_llm_guardrail
from app.rag.chunking import load_corpus

CASES = generate_50_synthetic_cases()
CORPUS = load_corpus()
BY_ID = {c["scenario_id"]: c for c in CASES}
with_source = [c for c in CASES if "source" in c["expected"]]
with_amount = [c for c in CASES if "amount" in c["expected"]]


def case_id(case):
    return f"{case['scenario_id']}-{case['scenario_type']}"


def test_fifty_cases_with_stable_primary_ids():
    assert [c["scenario_id"] for c in CASES] == [f"eval_case_{i:02d}" for i in range(1, 51)]
    primaries = [
        (BY_ID[f"eval_case_0{i}"]["customer_id"], BY_ID[f"eval_case_0{i}"]["invoice_id"]) for i in range(1, 5)
    ]
    assert primaries == [
        ("cust_hotstar_01", "inv_hotstar_101"),
        ("cust_notion_01", "inv_notion_202"),
        ("cust_quickkart_01", "inv_quickkart_303"),
        ("cust_bad_actor", "inv_adv_999"),
    ]
    assert len({c["invoice_id"] for c in CASES}) == 50


def test_no_case_repeats_another():
    repeats = Counter((c["merchant_id"], tuple(c["dialogue_script"])) for c in CASES)
    assert max(repeats.values()) == 1


def test_every_merchant_has_a_full_negotiation():
    merchants = set(load_catalog())
    assert {c["merchant_id"] for c in CASES if c["total_turns"] >= 3} == merchants
    assert sum(not c["is_multi_turn"] for c in CASES) <= 6  # first contact is covered, not padded


def test_expectations_use_real_actions():
    valid = ACTIONS | {"BLOCKED", "NONE"}
    for case in CASES:
        assert set(case["expected"]["actions"]) <= valid, case["scenario_id"]
        assert case["expected"]["link"] in (True, False, None)


@pytest.mark.parametrize("case", with_source, ids=case_id)
def test_expected_source_exists_in_the_merchant_corpus(case):
    marker = [case["expected"]["source"]]
    assert any(is_relevant(chunk, marker) for chunk in CORPUS[case["merchant_id"]])


def test_web_policy_snapshots_are_exercised():
    web_cases = [
        c for c in with_source
        if any(ch.kind == "web" and is_relevant(ch, [c["expected"]["source"]]) for ch in CORPUS[c["merchant_id"]])
    ]  # fmt: skip
    assert len(web_cases) >= 6
    assert len({c["merchant_id"] for c in web_cases}) >= 5


@pytest.mark.parametrize("case", with_amount, ids=case_id)
def test_expected_amount_is_one_the_guardrail_approves(case):
    with SessionLocal() as db:
        rules = get_merchant_rules(db, case["merchant_id"])
    amount = case["expected"]["amount"]
    approvals = [
        run_post_llm_guardrail({"proposed_amount": amount}, rules, case["original_amount"], action)
        for action in case["expected"]["actions"]
    ]
    assert any(r["passed"] and r["corrected_offer"]["proposed_amount"] == amount for r in approvals)


def test_score_case_checks_amount_and_source():
    tv = next(c for c in CASES if c["scenario_type"] == "NETFLIX_TV_PLAN_DOWNGRADE")
    state = {
        "action": "PLAN_DOWNGRADE",
        "razorpay_payload": {"success": True},
        "proposed_offer": {"proposed_amount": 199},
    }
    cited = ["[Netflix plans and pricing › Plans and Pricing] (https://help.netflix.com/...)\nMobile ₹149"]
    assert score_case(tv, state, cited)
    assert not score_case(tv, {**state, "proposed_offer": {"proposed_amount": 499}}, cited)  # wrong plan
    assert not score_case(
        tv, state, ["[Netflix India enforced limits › Guardrail limits]\n..."]
    )  # page not used
    assert not score_case(tv, {**state, "razorpay_payload": None}, cited)  # no link


def test_offline_engine_picks_the_plan_the_customer_named(client):
    netflix = next(c for c in CASES if c["scenario_type"] == "NETFLIX_TV_PLAN_DOWNGRADE")
    ids = {k: netflix[k] for k in ("merchant_id", "customer_id", "invoice_id")}

    def offer(text):
        body = {**ids, "messages": [{"role": "user", "content": text}]}
        return client.post("/api/chat", json=body).json()["proposed_offer"]["proposed_amount"]

    assert offer("Please switch me to the Basic plan.") == 199.0
    assert offer("Can I move to a cheaper plan?") == 499.0  # unnamed: the priciest cheaper plan
