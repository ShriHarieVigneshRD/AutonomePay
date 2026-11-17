"""Settlement node: reason over the merchant policy with the LLM, enforce guardrails,
handle escalation and discontinuation, and create the Razorpay payment link."""

import time
import uuid

from app.agents.settlement.offer import (
    amount_stated_in_message,
    heuristic_offer,
    is_asking_for_confirmation,
    is_initial_turn,
    parse_llm_json,
    strip_markdown,
    user_gave_consent,
)
from app.agents.settlement.prompt import build_settlement_prompt
from app.agents.state import AutonomeState
from app.core.database import Merchant, SessionLocal
from app.core.llm_gateway import gateway
from app.guardrails.input_guard import run_pre_llm_guardrail
from app.guardrails.offer_guard import run_post_llm_guardrail
from app.payments.razorpay import razorpay_mcp


def settlement_node(state: AutonomeState) -> AutonomeState:
    start_time = time.time()
    messages = state.get("messages", [])
    last_user_msg = messages[-1]["content"] if messages else "Hello"

    # 1. Input guardrail
    pre_check = run_pre_llm_guardrail(last_user_msg)
    if not pre_check["passed"]:
        state["guardrail_status"] = "ADVERSARIAL_INTERCEPTED"
        state["guardrail_violations"] = [pre_check["refusal_reason"]]
        state["final_response"] = pre_check["safe_response"]
        state["step"] = "GUARDRAIL_INTERCEPTED"
        state["latency_ms"] = round((time.time() - start_time) * 1000, 2)
        return state

    merchant_id = state.get("merchant_id", "hotstar")
    original_amount = float(state.get("original_amount", 299.00))
    intent = state.get("customer_intent", "STANDARD_RECOVERY")

    with SessionLocal() as db:
        merchant = db.get(Merchant, merchant_id)
        max_discount_inr = (
            float(merchant.max_discount_inr) if merchant and merchant.max_discount_inr is not None else 20.00
        )
        max_grace_days = (
            int(merchant.max_grace_days) if merchant and merchant.max_grace_days is not None else 7
        )
        merchant_name = state.get("merchant_name") or (
            merchant.name if merchant else merchant_id.replace("_", " ").title()
        )

    # 2. Ask the LLM for a structured offer
    system_prompt = build_settlement_prompt(
        merchant_name=merchant_name,
        original_amount=original_amount,
        intent=intent,
        max_discount_inr=max_discount_inr,
        max_grace_days=max_grace_days,
        policy_context="\n".join(state.get("retrieved_policy_chunks", [])),
    )
    session_id = state.get("session_id") or f"sess_{merchant_id}_{uuid.uuid4().hex[:6]}"
    llm_res = gateway.completion(messages=messages, system_prompt=system_prompt, session_id=session_id)
    raw_content = llm_res.get("content", "")

    parsed = parse_llm_json(raw_content) or heuristic_offer(
        last_user_msg, raw_content, original_amount, max_discount_inr, max_grace_days
    )
    action = parsed.get("action", "PROPOSE_SETTLEMENT")
    offer = parsed.get("offer", {})
    offer["original_amount"] = original_amount
    if "proposed_amount" not in offer or float(offer.get("proposed_amount", 0)) <= 0:
        offer["proposed_amount"] = original_amount

    # 3. Offer guardrail
    post_check = run_post_llm_guardrail(
        offer_data=offer, max_discount_inr=max_discount_inr, max_grace_days=max_grace_days, action=action
    )
    corrected_offer = post_check["corrected_offer"]
    state["proposed_offer"] = corrected_offer
    state["guardrail_violations"] = post_check["violations"]
    state["guardrail_status"] = "POLICY_BREACH_CORRECTED" if post_check["violations"] else "PASSED"

    # 4. Message clean-up and price alignment
    should_generate_link = bool(parsed.get("should_generate_link", False))
    cust_message = strip_markdown(parsed.get("message", "Here is your response."))

    final_amount = corrected_offer["proposed_amount"]
    stated = amount_stated_in_message(
        cust_message, action, corrected_offer["proposed_amount"], original_amount, max_discount_inr
    )
    if stated is not None:
        final_amount = stated
        state["proposed_offer"]["proposed_amount"] = final_amount

    # 5. Link gating
    if is_asking_for_confirmation(cust_message) or (
        is_initial_turn(messages) and not user_gave_consent(last_user_msg)
    ):
        should_generate_link = False

    if action == "HUMAN_ESCALATION":
        state["step"] = "HUMAN_ESCALATED"
        state["razorpay_payload"] = None
    elif action == "GRACEFUL_DISCONTINUATION":
        state["step"] = "DISCONTINUATION_ACCEPTED"
        state["razorpay_payload"] = None
    elif should_generate_link:
        mcp_result = razorpay_mcp.razorpay_create_payment_link(
            amount_in_inr=final_amount,
            customer_id=state.get("customer_id", "cust_123"),
            description=f"Settlement payment for invoice {state.get('invoice_id', 'inv_101')}",
        )
        state["razorpay_payload"] = mcp_result
        link_url = mcp_result.get("short_url", "https://rzp.io/i/mocklink")
        if "rzp.io" not in cust_message and "http" not in cust_message:
            cust_message += f"\n\n[ Pay INR {final_amount:.2f} via Razorpay ]({link_url})"
    else:
        state["razorpay_payload"] = None

    state["final_response"] = cust_message
    state["latency_ms"] = round((time.time() - start_time) * 1000, 2)
    return state
