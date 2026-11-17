"""Pure helpers: parse the LLM reply, decide on consent, and keep the customer message
consistent with the guardrail-approved offer."""

import json
import re
from typing import Any

from app.core.catalog import MerchantRules
from app.guardrails.offer_guard import TOLERANCE_INR

CONFIRMATION_QUESTIONS = (
    "once you confirm",
    "shall i",
    "would you like me to",
    "confirm so i can",
    "let me know if you'd like",
    "before i issue",
    "please confirm",
    "would you like to proceed",
    "do you want me to",
)
# Word-bounded so "payment" never counts as "pay" (B26).
_CONSENT = re.compile(
    r"\b(yes|yeah|yep|sure|ok(ay)?|confirm(ed)?|proceed|go ahead|accept(ed)?|agree(d)?|"
    r"sounds (good|fair|great|perfect)|let'?s do (it|that)|set (that|it) up|downgrade me|"
    r"i(?:'ll| will) pay|pay now|send\b[^.?!]{0,25}\blink|issue\b[^.?!]{0,25}\blink|generate\b[^.?!]{0,25}\blink)\b",
    re.IGNORECASE,
)
_NEGATION = re.compile(r"\b(no|not|don'?t|do not|can'?t|cannot|won'?t|never)\b", re.IGNORECASE)
_YES = re.compile(r"\byes\b", re.IGNORECASE)
INR_AMOUNT = re.compile(r"(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d+)?)", re.IGNORECASE)
_URL = re.compile(r"\[([^\]]*)\]\((https?://[^)]+)\)|https?://\S+")


