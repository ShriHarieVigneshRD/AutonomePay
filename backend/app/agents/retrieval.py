from app.agents.state import AutonomeState
from app.core.config import settings
from app.rag.retriever import NOT_FOUND, retriever

# Triage intents are labels, not words; these terms steer retrieval toward the matching rules.
INTENT_TERMS = {
    "BUDGET_FRICTION": "discount concession renewal afford",
    "SPLIT_REQUEST": "split instalment milestone payment",
    "DOWNGRADE_REQUEST": "downgrade plan cheaper plans pricing",
    "PAUSE_REQUEST": "pause grace period extension",
    "GOODS_DISPUTE": "dispute damaged undisputed hold portion",
    "BILLING_DISPUTE": "escalation dispute unauthorized",
    "CANCELLATION": "cancel cancellation discontinue",
    "TECHNICAL_GATEWAY_FAILURE": "payment failed retry gateway bank declined",
}


def rag_node(state: AutonomeState) -> AutonomeState:
    """Retrieve the merchant's most relevant policy passages for the customer's latest message."""
    intent = state.get("customer_intent", "")
    messages = state.get("messages", [])
    last_user_msg = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
    query = f"{last_user_msg} {INTENT_TERMS.get(intent, 'payment failed grace retry')}"

    hits = retriever.search(state.get("merchant_id", ""), query, top_k=settings.RAG_TOP_K)
    state["retrieved_policy_chunks"] = [chunk.labelled() for chunk, _ in hits] or [NOT_FOUND]
    state["retrieved_sources"] = [{**chunk.citation(), "score": round(score, 4)} for chunk, score in hits]
    state["step"] = "RAG_RETRIEVED"
    return state
