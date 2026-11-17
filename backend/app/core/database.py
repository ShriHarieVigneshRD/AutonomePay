from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from app.core.config import settings

if settings.DATABASE_URL.startswith("sqlite"):
    engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    # Naive UTC, matching what existing databases already store.
    return datetime.now(UTC).replace(tzinfo=None)


class Merchant(Base):
    __tablename__ = "merchants"

    merchant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    max_discount_inr: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=20.00)
    max_discount_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), default=5.00)
    max_grace_days: Mapped[int | None] = mapped_column(Integer, default=7)
    auto_escalation_limit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=50000.00)
    policy_doc_slug: Mapped[str] = mapped_column(String(100), nullable=False)
    # Policy-approved alternatives to a discount (all optional; see data/merchants.json)
    split_schedule_pct: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    split_min_invoice_inr: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    partial_settlement_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    plans: Mapped[list["MerchantPlan"]] = relationship(
        back_populates="merchant", cascade="all, delete-orphan", order_by="MerchantPlan.price_inr"
    )
    customers: Mapped[list["Customer"]] = relationship(back_populates="merchant")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="merchant")


class MerchantPlan(Base):
    """A plan the merchant sells; a downgrade must land on one of these prices."""

    __tablename__ = "merchant_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    merchant_id: Mapped[str] = mapped_column(String(64), ForeignKey("merchants.merchant_id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    price_inr: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    period: Mapped[str | None] = mapped_column(String(40), nullable=True)

    merchant: Mapped["Merchant"] = relationship(back_populates="plans")


class Customer(Base):
    __tablename__ = "customers"

    customer_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    merchant_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("merchants.merchant_id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    lifetime_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=0.00)
    risk_tier: Mapped[str | None] = mapped_column(String(20), default="Low")
    tenure_months: Mapped[int | None] = mapped_column(Integer, default=1)
    failed_payment_history_count: Mapped[int | None] = mapped_column(Integer, default=0)

    merchant: Mapped["Merchant"] = relationship(back_populates="customers")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="customer")


class Invoice(Base):
    __tablename__ = "invoices"

    invoice_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    customer_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("customers.customer_id"))
    merchant_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("merchants.merchant_id"))
    plan_name: Mapped[str] = mapped_column(String(100), nullable=False)
    original_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    current_status: Mapped[str] = mapped_column(String(50), nullable=False)
    failure_code: Mapped[str] = mapped_column(String(100), nullable=False)
    due_date: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)
    recovered_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=0.00)
    razorpay_payment_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)

    customer: Mapped["Customer"] = relationship(back_populates="invoices")
    merchant: Mapped["Merchant"] = relationship(back_populates="invoices")


class EvaluationBatch(Base):
    __tablename__ = "evaluation_batches"

    batch_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str | None] = mapped_column(String(50), default="RUNNING")
    total_cases: Mapped[int | None] = mapped_column(Integer, default=50)
    completed_cases: Mapped[int | None] = mapped_column(Integer, default=0)
    kpis: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)

    runs: Mapped[list["EvaluationRun"]] = relationship(back_populates="batch", cascade="all, delete-orphan")


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    batch_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("evaluation_batches.batch_id"), nullable=True
    )
    test_id: Mapped[str] = mapped_column(String(64), nullable=False)
    scenario_type: Mapped[str] = mapped_column(String(100), nullable=False)
    total_turns: Mapped[int | None] = mapped_column(Integer, default=1)
    rag_context_relevance: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), default=1.00)
    rag_faithfulness: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), default=1.00)
    rag_answer_relevance: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), default=1.00)
    policy_breach: Mapped[bool | None] = mapped_column(Boolean, default=False)
    adversarial_intercepted: Mapped[bool | None] = mapped_column(Boolean, default=False)
    final_agent_outcome: Mapped[str | None] = mapped_column(String(100), nullable=True)
    amount_recovered: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=0.00)
    langsmith_trace_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    execution_trace: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    # Measured results (nullable: rows from older versions don't have them)
    invoice_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    link_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    latency_ms: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    final_action: Mapped[str | None] = mapped_column(String(40), nullable=True)
    expected_action: Mapped[str | None] = mapped_column(String(255), nullable=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)

    batch: Mapped["EvaluationBatch"] = relationship(back_populates="runs")


class PaymentLink(Base):
    """Every payment link the agent issued (any mode). Sandbox links are also settled here."""

    __tablename__ = "payment_links"

    link_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    invoice_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("invoices.invoice_id"), nullable=True
    )
    session_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    amount_inr: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    amount_paid_inr: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    short_url: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="created")
    sandbox: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Conversation(Base):
    """A negotiation for one scenario. The server owns the history (clients send only new text)."""

    __tablename__ = "conversations"

    conversation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(String(64), nullable=False)
    merchant_id: Mapped[str] = mapped_column(String(64), ForeignKey("merchants.merchant_id"), nullable=False)
    customer_id: Mapped[str] = mapped_column(String(64), ForeignKey("customers.customer_id"), nullable=False)
    invoice_id: Mapped[str] = mapped_column(String(64), ForeignKey("invoices.invoice_id"), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)

    messages: Mapped[list["ConversationMessage"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="ConversationMessage.id"
    )


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("conversations.conversation_id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(String(8000), nullable=False)
    meta: Mapped[Any | None] = mapped_column(
        JSON, nullable=True
    )  # the agent turn result, for assistant replies
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.core.migrations import add_missing_columns
    from app.core.seed import seed_demo_data

    Base.metadata.create_all(bind=engine)
    add_missing_columns(engine)
    with SessionLocal() as db:
        seed_demo_data(db)
