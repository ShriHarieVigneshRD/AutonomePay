from typing import List, Dict, Any
from fastapi import APIRouter
from app.evals.dataset_generator import generate_50_synthetic_cases

router = APIRouter()

MERCHANT_METADATA = {
    "hotstar": {"name": "Disney+ Hotstar", "category": "OTT Entertainment", "plan": "Super Plan", "discount": 6.69, "grace": 3, "cust": "Aarav Sharma"},
    "netflix_india": {"name": "Netflix India", "category": "OTT Entertainment", "plan": "Premium 4K", "discount": 0.00, "grace": 2, "cust": "Neha Kapoor"},
    "amazon_prime": {"name": "Amazon Prime", "category": "E-Commerce & OTT", "plan": "Annual Prime", "discount": 5.00, "grace": 5, "cust": "Rahul Verma"},
    "spotify_india": {"name": "Spotify India", "category": "Music Streaming", "plan": "Duo Plan", "discount": 10.00, "grace": 3, "cust": "Ananya Roy"},
    "airtel_postpaid": {"name": "Airtel Postpaid", "category": "Telecom", "plan": "Family Plan 999", "discount": 5.00, "grace": 7, "cust": "Rajesh Kumar"},
    "jio_fiber": {"name": "JioFiber Broadband", "category": "Telecom & Broadband", "plan": "Fiber 100Mbps", "discount": 0.00, "grace": 5, "cust": "Siddharth Malhotra"},
    "swiggy_one": {"name": "Swiggy One", "category": "Food & Grocery", "plan": "Annual Membership", "discount": 5.00, "grace": 3, "cust": "Kavya Iyer"},
    "zomato_gold": {"name": "Zomato Gold", "category": "Food & Dining", "plan": "3-Month Edition", "discount": 8.00, "grace": 3, "cust": "Rohan Gupta"},
    "notion_saas": {"name": "Notion SaaS", "category": "B2B Productivity", "plan": "Business Plan (10 seats)", "discount": 0.00, "grace": 7, "cust": "Rohan Mehta (TechNova)"},
    "slack_workspace": {"name": "Slack Workspace", "category": "B2B Communication", "plan": "Pro Tier (25 users)", "discount": 10.00, "grace": 7, "cust": "Devendra Shah"},
    "zoho_one": {"name": "Zoho One", "category": "B2B Business Suite", "plan": "All-in-One Enterprise", "discount": 5.00, "grace": 10, "cust": "Sunil Bansal"},
    "jira_atlassian": {"name": "Jira Atlassian", "category": "B2B Software Dev", "plan": "Cloud Premium", "discount": 0.00, "grace": 7, "cust": "Tanya Saxena"},
    "quickkart_b2b": {"name": "QuickKart B2B", "category": "Wholesale Supply", "plan": "Inventory Batch #44", "discount": 3.00, "grace": 7, "cust": "Vikram Enterprises"},
    "udaan_wholesale": {"name": "Udaan Wholesale", "category": "B2B E-Commerce", "plan": "Bulk Traders License", "discount": 2.00, "grace": 14, "cust": "Mahavir Stores"},
    "razorpayx_payroll": {"name": "RazorpayX Payroll", "category": "Fintech & Payroll", "plan": "Automated Payroll Pro", "discount": 0.00, "grace": 5, "cust": "Apex Global Solutions"}
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

def get_all_50_formatted_scenarios() -> List[Dict[str, Any]]:
    raw_cases = generate_50_synthetic_cases()
    formatted = []

    for case in raw_cases:
        m_id = case["merchant_id"]
        meta = MERCHANT_METADATA.get(m_id, {
            "name": m_id.replace("_", " ").title(),
            "category": "Enterprise Subscription",
            "plan": "Standard Plan",
            "discount": 5.0,
            "grace": 7,
            "cust": f"Customer #{case['customer_id']}"
        })
        s_type_title = SCENARIO_TYPE_TITLES.get(case["scenario_type"], case["scenario_type"].replace("_", " ").title())
        case_num = case["scenario_id"].replace("eval_case_", "Case #")
        title = f"{case_num}: {meta['name']} — {s_type_title}"

        # Construct initial message greeting
        if case["scenario_id"] == "eval_case_01":
            init_msg = "Hi Aarav, your auto-renewal of INR 299 for Disney+ Hotstar Super Plan failed due to insufficient funds."
        elif case["scenario_id"] == "eval_case_02":
            init_msg = "Hi Rohan, invoice #202 for Notion Business (INR 15,000) failed due to bank issuer downtime."
        elif case["scenario_id"] == "eval_case_03":
            init_msg = "Hello Vikram, invoice #303 of INR 85,000 is marked overdue for Batch #44 inventory supply."
        elif case["scenario_id"] == "eval_case_04":
            init_msg = "Your Disney+ Hotstar Premium Plan payment of INR 499 is pending retry."
        else:
            init_msg = f"Hello {meta['cust']}, your subscription payment of INR {case['original_amount']:.2f} for {meta['name']} ({meta['plan']}) encountered a payment issue ({case['failure_code']})."

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
            "max_discount_pct": meta["discount"],
            "max_grace_days": meta["grace"],
            "is_multi_turn": case["is_multi_turn"],
            "initial_message": init_msg
        })

    return formatted

@router.get("/scenarios")
def get_scenarios():
    return get_all_50_formatted_scenarios()
