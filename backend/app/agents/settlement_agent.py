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
    max_discount_inr = float(merchant.max_discount_inr) if (merchant and merchant.max_discount_inr is not None) else 20.00
    max_grace_days = int(merchant.max_grace_days) if merchant else 7
    db.close()

    combined_policy = "\n".join(policy_chunks)

    # 2. Construct Prompt with Human Escalation, Discontinuation, Downgrade & Intent Rules
    system_prompt = f"""You are AutonomePay, an autonomous revenue recovery concierge for merchant '{merchant_id}'.
Original Invoice Amount: INR {original_amount:.2f}
Customer Intent: {intent}
Merchant Policy Constraints: Max Discount Limit = INR {max_discount_inr:.2f}, Max Grace Days = {max_grace_days}.
Retrieved Policy Context:
{combined_policy}

INSTRUCTIONS:
1. PLAN DOWNGRADE VS RENEWAL DISCOUNT:
   - If customer asks to downgrade or select a lighter tier plan, use ONLY plan options present in Retrieved Policy Context or Merchant Policy.
   - If offering a renewal discount on current plan, set action="PROPOSE_SETTLEMENT" and proposed_amount = {original_amount - max_discount_inr:.2f}.
   - If offering a milestone split payment (e.g. 50/50 split), set action="MILESTONE_SPLIT" and proposed_amount = {original_amount / 2.0:.2f}.

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
   - Set "should_generate_link" to true ONLY WHEN the customer explicitly confirms, selects an option, accepts an offer, or agrees to pay.
   - Set "should_generate_link" to false WHEN the customer is notifying of payment failure, asking questions, exploring options, or when you are asking for confirmation.

Output MUST be valid JSON with structure:
{{
  "action": "PROPOSE_SETTLEMENT" | "PLAN_DOWNGRADE" | "HUMAN_ESCALATION" | "GRACEFUL_DISCONTINUATION" | "EXTEND_GRACE" | "MILESTONE_SPLIT",
  "reasoning": "explanation citing relevant rule",
  "should_generate_link": false,
  "offer": {{
    "proposed_amount": 279.00,
    "discount_inr": {max_discount_inr:.2f},
    "grace_days": 0,
    "split_amounts": []
  }},
  "message": "Customer-facing response text"
}}
"""

    # 3. Call LiteLLM Gateway
    session_id = state.get("session_id") or f"sess_{merchant_id}_{uuid.uuid4().hex[:6]}"
    llm_res = gateway.completion(messages=messages, system_prompt=system_prompt, session_id=session_id)
    raw_content = llm_res.get("content", "")

    # Robust JSON Parsing using regex extraction
    parsed = None
    json_match = re.search(r"\{.*\}", raw_content, re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group(0))
        except Exception:
            pass

    if not parsed:
        lower_msg = last_user_msg.lower()

        if any(w in lower_msg for w in ["downgrade", "lighter plan", "lower tier"]):
            action = "PLAN_DOWNGRADE"
            target_amt = max(1.0, round(original_amount * 0.5, 2))
            should_gen = any(w in lower_msg for w in ["yes", "confirm", "proceed", "please"])
            cust_text = "I've noted your request for a plan downgrade. Would you like me to process this switch?" if not should_gen else "Your plan downgrade is confirmed."
        elif any(w in lower_msg for w in ["split", "50/50", "installment", "milestone"]):
            action = "MILESTONE_SPLIT"
            target_amt = round(original_amount / 2.0, 2)
            should_gen = any(w in lower_msg for w in ["yes", "confirm", "proceed", "please", "set that up"])
            cust_text = f"We can set up a 50/50 split milestone payment: INR {target_amt:.2f} today and INR {target_amt:.2f} later. Would you like me to generate the payment link?"
        elif any(w in lower_msg for w in ["cancel", "discontinue", "stop"]):
            action = "GRACEFUL_DISCONTINUATION"
            target_amt = original_amount
            should_gen = False
            cust_text = "Understood. I'll respect your decision and won't proceed with a payment request."
        else:
            action = "PROPOSE_SETTLEMENT"
            target_amt = max(0.0, round(original_amount - max_discount_inr, 2))
            should_gen = any(w in lower_msg for w in ["yes", "confirm", "proceed", "pay", "send link"])
            cust_text = raw_content if raw_content and not raw_content.startswith("{") else f"We can help resolve your subscription payment. Based on our policy, we can offer a settlement of INR {target_amt:.2f}. Would you like to proceed?"

        parsed = {
            "action": action,
            "reasoning": "Heuristic intent classification",
            "should_generate_link": should_gen,
            "offer": {
                "proposed_amount": target_amt,
                "discount_inr": max_discount_inr,
                "grace_days": min(3, max_grace_days),
                "split_amounts": []
            },
            "message": cust_text
        }

    action = parsed.get("action", "PROPOSE_SETTLEMENT")
    offer = parsed.get("offer", {})
    offer["original_amount"] = original_amount

    if "proposed_amount" not in offer or float(offer.get("proposed_amount", 0)) <= 0:
        offer["proposed_amount"] = original_amount

    # 4. Post-LLM Invariant Guardrail Verification
    post_check = run_post_llm_guardrail(
        offer_data=offer,
        max_discount_inr=max_discount_inr,
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
    raw_inr_matches = re.findall(r"INR\s*([\d,]+(?:\.\d+)?)", cust_message, re.IGNORECASE)
    if raw_inr_matches:
        valid_prices = []
        for p in raw_inr_matches:
            try:
                val = float(p.replace(",", ""))
                if 0 < val <= original_amount:
                    valid_prices.append(val)
            except ValueError:
                pass
        if valid_prices:
            # Pick the lowest valid price mentioned (e.g. INR 7,500.00 for 50/50 split)
            final_amount = valid_prices[0] if action == "MILESTONE_SPLIT" else valid_prices[-1]
            state["proposed_offer"]["proposed_amount"] = final_amount

    # Deferral Safety Gate: If text is asking for customer confirmation, defer link creation until confirmed
    asking_for_confirmation = any(phrase in cust_message.lower() for phrase in [
        "once you confirm", "shall i", "would you like me to", "confirm so i can",
        "let me know if you'd like", "before i issue", "please confirm", "shall i proceed", "would you like to proceed"
    ])

    # Deferral Safety Gate 2: Initial payment failure notification turn without explicit pay/agreed intent
    is_initial_turn = len(messages) <= 1 or (len(messages) == 2 and messages[0].get("role") == "user")
    user_confirmed_pay = any(kw in last_user_msg.lower() for kw in ["confirm", "proceed", "yes", "pay", "accept", "agreed", "send link", "downgrade me"])

    if asking_for_confirmation or (is_initial_turn and not user_confirmed_pay):
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
