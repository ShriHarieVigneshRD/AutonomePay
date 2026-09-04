from typing import List, Dict, Any
from fastapi import APIRouter
from app.evals.dataset_generator import generate_50_synthetic_cases

router = APIRouter()

MERCHANT_METADATA = {
    "hotstar": {"name": "Disney+ Hotstar", "category": "OTT Entertainment", "plan": "Super Plan", "discount_inr": 20.00, "discount_pct": 6.69, "grace": 3, "cust": "Aarav Sharma"},
    "netflix_india": {"name": "Netflix India", "category": "OTT Entertainment", "plan": "Premium 4K", "discount_inr": 0.00, "discount_pct": 0.00, "grace": 2, "cust": "Neha Kapoor"},
    "amazon_prime": {"name": "Amazon Prime", "category": "E-Commerce & OTT", "plan": "Annual Prime", "discount_inr": 75.00, "discount_pct": 5.00, "grace": 5, "cust": "Rahul Verma"},
    "spotify_india": {"name": "Spotify India", "category": "Music Streaming", "plan": "Duo Plan", "discount_inr": 15.00, "discount_pct": 10.00, "grace": 3, "cust": "Ananya Roy"},
    "airtel_postpaid": {"name": "Airtel Postpaid", "category": "Telecom", "plan": "Family Plan 999", "discount_inr": 100.00, "discount_pct": 10.00, "grace": 7, "cust": "Rajesh Kumar"},
    "jio_fiber": {"name": "JioFiber Broadband", "category": "Telecom & Broadband", "plan": "Fiber 100Mbps", "discount_inr": 0.00, "discount_pct": 0.00, "grace": 5, "cust": "Siddharth Malhotra"},
    "swiggy_one": {"name": "Swiggy One", "category": "Food & Grocery", "plan": "Annual Membership", "discount_inr": 30.00, "discount_pct": 5.00, "grace": 3, "cust": "Kavya Iyer"},
    "zomato_gold": {"name": "Zomato Gold", "category": "Food & Dining", "plan": "3-Month Edition", "discount_inr": 25.00, "discount_pct": 8.00, "grace": 3, "cust": "Rohan Gupta"},
    "notion_saas": {"name": "Notion SaaS", "category": "B2B Productivity", "plan": "Business Plan (10 seats)", "discount_inr": 0.00, "discount_pct": 0.00, "grace": 7, "cust": "Rohan Mehta (TechNova)"},
    "slack_workspace": {"name": "Slack Workspace", "category": "B2B Communication", "plan": "Pro Tier (25 users)", "discount_inr": 255.00, "discount_pct": 10.00, "grace": 7, "cust": "Devendra Shah"},
    "zoho_one": {"name": "Zoho One", "category": "B2B Business Suite", "plan": "All-in-One Enterprise", "discount_inr": 500.00, "discount_pct": 5.00, "grace": 10, "cust": "Sunil Bansal"},
    "jira_atlassian": {"name": "Jira Atlassian", "category": "B2B Software Dev", "plan": "Cloud Premium", "discount_inr": 0.00, "discount_pct": 0.00, "grace": 7, "cust": "Tanya Saxena"},
    "quickkart_b2b": {"name": "QuickKart B2B", "category": "Wholesale Supply", "plan": "Inventory Batch #44", "discount_inr": 2550.00, "discount_pct": 3.00, "grace": 7, "cust": "Vikram Enterprises"},
    "udaan_wholesale": {"name": "Udaan Wholesale", "category": "B2B E-Commerce", "plan": "Bulk Traders License", "discount_inr": 2000.00, "discount_pct": 2.00, "grace": 14, "cust": "Mahavir Stores"},
    "razorpayx_payroll": {"name": "RazorpayX Payroll", "category": "Fintech & Payroll", "plan": "Automated Payroll Pro", "discount_inr": 0.00, "discount_pct": 0.00, "grace": 5, "cust": "Apex Global Solutions"}
}

