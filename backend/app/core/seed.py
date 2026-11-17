"""Startup data sync.

Merchant configuration (limits, plans, split/partial rules) is synced from
data/merchants.json on every boot, so the guardrails, the scenarios API and the
UI all read the same numbers. Demo customers and invoices are only inserted when
missing; existing rows are never modified or deleted.
"""

import logging
import re

from sqlalchemy.orm import Session

from app.core.catalog import load_catalog
from app.core.database import Customer, Invoice, Merchant, MerchantPlan

logger = logging.getLogger(__name__)

# The three hand-written demo accounts from the original release.
PRIMARY_CUSTOMERS = [
    dict(customer_id="cust_hotstar_01", merchant_id="hotstar", name="Aarav Sharma", email="aarav.sharma@example.com",
         phone="+919876543210", lifetime_value=3500.00, risk_tier="Low", tenure_months=18, failed_payment_history_count=0),
    dict(customer_id="cust_notion_01", merchant_id="notion_saas", name="Rohan Mehta (TechNova Corp)", email="rohan@technova.io",
         phone="+919811223344", lifetime_value=45000.00, risk_tier="Medium", tenure_months=24, failed_payment_history_count=1),
    dict(customer_id="cust_quickkart_01", merchant_id="quickkart_b2b", name="Vikram Enterprises", email="accounts@vikraments.com",
         phone="+919988776655", lifetime_value=280000.00, risk_tier="Low", tenure_months=36, failed_payment_history_count=0),
]  # fmt: skip


def sync_merchants(db: Session) -> None:
    for cfg in load_catalog().values():
        merchant = db.get(Merchant, cfg["merchant_id"]) or Merchant(merchant_id=cfg["merchant_id"])
        merchant.name = cfg["name"]
        merchant.category = cfg["category"]
        merchant.policy_doc_slug = cfg["policy_doc"]
        merchant.max_discount_inr = cfg["max_discount_inr"]
        merchant.max_discount_pct = cfg["max_discount_pct"]
        merchant.max_grace_days = cfg["max_grace_days"]
        merchant.auto_escalation_limit = cfg["auto_escalation_limit"]
        merchant.split_schedule_pct = cfg.get("split_schedule_pct")
        merchant.split_min_invoice_inr = cfg.get("split_min_invoice_inr")
        merchant.partial_settlement_pct = cfg.get("partial_settlement_pct")
        merchant.plans = [
            MerchantPlan(name=p["name"], price_inr=p["price_inr"], period=p.get("period"))
            for p in cfg["plans"]
        ]
        db.add(merchant)
    db.commit()


def _demo_email(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", ".", name.lower()).strip(".") + "@example.com"


def seed_demo_accounts(db: Session) -> None:
    from app.evals.dataset import generate_50_synthetic_cases

    catalog = load_catalog()
    added = 0
    for row in PRIMARY_CUSTOMERS:
        if not db.get(Customer, row["customer_id"]):
            db.add(Customer(**row))
            added += 1
    db.flush()  # autoflush is off: make pending rows visible to db.get() below

    for case in generate_50_synthetic_cases():
        cfg = catalog[case["merchant_id"]]
        if not db.get(Customer, case["customer_id"]):
            name = "Unverified User" if case["customer_id"] == "cust_bad_actor" else cfg["demo_customer"]
            db.add(Customer(customer_id=case["customer_id"], merchant_id=case["merchant_id"], name=name,
                            email=_demo_email(name)))  # fmt: skip
            added += 1
        if not db.get(Invoice, case["invoice_id"]):
            db.add(
                Invoice(
                    invoice_id=case["invoice_id"],
                    customer_id=case["customer_id"],
                    merchant_id=case["merchant_id"],
                    plan_name=case["plan_name"],
                    original_amount=case["original_amount"],
                    current_status="DISPUTED"
                    if case["failure_code"] == "PARTIAL_GOODS_DISPUTE"
                    else "FAILED",
                    failure_code=case["failure_code"],
                )
            )
            added += 1
        db.flush()
    db.commit()
    if added:
        logger.info("Seeded %d demo customers/invoices", added)


def seed_demo_data(db: Session) -> None:
    sync_merchants(db)
    seed_demo_accounts(db)
