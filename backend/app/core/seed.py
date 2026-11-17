"""Demo seed data, inserted only into empty tables."""

import logging

from sqlalchemy.orm import Session

from app.core.database import Customer, Invoice, Merchant

logger = logging.getLogger(__name__)


def _merchants():
    return [
        Merchant(
            merchant_id="hotstar",
            name="Disney+ Hotstar",
            category="OTT Entertainment",
            max_discount_inr=20.00,
            max_discount_pct=6.69,
            max_grace_days=3,
            auto_escalation_limit=5000,
            policy_doc_slug="01_hotstar_policy.md",
        ),
        Merchant(
            merchant_id="netflix_india",
            name="Netflix India",
            category="OTT Streaming",
            max_discount_inr=0.00,
            max_discount_pct=0.00,
            max_grace_days=2,
            auto_escalation_limit=10000,
            policy_doc_slug="02_netflix_india_policy.md",
        ),
        Merchant(
            merchant_id="amazon_prime",
            name="Amazon Prime India",
            category="E-Commerce & Video",
            max_discount_inr=75.00,
            max_discount_pct=5.00,
            max_grace_days=5,
            auto_escalation_limit=15000,
            policy_doc_slug="03_amazon_prime_policy.md",
        ),
        Merchant(
            merchant_id="spotify_india",
            name="Spotify India",
            category="Audio Streaming",
            max_discount_inr=15.00,
            max_discount_pct=0.00,
            max_grace_days=7,
            auto_escalation_limit=5000,
            policy_doc_slug="04_spotify_india_policy.md",
        ),
        Merchant(
            merchant_id="airtel_postpaid",
            name="Airtel Postpaid",
            category="Telecom",
            max_discount_inr=100.00,
            max_discount_pct=10.00,
            max_grace_days=3,
            auto_escalation_limit=20000,
            policy_doc_slug="05_airtel_postpaid_policy.md",
        ),
        Merchant(
            merchant_id="jio_fiber",
            name="JioFiber",
            category="Broadband Internet",
            max_discount_inr=0.00,
            max_discount_pct=0.00,
            max_grace_days=3,
            auto_escalation_limit=15000,
            policy_doc_slug="06_jio_fiber_policy.md",
        ),
        Merchant(
            merchant_id="swiggy_one",
            name="Swiggy One",
            category="Food & Delivery",
            max_discount_inr=30.00,
            max_discount_pct=10.00,
            max_grace_days=2,
            auto_escalation_limit=5000,
            policy_doc_slug="07_swiggy_one_policy.md",
        ),
        Merchant(
            merchant_id="zomato_gold",
            name="Zomato Gold",
            category="Dining & Delivery",
            max_discount_inr=25.00,
            max_discount_pct=5.00,
            max_grace_days=1,
            auto_escalation_limit=5000,
            policy_doc_slug="08_zomato_gold_policy.md",
        ),
        Merchant(
            merchant_id="notion_saas",
            name="Notion SaaS",
            category="B2B Productivity",
            max_discount_inr=0.00,
            max_discount_pct=0.00,
            max_grace_days=7,
            auto_escalation_limit=100000,
            policy_doc_slug="09_notion_saas_policy.md",
        ),
        Merchant(
            merchant_id="slack_workspace",
            name="Slack Workspace",
            category="B2B Collaboration",
            max_discount_inr=255.00,
            max_discount_pct=3.00,
            max_grace_days=5,
            auto_escalation_limit=50000,
            policy_doc_slug="10_slack_workspace_policy.md",
        ),
        Merchant(
            merchant_id="zoho_one",
            name="Zoho One",
            category="B2B SaaS Suite",
            max_discount_inr=500.00,
            max_discount_pct=3.00,
            max_grace_days=10,
            auto_escalation_limit=150000,
            policy_doc_slug="11_zoho_one_policy.md",
        ),
        Merchant(
            merchant_id="jira_atlassian",
            name="Jira Atlassian",
            category="Developer Tools",
            max_discount_inr=0.00,
            max_discount_pct=0.00,
            max_grace_days=14,
            auto_escalation_limit=200000,
            policy_doc_slug="12_jira_atlassian_policy.md",
        ),
        Merchant(
            merchant_id="quickkart_b2b",
            name="QuickKart B2B",
            category="Wholesale Supply",
            max_discount_inr=2550.00,
            max_discount_pct=3.00,
            max_grace_days=7,
            auto_escalation_limit=500000,
            policy_doc_slug="13_quickkart_b2b_policy.md",
        ),
        Merchant(
            merchant_id="udaan_wholesale",
            name="Udaan Wholesale",
            category="B2B Logistics",
            max_discount_inr=2000.00,
            max_discount_pct=2.00,
            max_grace_days=5,
            auto_escalation_limit=1000000,
            policy_doc_slug="14_udaan_wholesale_policy.md",
        ),
        Merchant(
            merchant_id="razorpayx_payroll",
            name="RazorpayX Payroll",
            category="Fintech & Payroll",
            max_discount_inr=0.00,
            max_discount_pct=0.00,
            max_grace_days=5,
            auto_escalation_limit=2000000,
            policy_doc_slug="15_razorpayx_payroll_policy.md",
        ),
    ]


def _customers():
    return [
        Customer(
            customer_id="cust_hotstar_01",
            merchant_id="hotstar",
            name="Aarav Sharma",
            email="aarav.sharma@example.com",
            phone="+919876543210",
            lifetime_value=3500.00,
            risk_tier="Low",
            tenure_months=18,
            failed_payment_history_count=0,
        ),
        Customer(
            customer_id="cust_notion_01",
            merchant_id="notion_saas",
            name="Rohan Mehta (TechNova Corp)",
            email="rohan@technova.io",
            phone="+919811223344",
            lifetime_value=45000.00,
            risk_tier="Medium",
            tenure_months=24,
            failed_payment_history_count=1,
        ),
        Customer(
            customer_id="cust_quickkart_01",
            merchant_id="quickkart_b2b",
            name="Vikram Enterprises",
            email="accounts@vikraments.com",
            phone="+919988776655",
            lifetime_value=280000.00,
            risk_tier="Low",
            tenure_months=36,
            failed_payment_history_count=0,
        ),
    ]


def _invoices():
    return [
        Invoice(
            invoice_id="inv_hotstar_101",
            customer_id="cust_hotstar_01",
            merchant_id="hotstar",
            plan_name="Super Plan",
            original_amount=299.00,
            current_status="FAILED",
            failure_code="INSUFFICIENT_FUNDS",
        ),
        Invoice(
            invoice_id="inv_notion_202",
            customer_id="cust_notion_01",
            merchant_id="notion_saas",
            plan_name="Business Plan (10 seats)",
            original_amount=15000.00,
            current_status="FAILED",
            failure_code="ISSUER_DOWN",
        ),
        Invoice(
            invoice_id="inv_quickkart_303",
            customer_id="cust_quickkart_01",
            merchant_id="quickkart_b2b",
            plan_name="Inventory Supply Batch #44",
            original_amount=85000.00,
            current_status="DISPUTED",
            failure_code="PARTIAL_GOODS_DISPUTE",
        ),
    ]


def seed_demo_data(db: Session) -> None:
    for model, rows in ((Merchant, _merchants), (Customer, _customers), (Invoice, _invoices)):
        if db.query(model).count() == 0:
            db.add_all(rows())
            db.commit()
            logger.info("Seeded %s", model.__tablename__)