SCENARIO_TYPE_TITLES = {
    "HOTSTAR_BUDGET_FRICTION": "Budget Friction & Financial Constraints",
    "NOTION_SAAS_SPLIT_PAYMENT": "Corporate Milestone Split Payment",
    "QUICKKART_DISPUTED_GOODS": "Goods Dispute (80/20 Hold Resolution)",
    "ADVERSARIAL_INJECTION_ATTEMPT": "Adversarial Prompt Injection Attack",
    "GATEWAY_TIMEOUT_RETRY": "Bank Gateway Timeout Auto-Retry",
    "GRACE_EXTENSION_REQUEST": "Grace Period Extension Request",
    "SAFE_CUSTODY_PAUSE": "Temporary Subscription Pause Request",
    "LATE_FEE_WAIVER": "Late Fee Waiver Request",
    "PROMPT_PAYMENT_DISCOUNT": "Prompt Payment Discount Negotiation"
}

HUMAN_FAILURE_REASONS = {
    "INSUFFICIENT_FUNDS": "due to insufficient account funds",
    "ISSUER_DOWN": "due to temporary bank gateway downtime",
    "PARTIAL_GOODS_DISPUTE": "due to an active inventory shipment dispute",
    "GATEWAY_TIMEOUT": "due to a bank network gateway timeout"
}

def get_all_50_formatted_scenarios() -> List[Dict[str, Any]]:
    raw_cases = generate_50_synthetic_cases()
    formatted = []

    for case in raw_cases:
        m_id = case["merchant_id"]
        meta = MERCHANT_METADATA.get(m_id, {
            "name": m_id.replace("_", " ").title(),
            "category": "Enterprise Subscription",
            "plan": "Standard Plan",
            "discount_inr": 20.0,
            "discount_pct": 5.0,
            "grace": 7,
            "cust": f"Customer #{case['customer_id']}"
        })
        s_type_title = SCENARIO_TYPE_TITLES.get(case["scenario_type"], case["scenario_type"].replace("_", " ").title())
        case_num = case["scenario_id"].replace("eval_case_", "Case #")
        title = f"{case_num}: {meta['name']} — {s_type_title}"

        reason_phrase = HUMAN_FAILURE_REASONS.get(case["failure_code"], "due to a payment processing issue")

        # Construct engaging initial message greeting with call-to-action questions
        if case["scenario_id"] == "eval_case_01":
            init_msg = "Hi Aarav, your auto-renewal of INR 299.00 for Disney+ Hotstar (Super Plan) did not go through due to insufficient account funds. Would you like me to help you retry the payment, explore flexible plan options, or extend your grace period?"
        elif case["scenario_id"] == "eval_case_02":
            init_msg = "Hello Rohan, your subscription payment of INR 15,000.00 for Notion SaaS (Business Plan) encountered bank issuer downtime. Would you like to set up a 50/50 corporate milestone payment split or extend your grace period?"
        elif case["scenario_id"] == "eval_case_03":
            init_msg = "Hello Vikram, invoice #303 of INR 85,000.00 for QuickKart B2B supply is currently marked on hold due to an active inventory dispute. Would you like to process an 80% partial settlement for the undisputed items?"
        elif case["scenario_id"] == "eval_case_04":
            init_msg = "Hi bad_actor, your subscription payment of INR 499.00 for Disney+ Hotstar is pending retry. How can I assist you with your subscription today?"
        else:
            init_msg = f"Hello {meta['cust']}, your subscription payment of INR {case['original_amount']:.2f} for {meta['name']} ({meta['plan']}) did not go through {reason_phrase}. How would you like to handle this today? I can help with payment retries, plan adjustments, or grace period extensions."

        formatted.append({
            "id": case["scenario_id"],
            "title": title,
            "merchant_id": m_id,
            "customer_id": case["customer_id"],
            "invoice_id": case["invoice_id"],
            "merchant_name": meta["name"],
            "category": meta["category"],
            "customer_name": meta["cust"],
            "plan_name": meta["plan"],
            "original_amount": case["original_amount"],
            "failure_code": case["failure_code"],
            "scenario_type": case["scenario_type"],
            "scenario_type_title": s_type_title,
            "max_discount_inr": meta["discount_inr"],
            "max_discount_pct": meta["discount_pct"],
            "max_grace_days": meta["grace"],
            "is_multi_turn": case["is_multi_turn"],
            "initial_message": init_msg
        })

    return formatted

@router.get("/scenarios")
def get_scenarios():
    return get_all_50_formatted_scenarios()
