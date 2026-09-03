from typing import Dict, Any
from app.agents.state import AutonomeState
from app.rag.retriever import retriever

def rag_node(state: AutonomeState) -> AutonomeState:
    """
    Policy RAG Node: Retrieves merchant-specific settlement policies.
    """
    merchant_id = state.get("merchant_id", "hotstar")
    customer_intent = state.get("customer_intent", "STANDARD_RECOVERY")
    messages = state.get("messages", [])
    last_msg = messages[-1]["content"] if messages else customer_intent

    query = f"{customer_intent} {last_msg}"
    chunks = retriever.retrieve_context(merchant_id=merchant_id, query=query, top_k=2)

    state["retrieved_policy_chunks"] = chunks
    state["step"] = "RAG_RETRIEVED"
    return state
