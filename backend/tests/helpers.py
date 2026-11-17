"""Plain helpers shared by tests."""

HOTSTAR = {"merchant_id": "hotstar", "customer_id": "cust_hotstar_01", "invoice_id": "inv_hotstar_101"}
NOTION = {"merchant_id": "notion_saas", "customer_id": "cust_notion_01", "invoice_id": "inv_notion_202"}
GREETING = {"role": "assistant", "content": "Hi Aarav, your renewal of INR 299.00 did not go through."}

CHAT_RESPONSE_KEYS = {
    "final_response",
    "guardrail_status",
    "guardrail_violations",
    "retrieved_policy_chunks",
    "proposed_offer",
    "razorpay_payload",
    "latency_ms",
    "token_spend",
}


def chat_body(*user_turns, ids=HOTSTAR, greeting=GREETING):
    """Build a /api/chat body: greeting followed by alternating user turns."""
    messages = [greeting]
    for i, turn in enumerate(user_turns):
        if i:
            messages.append({"role": "assistant", "content": "Noted."})
        messages.append({"role": "user", "content": turn})
    return {**ids, "messages": messages}


def settlement(
    action="PROPOSE_SETTLEMENT", amount=279.0, message="Your net amount is INR 279.00.", link=True, **offer
):
    """An LLM JSON reply in the shape the settlement prompt asks for."""
    return {
        "action": action,
        "reasoning": "test",
        "should_generate_link": link,
        "offer": {
            "proposed_amount": amount,
            "discount_inr": 20.0,
            "grace_days": 0,
            "split_amounts": [],
            **offer,
        },
        "message": message,
    }
