"""Tolerant parsing of LLM settlement replies (found in the live run against OpenRouter)."""

from app.agents.settlement.offer import parse_llm_json

GOOD = '{"action": "PLAN_DOWNGRADE", "should_generate_link": false, "offer": {"proposed_amount": 149}, "message": "Hi"}'


def test_plain_json():
    assert parse_llm_json(GOOD)["action"] == "PLAN_DOWNGRADE"


def test_code_fences_and_surrounding_prose():
    assert (
        parse_llm_json(f"Sure! Here it is:\n```json\n{GOOD}\n```\nLet me know.")["offer"]["proposed_amount"]
        == 149
    )


def test_raw_newlines_inside_the_message():
    raw = '{"action": "PROPOSE_SETTLEMENT", "offer": {"proposed_amount": 649}, "message": "Options:\n\n1. Grace\n2. Downgrade"}'
    assert parse_llm_json(raw)["message"].startswith("Options:\n\n1.")


def test_reply_that_never_closes_the_message():
    # Nemotron 3 Ultra (free) returned exactly this shape: the string and object are left open.
    raw = '{\n  "action": "PROPOSE_SETTLEMENT",\n  "should_generate_link": false,\n  "offer": {"proposed_amount": 649.0, "grace_days": 2},\n  "message": "Here are your options:\n\n1. Grace period\n2. Downgrade to Mobile: INR 149/month'
    parsed = parse_llm_json(raw)
    assert parsed["action"] == "PROPOSE_SETTLEMENT" and parsed["offer"]["grace_days"] == 2
    assert parsed["message"].endswith("INR 149/month")


def test_not_json_at_all():
    assert parse_llm_json("I can offer you a discount.") is None
    assert parse_llm_json("") is None
    assert parse_llm_json("[1, 2, 3]") is None
