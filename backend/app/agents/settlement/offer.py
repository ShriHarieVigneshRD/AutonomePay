"""Pure helpers for turning an LLM reply into an offer and deciding on the payment link."""

import json
import re
from typing import Any

CONFIRMATION_QUESTIONS = (
    "once you confirm",
    "shall i",
    "would you like me to",
    "confirm so i can",
    "let me know if you'd like",
    "before i issue",
    "please confirm",
    "shall i proceed",
    "would you like to proceed",
)
CONSENT_KEYWORDS = ("confirm", "proceed", "yes", "pay", "accept", "agreed", "send link", "downgrade me")
INR_AMOUNT = re.compile(r"INR\s*([\d,]+(?:\.\d+)?)", re.IGNORECASE)


def parse_llm_json(raw_content: str) -> dict[str, Any] | None:
    match = re.search(r"\{.*\}", raw_content, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def heuristic_offer(
    last_user_msg: str, raw_content: str, original_amount: float, max_discount_inr: float, max_grace_days: int
) -> dict[str, Any]:
    """Keyword-based fallback when the LLM reply is not usable JSON."""
    lower_msg = last_user_msg.lower()

    if any(w in lower_msg for w in ["downgrade", "lighter plan", "lower tier"]):
        action = "PLAN_DOWNGRADE"
        target_amt = max(1.0, round(original_amount * 0.5, 2))
        should_gen = any(w in lower_msg for w in ["yes", "confirm", "proceed", "please"])
        cust_text = (
            "Your plan downgrade is confirmed."
            if should_gen
            else "I've noted your request for a plan downgrade. Would you like me to process this switch?"
        )
    elif any(w in lower_msg for w in ["split", "50/50", "installment", "milestone"]):
        action = "MILESTONE_SPLIT"
        target_amt = round(original_amount / 2.0, 2)
        should_gen = any(w in lower_msg for w in ["yes", "confirm", "proceed", "please", "set that up"])
        cust_text = (
            f"We can set up a 50/50 split milestone payment: INR {target_amt:.2f} today and INR {target_amt:.2f} later. "
            "Would you like me to generate the payment link?"
        )
    elif any(w in lower_msg for w in ["cancel", "discontinue", "stop"]):
        action = "GRACEFUL_DISCONTINUATION"
        target_amt = original_amount
        should_gen = False
        cust_text = "Understood. I'll respect your decision and won't proceed with a payment request."
    else:
        action = "PROPOSE_SETTLEMENT"
        target_amt = max(0.0, round(original_amount - max_discount_inr, 2))
        should_gen = any(w in lower_msg for w in ["yes", "confirm", "proceed", "pay", "send link"])
        cust_text = (
            raw_content
            if raw_content and not raw_content.startswith("{")
            else "We can help resolve your subscription payment. Based on our policy, we can offer a settlement of "
            f"INR {target_amt:.2f}. Would you like to proceed?"
        )

    return {
        "action": action,
        "reasoning": "Heuristic intent classification",
        "should_generate_link": should_gen,
        "offer": {
            "proposed_amount": target_amt,
            "discount_inr": max_discount_inr,
            "grace_days": min(3, max_grace_days),
            "split_amounts": [],
        },
        "message": cust_text,
    }


def strip_markdown(message: str) -> str:
    message = re.sub(r"^\s*#{1,6}\s+", "", message, flags=re.MULTILINE)
    return re.sub(r"\*\*([^*]+)\*\*", r"\1", message)


def amount_stated_in_message(
    message: str, action: str, approved_amount: float, original_amount: float, max_discount_inr: float
) -> float | None:
    """Pick the INR amount from the message that the payment link should use, if any."""
    valid_prices = []
    for raw in INR_AMOUNT.findall(message):
        try:
            val = float(raw.replace(",", ""))
        except ValueError:
            continue
        if (0 < val <= original_amount and abs(val - max_discount_inr) > 0.01) or val == original_amount:
            valid_prices.append(val)
    if not valid_prices:
        return None
    if action == "MILESTONE_SPLIT":
        return valid_prices[0]
    return min(valid_prices, key=lambda x: abs(x - approved_amount))


def is_asking_for_confirmation(message: str) -> bool:
    lower = message.lower()
    return any(phrase in lower for phrase in CONFIRMATION_QUESTIONS)


def user_gave_consent(last_user_msg: str) -> bool:
    lower = last_user_msg.lower()
    return any(kw in lower for kw in CONSENT_KEYWORDS)


def is_initial_turn(messages: list[dict[str, str]]) -> bool:
    return len(messages) <= 1 or (len(messages) == 2 and messages[0].get("role") == "user")
