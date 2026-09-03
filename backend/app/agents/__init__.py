from langgraph.graph import StateGraph, START, END
from app.agents.state import AutonomeState
from app.agents.triage_agent import triage_node
from app.agents.rag_agent import rag_node
from app.agents.settlement_agent import settlement_node

def create_autonomepay_graph():
    builder = StateGraph(AutonomeState)

    # Add Nodes
    builder.add_node("triage", triage_node)
    builder.add_node("rag", rag_node)
    builder.add_node("settlement", settlement_node)

    # Define Edges
    builder.add_edge(START, "triage")
    builder.add_edge("triage", "rag")
    builder.add_edge("rag", "settlement")
    builder.add_edge("settlement", END)

    return builder.compile()

autonomepay_graph = create_autonomepay_graph()
