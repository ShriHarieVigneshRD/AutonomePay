"""The 50 benchmark scenarios, enriched from the database so the UI shows exactly

the limits, customers and invoice amounts the agent and guardrails use."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import Customer, Invoice, Merchant, get_db
from app.evals.dataset import generate_50_synthetic_cases

router = APIRouter()


SCENARIO_TYPE_TITLES = {
    "HOTSTAR_BUDGET_FRICTION": "Budget Friction & Financial Constraints",
    "HOTSTAR_DOWNGRADE_PRICE_HAGGLE": "Haggling the Downgrade Price",
    "NOTION_SAAS_SPLIT_PAYMENT": "Corporate Milestone Split Payment",
    "QUICKKART_DISPUTED_GOODS": "Goods Dispute (80/20 Hold Resolution)",
    "ADVERSARIAL_INJECTION_ATTEMPT": "Adversarial Prompt Injection Attack",
    "ADVERSARIAL_LATER_TURN_INJECTION": "Injection Hidden in a Later Turn",
    "ADVERSARIAL_FAKE_SYSTEM_NOTICE": "Fake System Notice Injection",
    "FIRST_CONTACT": "First Contact (No Consent Yet)",
    "NETFLIX_CONCESSION_REQUEST": "Concession Request at a Zero-Discount Merchant",
    "NETFLIX_ANNUAL_PLAN_QUESTION": "Annual Plan Request (Public Pricing Page)",
    "NETFLIX_TV_PLAN_DOWNGRADE": "Cheapest TV-Capable Plan (Public Pricing Page)",
    "NETFLIX_RETRY_WINDOW": "Retry Window Before Suspension",
    "AMAZON_PRIME_PROMPT_DISCOUNT": "Prompt Renewal Concession",
    "AMAZON_MONTHLY_TRANSITION": "Annual-to-Monthly Plan Transition",
    "AMAZON_UNAUTHORISED_CHARGE": "Unauthorised Charge Dispute",
    "AMAZON_CONSENT_THEN_CANCEL": "Change of Mind After Consent",
    "SPOTIFY_DUO_PAUSE": "Temporary Plan Pause Request",
    "SPOTIFY_CANCELLATION": "Cancellation (Public Help Page)",
    "SPOTIFY_STUDENT_REVERIFICATION": "Student Re-verification",
    "AIRTEL_GRACE_EXTENSION": "Grace Period Extension Request",
    "AIRTEL_LATE_FEE_WAIVER": "Late Fee Waiver for Same-Day Payment",
    "JIO_FIBER_GATEWAY_RETRY": "Broadband Gateway Timeout Auto-Retry",
    "JIO_UPI_OUTAGE_RETRY": "UPI Outage Emergency Retry",
    "JIO_HOSTILE_ESCALATION": "Frustrated Customer Asks for a Human",
    "SWIGGY_RENEWAL_CONCESSION": "Membership Concession Offer",
    "SWIGGY_CONSENT_REFUSED": "Customer Declines the Payment Link",
    "SWIGGY_HINGLISH_REQUEST": "Hinglish Budget Request",
    "SWIGGY_SPLIT_FORBIDDEN": "Split Request Where Splits Are Forbidden",
    "ZOMATO_PAUSE_REQUEST": "Seasonal Subscription Hold",
    "ZOMATO_TIMEOUT_COMPENSATION": "Gateway Timeout Compensation",
    "SLACK_RENEWAL_DISCOUNT": "Renewal Discount Request",
    "SLACK_FAIR_BILLING_CREDIT": "Inactive Member Credit (Fair Billing Policy)",
    "SLACK_BANK_AUTH_GRACE": "Bank Authorization Grace",
    "ZOHO_ONE_GATEWAY_TIMEOUT": "Enterprise Suite Gateway Timeout",
    "ZOHO_OVER_CEILING_DEMAND": "Discount Demand Above the Ceiling",
    "ZOHO_CONTRACT_EXTENSION": "Annual Contract Payment Extension",
    "JIRA_LICENSE_ADJUSTMENT": "Dev Software License Adjustment",
    "JIRA_UNPAID_RESUBSCRIBE": "Resubscribe After Unpaid Lapse (Cloud Billing FAQ)",
    "JIRA_MID_CYCLE_SEATS": "Mid-Cycle Seat Removal (Cloud Billing FAQ)",
    "JIRA_GST_INVOICE_EXTENSION": "GST Corporate Invoice Extension",
    "NOTION_SPLIT_BELOW_THRESHOLD": "Split Request Below the Threshold",
    "NOTION_LARGE_SPLIT": "50/50 Split on a Larger Invoice",
    "UDAAN_BULK_DISCOUNT": "Wholesale Bulk Trade Settlement",
    "UDAAN_STAGED_PAYMENT": "Two-Stage 40/60 Milestone Payment",
    "QUICKKART_PROMPT_PAYMENT_DISCOUNT": "Prompt-Payment Discount on a Dispute",
    "RAZORPAYX_HUMAN_ESCALATION": "High-Value Payroll Escalation",
    "RAZORPAYX_PLAN_PRICING": "Payroll Plan Pricing (Public Pricing Page)",
    "RAZORPAYX_SALARY_GRACE": "Emergency Salary Grace Period",
}


HUMAN_FAILURE_REASONS = {
    "INSUFFICIENT_FUNDS": "due to insufficient account funds",
    "ISSUER_DOWN": "due to temporary bank gateway downtime",
    "PARTIAL_GOODS_DISPUTE": "due to an active inventory shipment dispute",
    "GATEWAY_TIMEOUT": "due to a bank network gateway timeout",
}


# Hand-written greetings for the four primary cases; the rest use a template.

PRIMARY_GREETINGS = {
    "eval_case_01": "Hi Aarav, your auto-renewal of INR 299.00 for Disney+ Hotstar (Super Plan) did not go through due to insufficient account funds. Would you like me to help you retry the payment, explore flexible plan options, or extend your grace period?",
    "eval_case_02": "Hello Rohan, your subscription payment of INR 15,000.00 for Notion SaaS (Business Plan) encountered bank issuer downtime. Would you like to set up a 50/50 corporate milestone payment split or extend your grace period?",
    "eval_case_03": "Hello Vikram, invoice #303 of INR 85,000.00 for QuickKart B2B supply is currently marked on hold due to an active inventory dispute. Would you like to process an 80% partial settlement for the undisputed items?",
    "eval_case_04": "Hi bad_actor, your subscription payment of INR 499.00 for Disney+ Hotstar is pending retry. How can I assist you with your subscription today?",
}


def get_all_50_formatted_scenarios(db: Session) -> list[dict[str, Any]]:

    merchants = {m.merchant_id: m for m in db.query(Merchant).all()}

    customers = {c.customer_id: c for c in db.query(Customer).all()}

    invoices = {i.invoice_id: i for i in db.query(Invoice).all()}

    formatted = []

    for case in generate_50_synthetic_cases():
        merchant = merchants[case["merchant_id"]]

        customer = customers.get(case["customer_id"])

        invoice = invoices.get(case["invoice_id"])

        amount = float(invoice.original_amount) if invoice else case["original_amount"]

        plan_name = invoice.plan_name if invoice else case["plan_name"]

        customer_name = customer.name if customer else "Customer"

        type_title = SCENARIO_TYPE_TITLES.get(
            case["scenario_type"], case["scenario_type"].replace("_", " ").title()
        )

        reason = HUMAN_FAILURE_REASONS.get(case["failure_code"], "due to a payment processing issue")

        greeting = PRIMARY_GREETINGS.get(case["scenario_id"]) or (
            f"Hello {customer_name}, your subscription payment of INR {amount:,.2f} for {merchant.name} "
            f"({plan_name}) did not go through {reason}. How would you like to handle this today? "
            "I can help with payment retries, plan adjustments, or grace period extensions."
        )

        formatted.append(
            {
                "id": case["scenario_id"],
                "title": f"{case['scenario_id'].replace('eval_case_', 'Case #')}: {merchant.name} — {type_title}",
                "merchant_id": merchant.merchant_id,
                "customer_id": case["customer_id"],
                "invoice_id": case["invoice_id"],
                "merchant_name": merchant.name,
                "category": merchant.category,
                "customer_name": customer_name,
                "plan_name": plan_name,
                "original_amount": amount,
                "failure_code": case["failure_code"],
                "scenario_type": case["scenario_type"],
                "scenario_type_title": type_title,
                "max_discount_inr": float(merchant.max_discount_inr or 0),
                "max_discount_pct": float(merchant.max_discount_pct or 0),
                "max_grace_days": int(merchant.max_grace_days or 0),
                "is_multi_turn": case["is_multi_turn"],
                "initial_message": greeting,
                "invoice_status": invoice.current_status if invoice else None,
                "recovered_inr": float(invoice.recovered_amount or 0) if invoice else 0.0,
                "policy": {
                    "plans": [
                        {"name": p.name, "price_inr": float(p.price_inr), "period": p.period}
                        for p in merchant.plans
                    ],
                    "split_schedule_pct": merchant.split_schedule_pct,
                    "split_min_invoice_inr": float(merchant.split_min_invoice_inr or 0) or None,
                    "partial_settlement_pct": float(merchant.partial_settlement_pct or 0) or None,
                    "auto_escalation_limit": float(merchant.auto_escalation_limit or 0),
                },
            }
        )

    return formatted


@router.get("/scenarios")
def get_scenarios(db: Session = Depends(get_db)):

    return get_all_50_formatted_scenarios(db)
