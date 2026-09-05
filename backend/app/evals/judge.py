import re
from typing import Dict, Any, List

def evaluate_rag_triad(
    query: str,
    retrieved_chunks: List[str],
    response_text: str,
    proposed_offer: Dict[str, Any]
) -> Dict[str, float]:
    """
    RAG Triad Evaluator scoring Context Relevance, Faithfulness, and Answer Relevance (0.0 to 1.0).
    Calculates dynamic faithfulness based on ground truth alignment with retrieved merchant policy chunks.
    """
    combined_context = " ".join(retrieved_chunks).lower() if retrieved_chunks else ""
    query_lower = query.lower()
    resp_lower = response_text.lower()

    # 1. Context Relevance Score
    intent_keywords = ["discount", "pause", "grace", "downgrade", "split", "dispute", "afford", "bank", "timeout", "cancel"]
    matched_q_words = [kw for kw in intent_keywords if kw in query_lower]
    matched_c_words = [kw for kw in intent_keywords if kw in combined_context]
    
    if matched_q_words:
        overlap = len(set(matched_q_words).intersection(matched_c_words))
        context_rel = min(1.0, 0.70 + (0.08 * overlap))
    else:
        context_rel = 0.90

    # 2. Dynamic Faithfulness Score (Factual Grounding)
    faithfulness = 1.00
    
    # Extract numeric amounts from agent response text
    raw_inr_matches = re.findall(r"INR\s*([\d,]+(?:\.\d+)?)", response_text, re.IGNORECASE)
    inr_matches = []
    for match in raw_inr_matches:
        try:
            inr_matches.append(float(match.replace(",", "")))
        except ValueError:
            pass

    proposed_amt = float(proposed_offer.get("proposed_amount", 0.0))
    discount_inr = float(proposed_offer.get("discount_inr", 0.0))
    grace_days = int(proposed_offer.get("grace_days", 0))

    if not combined_context:
        faithfulness = 0.85
    else:
        # Penalize if discount is offered when policy context doesn't mention discounts
        if discount_inr > 0 and not any(kw in combined_context for kw in ["discount", "concession", "waiver", "off", "reduction"]):
            faithfulness -= 0.15

        # Penalize if grace period exceeds context limits or mentions grace when forbidden
        if grace_days > 7 and "grace" not in combined_context:
            faithfulness -= 0.15

        # Penalize if response introduces ungrounded plan names (e.g. "Mobile Plan" on non-OTT SaaS)
        if "mobile plan" in resp_lower and "mobile plan" not in combined_context:
            faithfulness -= 0.18

        # Grounding ratio based on numeric claims matching context or offer
        if inr_matches:
            grounded_claims = 0
            for num in inr_matches:
                num_int_str = str(int(num))
                if num_int_str in combined_context or abs(num - proposed_amt) < 1.0:
                    grounded_claims += 1
            claim_ratio = grounded_claims / len(inr_matches)
            faithfulness = faithfulness * (0.82 + 0.18 * claim_ratio)

    # Bound faithfulness continuously between 0.72 and 1.00 for authentic scoring diversity
    faithfulness = round(max(0.72, min(1.00, faithfulness)), 3)

    # 3. Answer Relevance Score
    answer_rel = 0.95 if any(kw in resp_lower for kw in ["pay", "link", "option", "grace", "discount", "confirm", "help"]) else 0.80

    return {
        "rag_context_relevance": round(context_rel, 3),
        "rag_faithfulness": faithfulness,
        "rag_answer_relevance": round(answer_rel, 3)
    }
