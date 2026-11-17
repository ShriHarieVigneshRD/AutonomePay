"""Settlement node: ask the LLM for an offer within merchant policy, enforce the deterministic
guardrails, and create a payment link only for the approved amount and only with consent."""

import logging
import time
import uuid
from typing import Any

from app.agents.settlement.offer import (
    approved_offer_message,
    heuristic_offer,
    is_asking_for_confirmation,
    legitimate_amounts,
    parse_llm_json,
    strip_markdown,
    strip_urls,
    unapproved_amounts,
    user_gave_consent,
)
from app.agents.settlement.prompt import TICKET_PLACEHOLDER, build_settlement_prompt
from app.agents.state import AutonomeState
from app.core.catalog import MerchantRules, get_merchant_rules
from app.core.database import Customer, SessionLocal
from app.core.llm_gateway import gateway
from app.guardrails.input_guard import screen_conversation
from app.guardrails.offer_guard import NO_PAYMENT_ACTIONS, run_post_llm_guardrail
from app.payments import mcp_client
from app.payments.ledger import record_issued_link

logger = logging.getLogger(__name__)

BUDGET_MESSAGE = (
    "This conversation has reached its length limit. Please start a new conversation to continue."
)
LINK_FAILED_MESSAGE = "I couldn't create the payment link just now. Please try again in a moment."
# Why the backup rulebook answered instead of the LLM (shown in the benchmark trace).
RULEBOOK_REASONS = {
    "LLM_NOT_CONFIGURED": "no LLM key configured",
    "LLM_UNAVAILABLE": "every LLM in the chain failed",
    "RATE_LIMITED": "LLM rate limit (free tier)",
    "DAILY_LIMIT": "LLM daily free limit reached",
}
STEP_FOR_ACTION = {
    "HUMAN_ESCALATION": "HUMAN_ESCALATED",
    "GRACEFUL_DISCONTINUATION": "DISCONTINUATION_ACCEPTED",
}


def _finish(state: AutonomeState, start: float, **updates: Any) -> AutonomeState:
    state.update(updates)  # type: ignore[typeddict-item]
    state["latency_ms"] = round((time.time() - start) * 1000, 2)
    return state