def parse_llm_json(raw_content: str) -> dict[str, Any] | None:
    match = re.search(r"\{.*\}", raw_content or "", re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
    except ValueError:
        return None
    return parsed if isinstance(parsed, dict) else None


def user_gave_consent(message: str) -> bool:
    if not _CONSENT.search(message):
        return False
    return not (_NEGATION.search(message) and not _YES.search(message))


def is_asking_for_confirmation(message: str) -> bool:
    lower = message.lower()
    return any(phrase in lower for phrase in CONFIRMATION_QUESTIONS)


def strip_markdown(message: str) -> str:
    message = re.sub(r"^\s*#{1,6}\s+", "", message, flags=re.MULTILINE)
    return re.sub(r"\*\*([^*]+)\*\*", r"\1", message)


def strip_urls(message: str) -> str:
    """The LLM must never hand out links; only the payment tool creates them."""
    return _URL.sub(lambda m: m.group(1) or "", message).strip()


def stated_amounts(message: str) -> list[float]:
    amounts = []
    for raw in INR_AMOUNT.findall(message):
        try:
            amounts.append(float(raw.replace(",", "")))
        except ValueError:
            continue
    return amounts


def legitimate_amounts(rules: MerchantRules, original_amount: float, offer: dict[str, Any]) -> list[float]:
    figures = [
        original_amount,
        offer.get("proposed_amount", 0.0),
        offer.get("discount_inr", 0.0),
        rules.max_discount_inr,
        *offer.get("split_amounts", []),
        *(p.price_inr for p in rules.plans),
    ]
    if rules.split_allowed(original_amount):
        figures += rules.split_amounts(original_amount)
    partial = rules.partial_amount(original_amount)
    if partial:
        figures += [partial, round(original_amount - partial, 2)]
    return [float(f) for f in figures if f]


def unapproved_amounts(message: str, allowed: list[float]) -> list[float]:
    return [a for a in stated_amounts(message) if not any(abs(a - b) <= TOLERANCE_INR for b in allowed)]


def approved_offer_message(action: str, offer: dict[str, Any], rules: MerchantRules) -> str:
    """Deterministic wording for an approved offer (used when the LLM's text can't be trusted)."""
    amount, original = offer["proposed_amount"], offer["original_amount"]
    if action == "PLAN_DOWNGRADE":
        plan = next(
            (p.name for p in rules.plans if abs(p.price_inr - amount) <= TOLERANCE_INR), "a lighter plan"
        )
        text = f"I can move you to the {plan} at INR {amount:,.2f}."
    elif action == "MILESTONE_SPLIT" and offer.get("split_amounts"):
        rest = " and ".join(f"INR {s:,.2f}" for s in offer["split_amounts"][1:])
        text = f"You can pay in instalments: INR {amount:,.2f} now, then {rest} later."
    elif action == "PARTIAL_SETTLEMENT":
        text = (
            f"You can pay the undisputed portion now: INR {amount:,.2f}. "
            "The disputed balance stays on hold until it's resolved."
        )
    elif offer.get("discount_inr"):
        text = (
            f"I can take INR {offer['discount_inr']:,.2f} off: you'd pay INR {amount:,.2f} "
            f"instead of INR {original:,.2f}."
        )
    else:
        text = f"The amount due is INR {amount:,.2f}."
    if offer.get("grace_days"):
        text += f" I can also give you {offer['grace_days']} extra days to pay."
    return text


def heuristic_offer(last_user_msg: str, rules: MerchantRules, original_amount: float) -> dict[str, Any]:
    """Keyword-based reply used when the LLM is unavailable or its reply is unusable."""
    lower = last_user_msg.lower()
    consent = user_gave_consent(last_user_msg)
    lower_plans = rules.lower_plans(original_amount)
    partial = rules.partial_amount(original_amount)

    if any(w in lower for w in ("cancel", "discontinue", "don't renew", "stop my")):
        return _reply("GRACEFUL_DISCONTINUATION", original_amount, False,
                      "Understood. I'll respect your decision and won't proceed with a payment request. "
                      "If you'd like to return in the future, we'll be happy to help.")  # fmt: skip
    if any(w in lower for w in ("fraud", "unauthori", "escalate", "specialist", "human")):
        return _reply("HUMAN_ESCALATION", original_amount, False,
                      "I've escalated this to a human specialist with ticket {TICKET}. "
                      "They'll reach out within 24 hours.")  # fmt: skip
    if partial and any(w in lower for w in ("damaged", "dispute", "undisputed", "holding", "hold the")):
        return _reply("PARTIAL_SETTLEMENT", partial, consent,
                      f"We can hold the disputed portion and settle the undisputed balance of INR {partial:,.2f} now.")  # fmt: skip
    if any(w in lower for w in ("split", "50/50", "instal", "milestone", "tranche")):
        if rules.split_allowed(original_amount):
            parts = rules.split_amounts(original_amount)
            schedule = "/".join(f"{pct:g}" for pct in rules.split_schedule_pct)
            later = " and ".join(f"INR {p:,.2f}" for p in parts[1:])
            return _reply("MILESTONE_SPLIT", parts[0], consent,
                          f"We can do a {schedule} split: INR {parts[0]:,.2f} now and {later} later.",
                          split_amounts=parts)  # fmt: skip
        return _reply("PROPOSE_SETTLEMENT", original_amount, False,
                      f"{rules.name}'s policy doesn't allow split payments for this invoice, but I can give you "
                      f"up to {rules.max_grace_days} extra days to pay the full amount.", question=False)  # fmt: skip
    if lower_plans and any(
        w in lower for w in ("downgrade", "cheaper", "lighter", "lower tier", "smaller plan")
    ):
        plan = max(lower_plans, key=lambda p: p.price_inr)
        return _reply("PLAN_DOWNGRADE", plan.price_inr, consent,
                      f"I can move you to the {plan.name} at INR {plan.price_inr:,.2f}.")  # fmt: skip

    grace = min(3, rules.max_grace_days)
    if rules.max_discount_inr > 0:
        amount = round(original_amount - rules.max_discount_inr, 2)
        text = (
            f"Based on {rules.name}'s policy I can take INR {rules.max_discount_inr:,.2f} off: you'd pay "
            f"INR {amount:,.2f} instead of INR {original_amount:,.2f}, with up to {rules.max_grace_days} "
            "extra days if you need them."
        )
    else:
        amount = original_amount
        text = (
            f"{rules.name} doesn't offer discounts, but I can give you up to {rules.max_grace_days} extra days, "
            f"or a fresh link for INR {original_amount:,.2f} to retry now."
        )
    return _reply("PROPOSE_SETTLEMENT", amount, consent, text, grace_days=grace)


def _reply(
    action: str, amount: float, link: bool, message: str, question: bool = True, **offer: Any
) -> dict[str, Any]:
    if question and not link and action not in ("GRACEFUL_DISCONTINUATION", "HUMAN_ESCALATION"):
        message += " Would you like me to send the payment link?"
    return {
        "action": action,
        "reasoning": "Offline policy heuristic (LLM unavailable or reply unusable).",
        "should_generate_link": link,
        "offer": {"proposed_amount": amount, "grace_days": 0, "split_amounts": [], **offer},
        "message": message,
    }
