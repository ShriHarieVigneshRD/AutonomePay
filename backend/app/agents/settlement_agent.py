import re
import json
import time
import uuid
from typing import Dict, Any

from app.agents.state import AutonomeState
from app.guardrails.pre_guardrails import run_pre_llm_guardrail
from app.guardrails.post_guardrails import run_post_llm_guardrail
from app.mcp.razorpay_mcp_client import razorpay_mcp
from app.core.gateway import gateway
from app.core.database import SessionLocal, Merchant

def settlement_node(state: AutonomeState) -> AutonomeState:
    """
    Autonomous Settlement Agent Node:
    Reason over retrieved merchant policies via LLM, enforce mathematical guardrails,
    handle Human Escalations & Graceful Discontinuations, and generate Razorpay MCP payment links.
    """
    start_time = time.time()
    messages = state.get("messages", [])
    last_user_msg = messages[-1]["content"] if messages else "Hello"

    # 1. Pre-LLM Guardrail Check
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
    policy_chunks = state.get("retrieved_policy_chunks", [])
    intent = state.get("customer_intent", "STANDARD_RECOVERY")

    # Fetch Merchant constraints from Database
    db = SessionLocal()
    merchant = db.query(Merchant).filter(Merchant.merchant_id == merchant_id).first()
    max_discount_pct = float(merchant.max_discount_pct) if merchant else 5.00
    max_grace_days = int(merchant.max_grace_days) if merchant else 7
    db.close()

    combined_policy = "\n".join(policy_chunks)

    # 2. Construct Prompt with Human Escalation, Discontinuation, Downgrade & Intent Rules
    system_prompt = f"""You are AutonomePay, an autonomous revenue recovery concierge for merchant '{merchant_id}'.
Original Invoice Amount: INR {original_amount:.2f}
Customer Intent: {intent}
Merchant Policy Constraints: Max Discount = {max_discount_pct}%, Max Grace Days = {max_grace_days}.
Retrieved Policy Context:
{combined_policy}

INSTRUCTIONS:
1. PLAN DOWNGRADE VS RENEWAL DISCOUNT:
   - If customer asks to downgrade or when offering a lower plan tier (e.g. Mobile Plan at INR 149.00), set action="PLAN_DOWNGRADE", proposed_amount=149.00, and discount_pct=0.0 (full price for lower plan tier).
   - If offering a discount on current plan (e.g. INR 20 off Super Plan -> 279.00), set action="PROPOSE_SETTLEMENT".

2. HUMAN ESCALATION CRITERIA:
   Set action="HUMAN_ESCALATION" and should_generate_link=false if ANY of the following occur:
   a) Customer disputes invoice amount or claims unauthorized/fraudulent payment.
   b) Situation is not covered by merchant policy or contains conflicting rules.
   c) Invoice amount is high-value (> INR 50,000) requiring manual clearance.
   d) Customer remains repeatedly frustrated or hostile after options are presented.
   In escalation cases, explain politely that your case has been escalated to a human specialist with Ticket #ESC-{uuid.uuid4().hex[:6].upper()} who will reach out within 24 hours.

3. GRACEFUL DISCONTINUATION CRITERIA:
   Set action="GRACEFUL_DISCONTINUATION" and should_generate_link=false if:
   a) Customer decides to discontinue, cancel, or stop their plan (e.g. "I want to cancel", "I will discontinue", "Don't renew").
   Do NOT force them into payment requests. Respond gracefully with text similar to:
   "Understood. I'll respect your decision and won't proceed with a payment request. Your subscription will be marked for discontinuation. If you'd like to return in the future, we'll be happy to help."

4. TEXT FORMATTING RULES:
   Do NOT use raw Markdown hashtags (# or ##) or ugly raw asterisks (like **Text**) in bullet points. Use clean, plain bullet points (1., 2., 3. or - ) with standard title casing so text renders cleanly in message bubbles.

5. LLM INTENT CONFIRMATION & TOOL CALL CONTROL ("should_generate_link"):
   - Set "should_generate_link" to true ONLY AFTER the customer confirms, selects an option, accepts an offer, or agrees to pay.
   - Set "should_generate_link" to false WHEN asking the customer to confirm or present options.

Output MUST be valid JSON with structure:
{{
  "action": "PROPOSE_SETTLEMENT" | "PLAN_DOWNGRADE" | "HUMAN_ESCALATION" | "GRACEFUL_DISCONTINUATION" | "EXTEND_GRACE" | "PAUSE_PLAN",
  "reasoning": "explanation citing relevant rule",
  "should_generate_link": false,
  "offer": {{
    "proposed_amount": 149.00,
    "discount_pct": 0.0,
    "grace_days": 0,
    "split_amounts": []
  }},
  "message": "Customer-facing response text"
}}
"""

    # 3. Call LiteLLM Gateway
    llm_res = gateway.completion(messages=messages, system_prompt=system_prompt)
    raw_content = llm_res.get("content", "")

    # Clean JSON output if wrapped in markdown code blocks
    cleaned_json = raw_content
    if "```json" in raw_content:
        cleaned_json = raw_content.split("```json")[1].split("```")[0].strip()
    elif "```" in raw_content:
        cleaned_json = raw_content.split("```")[1].split("```")[0].strip()

    try:
        parsed = json.loads(cleaned_json)
    except Exception:
        disc_val = min(max_discount_pct, 5.0)
        target_amt = round(original_amount * (1.0 - (disc_val / 100.0)), 2)
        parsed = {
            "action": "PROPOSE_SETTLEMENT",
            "reasoning": "Standard policy offer",
            "should_generate_link": False,
            "offer": {
                "proposed_amount": target_amt,
                "discount_pct": disc_val,
                "grace_days": min(3, max_grace_days),
                "split_amounts": []
            },
            "message": raw_content if raw_content and not raw_content.startswith("{") else f"Based on policy, we can offer a settlement of INR {target_amt:.2f}. Would you like me to issue the payment link?"
        }

    action = parsed.get("action", "PROPOSE_SETTLEMENT")
    offer = parsed.get("offer", {})
    offer["original_amount"] = original_amount

    if "proposed_amount" not in offer or float(offer.get("proposed_amount", 0)) <= 0:
        offer["proposed_amount"] = original_amount

    # 4. Post-LLM Invariant Guardrail Verification
    post_check = run_post_llm_guardrail(
        offer_data=offer,
        max_discount_pct=max_discount_pct,
        max_grace_days=max_grace_days,
        action=action
    )

    corrected_offer = post_check["corrected_offer"]
    state["proposed_offer"] = corrected_offer
    state["guardrail_violations"] = post_check["violations"]
    state["guardrail_status"] = "POLICY_BREACH_CORRECTED" if post_check["violations"] else "PASSED"

    # 5. Handle Action States & Exact Price Alignment
    should_generate_link = bool(parsed.get("should_generate_link", False))
    cust_message = parsed.get("message", "Here is your response.")

    # Clean up any leftover Markdown hashtags or raw bold asterisks in message
    cust_message = re.sub(r"^\s*#{1,6}\s+", "", cust_message, flags=re.MULTILINE)
    cust_message = re.sub(r"\*\*([^*]+)\*\*", r"\1", cust_message)

    # Price Alignment Guardrail: Ensure button amount matches net price stated in message text
    final_amount = corrected_offer["proposed_amount"]
    inr_matches = re.findall(r"INR\s*(\d+(?:\.\d+)?)", cust_message, re.IGNORECASE)
    if inr_matches:
        valid_prices = [float(p) for p in inr_matches if float(p) > 0 and float(p) <= original_amount]
        if valid_prices:
            final_amount = valid_prices[-1]
            state["proposed_offer"]["proposed_amount"] = final_amount

    # Confirmation Deferral Gate: If text is asking for customer confirmation, defer link creation until customer confirms
    asking_for_confirmation = any(phrase in cust_message.lower() for phrase in [
        "once you confirm", "shall i", "would you like me to", "confirm so i can",
        "let me know if you'd like", "before i issue", "please confirm", "shall i proceed"
    ])

    if asking_for_confirmation:
        should_generate_link = False

    if action == "HUMAN_ESCALATION":
        should_generate_link = False
        state["step"] = "HUMAN_ESCALATED"
        state["escalated"] = True
        state["razorpay_payload"] = None

    elif action == "GRACEFUL_DISCONTINUATION":
        should_generate_link = False
        state["step"] = "DISCONTINUATION_ACCEPTED"
        state["razorpay_payload"] = None

    elif should_generate_link:
        mcp_result = razorpay_mcp.razorpay_create_payment_link(
            amount_in_inr=final_amount,
            customer_id=state.get("customer_id", "cust_123"),
            description=f"Settlement payment for invoice {state.get('invoice_id', 'inv_101')}"
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