def settlement_node(state: AutonomeState) -> AutonomeState:
    start = time.time()
    messages = state.get("messages", [])
    last_user_msg = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")

    # 1. Input guardrail over every user turn
    screen = screen_conversation(messages)
    if not screen["passed"]:
        return _finish(
            state, start,
            guardrail_status="ADVERSARIAL_INTERCEPTED",
            guardrail_violations=[screen["refusal_reason"]],
            guardrail_checks=[{"id": "input", "label": "Prompt-injection screen", "status": "blocked",
                               "detail": screen["refusal_reason"]}],
            final_response=screen["safe_response"], action="BLOCKED", step="GUARDRAIL_INTERCEPTED",
            razorpay_payload=None, reply_source={"by": "guardrail", "reason": "prompt injection blocked"},
        )  # fmt: skip
    input_check = {"id": "input", "label": "Prompt-injection screen", "status": "passed",
                   "detail": "No injection patterns in the customer's messages."}  # fmt: skip

    original_amount = float(state["original_amount"])
    merchant_id = state["merchant_id"]
    with SessionLocal() as db:
        rules = get_merchant_rules(db, merchant_id) or MerchantRules(
            merchant_id, state.get("merchant_name") or merchant_id
        )

    # 2. Ask the LLM; fall back to the policy heuristic when it is unavailable or unusable
    session_id = state.get("session_id") or f"sess_{uuid.uuid4().hex}"
    llm = gateway.completion(
        messages=messages,
        system_prompt=build_settlement_prompt(
            rules=rules,
            original_amount=original_amount,
            intent=state.get("customer_intent", ""),
            policy_context="\n\n".join(state.get("retrieved_policy_chunks", [])),
        ),
        session_id=session_id,
        patient=state.get("benchmark", False),
    )
    state["tokens_used"] = llm.get("tokens_used", 0)
    if llm.get("error") == "TOKEN_BUDGET_EXCEEDED":
        return _finish(state, start, final_response=BUDGET_MESSAGE, action="NONE", step="BUDGET_EXHAUSTED",
                       guardrail_checks=[input_check], razorpay_payload=None,
                       reply_source={"by": "guardrail", "reason": "conversation length limit"})  # fmt: skip

    content = llm.get("content", "")
    parsed = parse_llm_json(content)
    source: dict[str, Any] = {"by": "ai", "model": llm.get("model_used")}
    if parsed is None:
        reason = RULEBOOK_REASONS.get(llm.get("error", ""), "LLM reply not in the required format")
        source = {"by": "rulebook", "reason": reason}
        if content:
            logger.warning(
                "LLM reply was not usable JSON; using the policy heuristic. Reply began: %r", content[:300]
            )
        parsed = heuristic_offer(last_user_msg, rules, original_amount)

    # 3. Deterministic offer guardrail
    guard = run_post_llm_guardrail(
        parsed.get("offer"), rules, original_amount, str(parsed.get("action") or "PROPOSE_SETTLEMENT").upper()
    )
    action, offer = guard["action"], guard["corrected_offer"]
    violations, checks = list(guard["violations"]), [input_check, *guard["checks"]]

    # 4. Customer message must agree with the approved offer
    raw_message = parsed.get("message")
    message = raw_message if isinstance(raw_message, str) else ""
    message = strip_urls(strip_markdown(message))
    if not message:
        message = approved_offer_message(action, offer, rules)
        source = {"by": "guardrail", "reason": "reply had no message; stated the approved offer"}
    if action not in NO_PAYMENT_ACTIONS:
        bad = unapproved_amounts(message, legitimate_amounts(rules, original_amount, offer))
        if bad:
            detail = f"Message stated INR {bad[0]:,.2f}, which is not an approved amount; replaced with the approved offer."
            violations.append(detail)
            checks.append(
                {
                    "id": "message",
                    "label": "Message matches approved offer",
                    "status": "corrected",
                    "detail": detail,
                }
            )
            message = approved_offer_message(action, offer, rules)
            source = {
                "by": "guardrail",
                "reason": "reply named an unapproved amount; stated the approved offer",
            }
        else:
            checks.append({"id": "message", "label": "Message matches approved offer", "status": "passed",
                           "detail": "Every amount in the reply is an approved figure."})  # fmt: skip
    if action == "HUMAN_ESCALATION":
        ticket = f"#ESC-{uuid.uuid4().hex[:6].upper()}"
        message = message.replace(TICKET_PLACEHOLDER, ticket)
        if ticket not in message:
            message += f" Your ticket number is {ticket}."
    message = message.replace(TICKET_PLACEHOLDER, "").strip()

    state["proposed_offer"] = offer
    state["reply_source"] = source
    state["guardrail_violations"] = violations
    state["guardrail_status"] = "POLICY_BREACH_CORRECTED" if violations else "PASSED"

    # 5. Payment link: approved amount only, explicit customer consent only
    issue_link = (
        action not in NO_PAYMENT_ACTIONS
        and bool(parsed.get("should_generate_link"))
        and user_gave_consent(last_user_msg)
        and not is_asking_for_confirmation(message)
    )
    if not issue_link:
        return _finish(state, start, final_response=message, action=action, guardrail_checks=checks,
                       step=STEP_FOR_ACTION.get(action, "OFFER_PROPOSED"), razorpay_payload=None)  # fmt: skip

    with SessionLocal() as db:
        customer = db.get(Customer, state["customer_id"])
        contact = (customer.name, customer.email, customer.phone) if customer else (None, None, None)
    result = mcp_client.create_payment_link(
        amount_in_inr=offer["proposed_amount"],
        description=f"Settlement for invoice {state['invoice_id']}",
        reference_id=f"{state['invoice_id']}-{uuid.uuid4().hex[:8]}",
        customer_name=contact[0],
        customer_email=contact[1],
        customer_phone=contact[2],
    )
    if result["success"]:
        record_issued_link(result, state["invoice_id"], session_id)
        message += f"\n\n[ Pay INR {offer['proposed_amount']:.2f} via Razorpay ]({result['short_url']})"
        step = "LINK_ISSUED"
    else:
        # The LLM may have promised the link; restate the offer instead of contradicting it.
        message = f"{approved_offer_message(action, offer, rules)}\n\n{LINK_FAILED_MESSAGE}"
        step = "LINK_FAILED"
        state["reply_source"] = {
            "by": "guardrail",
            "reason": "payment link failed; restated the approved offer",
        }
    return _finish(state, start, final_response=message, action=action, guardrail_checks=checks, step=step,
                   razorpay_payload=result)  # fmt: skip
