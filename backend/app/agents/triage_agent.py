from typing import Dict, Any
from app.agents.state import AutonomeState

def triage_node(state: AutonomeState) -> AutonomeState:
    """
    Triage Node: Classifies payment failure codes & customer intent.
    """
    failure_code = state.get("failure_code", "UNKNOWN_FAILURE")
    messages = state.get("messages", [])
    last_user_msg = messages[-1]["content"] if messages else ""

    msg_lower = last_user_msg.lower()

    if "afford" in msg_lower or "expensive" in msg_lower or "tight" in msg_lower or "budget" in msg_lower:
        intent = "BUDGET_FRICTION"
    elif "bank" in msg_lower or "gateway" in msg_lower or "failed" in msg_lower or "timeout" in msg_lower:
        intent = "TECHNICAL_GATEWAY_FAILURE"
    elif "dispute" in msg_lower or "damaged" in msg_lower or "quality" in msg_lower:
        intent = "GOODS_DISPUTE"
    elif "pause" in msg_lower or "traveling" in msg_lower or "hold" in msg_lower:
        intent = "PAUSE_REQUEST"
    else:
        intent = f"STANDARD_RECOVERY_{failure_code}"

    state["customer_intent"] = intent
    state["step"] = "TRIAGED"
    return state
