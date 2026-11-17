"""Pure helpers: parse the LLM reply, decide on consent, and keep the customer message
consistent with the guardrail-approved offer."""

import json
import re
from typing import Any

from app.core.catalog import MerchantRules, Plan
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
GRACE_WORDS = (
    "pause",
    "grace",
    "extension",
    "extend",
    "more time",
    "extra days",
    "payday",
    "next week",
    "hold access",
)
_DAYS = re.compile(r"(\d+)\s*(?:-\s*|extra\s+|more\s+|additional\s+)?days?\b")
INR_AMOUNT = re.compile(r"(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d+)?)", re.IGNORECASE)
_URL = re.compile(r"\[([^\]]*)\]\((https?://[^)]+)\)|https?://\S+")


def parse_llm_json(raw_content: str) -> dict[str, Any] | None:
    """Extract the reply's JSON object, tolerating what free models actually send: code fences,
    prose around the object, raw newlines inside strings, and an unclosed final string."""
    text = raw_content or ""
    start = text.find("{")
    if start < 0:
        return None
    body = text[start:]
    end = body.rfind("}")
    for candidate in (body[: end + 1] if end >= 0 else None, body + '"}', body + "}"):
        if candidate is None:
            continue
        try:
            parsed = json.loads(candidate, strict=False)  # strict=False: allow raw newlines in strings
        except ValueError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


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
        round(original_amount - rules.max_discount_inr, 2) if rules.max_discount_inr else 0.0,
        rules.split_min_invoice_inr or 0.0,  # explaining why a split isn't available
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


def plan_label(name: str) -> str:
    """ "Basic" -> "Basic plan"; "Mobile Plan" stays as is."""
    return name if "plan" in name.lower() else f"{name} plan"


def approved_offer_message(action: str, offer: dict[str, Any], rules: MerchantRules) -> str:
    """Deterministic wording for an approved offer (used when the LLM's text can't be trusted)."""
    amount, original = offer["proposed_amount"], offer["original_amount"]
    if action == "PLAN_DOWNGRADE":
        plan = next((p.name for p in rules.plans if abs(p.price_inr - amount) <= TOLERANCE_INR), None)
        target = f"the {plan_label(plan)}" if plan else "a lighter plan"
        text = f"I can move you to {target} at INR {amount:,.2f}."
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


DOWNGRADE_WORDS = ("downgrade", "cheaper", "cheapest", "lighter", "lower tier", "smaller plan",
                   "switch me to", "move me to", "switch to the", "move to the")  # fmt: skip


def named_plan(message: str, plans: list[Plan]) -> Plan:
    """The plan the customer named (most shared words), else the priciest of the cheaper plans."""
    words = set(re.findall(r"[a-z]+", message.lower()))

    def overlap(plan: Plan) -> int:
        return len((set(re.findall(r"[a-z]+", plan.name.lower())) - {"plan"}) & words)

    return max(plans, key=lambda p: (overlap(p), p.price_inr))


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
    if any(w in lower for w in ("fraud", "unauthori", "never authori", "escalate", "specialist", "human")):
        return _reply("HUMAN_ESCALATION", original_amount, False,
                      "I've escalated this to a human specialist with ticket {TICKET}. "
                      "They'll reach out within 24 hours.")  # fmt: skip
    if partial and any(w in lower for w in ("damaged", "dispute", "undisputed", "holding", "hold the")):
        return _reply("PARTIAL_SETTLEMENT", partial, consent,
                      f"We can hold the disputed portion and settle the undisputed balance of INR {partial:,.2f} now.")  # fmt: skip
    if any(w in lower for w in ("split", "50/50", "instal", "milestone", "tranche", "stage")):
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
    if lower_plans and any(w in lower for w in DOWNGRADE_WORDS):
        plan = named_plan(lower, lower_plans)
        return _reply("PLAN_DOWNGRADE", plan.price_inr, consent,
                      f"I can move you to the {plan_label(plan.name)} at INR {plan.price_inr:,.2f}.")  # fmt: skip

    if rules.max_grace_days and any(w in lower for w in GRACE_WORDS):
        requested = _DAYS.search(lower)
        wanted = int(requested.group(1)) if requested else rules.max_grace_days
        days = max(1, min(wanted, rules.max_grace_days))
        text = f"I can give you {days} extra day{'s' if days > 1 else ''} to pay the full INR {original_amount:,.2f}."
        if wanted > rules.max_grace_days:
            text += f" That's the most {rules.name}'s policy allows."
        return _reply("EXTEND_GRACE", original_amount, consent, text, grace_days=days)

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
