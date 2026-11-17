import re

from app.agents.state import AutonomeState

# First match wins, so the most specific intents come first.
INTENT_RULES = [
    (
        "BILLING_DISPUTE",
        r"\b(fraud\w*|unauthori[sz]ed|never (authori[sz]ed|signed)|wrong(ly)? charged|not my charge)\b",
    ),
    ("CANCELLATION", r"\b(cancel\w*|discontinue|don'?t renew|stop (my|the) (plan|subscription))\b"),
    ("GOODS_DISPUTE", r"\b(dispute\w*|damaged|defective|quality issue|undisputed)\b"),
    ("SPLIT_REQUEST", r"\b(split|50/50|instal+ments?|milestone|tranche|stages?|staged|halves)\b"),
    (
        "DOWNGRADE_REQUEST",
        r"\b(downgrade|cheaper|cheapest|lighter plan|lower tier|smaller plan|(switch|move) (me )?to)\b",
    ),
    ("PAUSE_REQUEST", r"\b(pause|travel+ing|on hold|hold (my|access))\b"),
    ("BUDGET_FRICTION", r"\b(afford|expensive|tight|budget|cash ?flow|payday|salary)\b"),
    ("TECHNICAL_GATEWAY_FAILURE", r"\b(bank|gateway|time[sd]? ?out|server|upi|mandate|declined)\b"),
]
_COMPILED = [(intent, re.compile(pattern, re.IGNORECASE)) for intent, pattern in INTENT_RULES]


def classify_intent(message: str, failure_code: str) -> str:
    for intent, pattern in _COMPILED:
        if pattern.search(message):
            return intent
    return f"STANDARD_RECOVERY_{failure_code}"


def triage_node(state: AutonomeState) -> AutonomeState:
    """Classify the customer's intent from their latest message (keyword rules, no LLM)."""
    messages = state.get("messages", [])
    last_user_msg = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
    state["customer_intent"] = classify_intent(last_user_msg, state.get("failure_code", "UNKNOWN_FAILURE"))
    state["step"] = "TRIAGED"
    return state
