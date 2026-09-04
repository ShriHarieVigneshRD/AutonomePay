import os
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Numeric, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

from app.core.config import settings

# SQLite or PostgreSQL configuration
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite"):
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
else:
    engine = create_engine(db_url, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# DDL Models matching specification
class Merchant(Base):
    __tablename__ = "merchants"

    merchant_id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    max_discount_pct = Column(Numeric(5, 2), default=5.00)
    max_grace_days = Column(Integer, default=7)
    auto_escalation_limit = Column(Numeric(12, 2), default=50000.00)
    policy_doc_slug = Column(String(100), nullable=False)

    customers = relationship("Customer", back_populates="merchant")
    invoices = relationship("Invoice", back_populates="merchant")


class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(String(64), primary_key=True)
    merchant_id = Column(String(64), ForeignKey("merchants.merchant_id"))
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    lifetime_value = Column(Numeric(12, 2), default=0.00)
    risk_tier = Column(String(20), default="Low")
    tenure_months = Column(Integer, default=1)
    failed_payment_history_count = Column(Integer, default=0)

    merchant = relationship("Merchant", back_populates="customers")
    invoices = relationship("Invoice", back_populates="customer")


class Invoice(Base):
    __tablename__ = "invoices"

    invoice_id = Column(String(64), primary_key=True)
    customer_id = Column(String(64), ForeignKey("customers.customer_id"))
    merchant_id = Column(String(64), ForeignKey("merchants.merchant_id"))
    plan_name = Column(String(100), nullable=False)
    original_amount = Column(Numeric(12, 2), nullable=False)
    current_status = Column(String(50), nullable=False)
    failure_code = Column(String(100), nullable=False)
    due_date = Column(DateTime, default=datetime.utcnow)
    recovered_amount = Column(Numeric(12, 2), default=0.00)
    razorpay_payment_link = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="invoices")
    merchant = relationship("Merchant", back_populates="invoices")


class EvaluationBatch(Base):
    __tablename__ = "evaluation_batches"

    batch_id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    status = Column(String(50), default="RUNNING")
    total_cases = Column(Integer, default=50)
    completed_cases = Column(Integer, default=0)
    kpis = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    runs = relationship("EvaluationRun", back_populates="batch", cascade="all, delete-orphan")


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    run_id = Column(String(64), primary_key=True)
    batch_id = Column(String(64), ForeignKey("evaluation_batches.batch_id"), nullable=True)
    test_id = Column(String(64), nullable=False)
    scenario_type = Column(String(100), nullable=False)
    total_turns = Column(Integer, default=1)
    rag_context_relevance = Column(Numeric(4, 3), default=1.00)
    rag_faithfulness = Column(Numeric(4, 3), default=1.00)
    rag_answer_relevance = Column(Numeric(4, 3), default=1.00)
    policy_breach = Column(Boolean, default=False)
    adversarial_intercepted = Column(Boolean, default=False)
    final_agent_outcome = Column(String(100), nullable=True)
    amount_recovered = Column(Numeric(12, 2), default=0.00)
    langsmith_trace_url = Column(String(500), nullable=True)
    execution_trace = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    batch = relationship("EvaluationBatch", back_populates="runs")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Check if seed merchants exist
    if db.query(Merchant).count() == 0:
        seed_merchants = [
            Merchant(merchant_id="hotstar", name="Disney+ Hotstar", category="OTT Entertainment", max_discount_pct=6.69, max_grace_days=3, auto_escalation_limit=5000, policy_doc_slug="01_hotstar_policy.md"),
            Merchant(merchant_id="netflix_india", name="Netflix India", category="OTT Streaming", max_discount_pct=0.00, max_grace_days=2, auto_escalation_limit=10000, policy_doc_slug="02_netflix_india_policy.md"),
            Merchant(merchant_id="amazon_prime", name="Amazon Prime India", category="E-Commerce & Video", max_discount_pct=5.00, max_grace_days=5, auto_escalation_limit=15000, policy_doc_slug="03_amazon_prime_policy.md"),
            Merchant(merchant_id="spotify_india", name="Spotify India", category="Audio Streaming", max_discount_pct=0.00, max_grace_days=7, auto_escalation_limit=5000, policy_doc_slug="04_spotify_india_policy.md"),
            Merchant(merchant_id="airtel_postpaid", name="Airtel Postpaid", category="Telecom", max_discount_pct=10.00, max_grace_days=3, auto_escalation_limit=20000, policy_doc_slug="05_airtel_postpaid_policy.md"),
            Merchant(merchant_id="jio_fiber", name="JioFiber", category="Broadband Internet", max_discount_pct=0.00, max_grace_days=3, auto_escalation_limit=15000, policy_doc_slug="06_jio_fiber_policy.md"),
            Merchant(merchant_id="swiggy_one", name="Swiggy One", category="Food & Delivery", max_discount_pct=10.00, max_grace_days=2, auto_escalation_limit=5000, policy_doc_slug="07_swiggy_one_policy.md"),
            Merchant(merchant_id="zomato_gold", name="Zomato Gold", category="Dining & Delivery", max_discount_pct=5.00, max_grace_days=1, auto_escalation_limit=5000, policy_doc_slug="08_zomato_gold_policy.md"),
            Merchant(merchant_id="notion_saas", name="Notion SaaS", category="B2B Productivity", max_discount_pct=0.00, max_grace_days=7, auto_escalation_limit=100000, policy_doc_slug="09_notion_saas_policy.md"),
            Merchant(merchant_id="slack_workspace", name="Slack Workspace", category="B2B Collaboration", max_discount_pct=3.00, max_grace_days=5, auto_escalation_limit=50000, policy_doc_slug="10_slack_workspace_policy.md"),
            Merchant(merchant_id="zoho_one", name="Zoho One", category="B2B SaaS Suite", max_discount_pct=3.00, max_grace_days=10, auto_escalation_limit=150000, policy_doc_slug="11_zoho_one_policy.md"),
            Merchant(merchant_id="jira_atlassian", name="Jira Atlassian", category="Developer Tools", max_discount_pct=0.00, max_grace_days=14, auto_escalation_limit=200000, policy_doc_slug="12_jira_atlassian_policy.md"),
            Merchant(merchant_id="quickkart_b2b", name="QuickKart B2B", category="Wholesale Supply", max_discount_pct=3.00, max_grace_days=7, auto_escalation_limit=500000, policy_doc_slug="13_quickkart_b2b_policy.md"),
            Merchant(merchant_id="udaan_wholesale", name="Udaan Wholesale", category="B2B Logistics", max_discount_pct=2.00, max_grace_days=5, auto_escalation_limit=1000000, policy_doc_slug="14_udaan_wholesale_policy.md"),
            Merchant(merchant_id="razorpayx_payroll", name="RazorpayX Payroll", category="Fintech & Payroll", max_discount_pct=0.00, max_grace_days=5, auto_escalation_limit=2000000, policy_doc_slug="15_razorpayx_payroll_policy.md"),
        ]
        db.add_all(seed_merchants)
        db.commit()

    if db.query(Customer).count() == 0:
        seed_customers = [
            Customer(customer_id="cust_hotstar_01", merchant_id="hotstar", name="Aarav Sharma", email="aarav.sharma@example.com", phone="+919876543210", lifetime_value=3500.00, risk_tier="Low", tenure_months=18, failed_payment_history_count=0),
            Customer(customer_id="cust_notion_01", merchant_id="notion_saas", name="Rohan Mehta (TechNova Corp)", email="rohan@technova.io", phone="+919811223344", lifetime_value=45000.00, risk_tier="Medium", tenure_months=24, failed_payment_history_count=1),
            Customer(customer_id="cust_quickkart_01", merchant_id="quickkart_b2b", name="Vikram Enterprises", email="accounts@vikraments.com", phone="+919988776655", lifetime_value=280000.00, risk_tier="Low", tenure_months=36, failed_payment_history_count=0),
        ]
        db.add_all(seed_customers)
        db.commit()

    if db.query(Invoice).count() == 0:
        seed_invoices = [
            Invoice(invoice_id="inv_hotstar_101", customer_id="cust_hotstar_01", merchant_id="hotstar", plan_name="Super Plan", original_amount=299.00, current_status="FAILED", failure_code="INSUFFICIENT_FUNDS"),
            Invoice(invoice_id="inv_notion_202", customer_id="cust_notion_01", merchant_id="notion_saas", plan_name="Business Plan (10 seats)", original_amount=15000.00, current_status="FAILED", failure_code="ISSUER_DOWN"),
            Invoice(invoice_id="inv_quickkart_303", customer_id="cust_quickkart_01", merchant_id="quickkart_b2b", plan_name="Inventory Supply Batch #44", original_amount=85000.00, current_status="DISPUTED", failure_code="PARTIAL_GOODS_DISPUTE"),
        ]
        db.add_all(seed_invoices)
        db.commit()

    db.close()
