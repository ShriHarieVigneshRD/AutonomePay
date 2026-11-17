"""Merchant catalogue (data/merchants.json) and the per-merchant rules the guardrails enforce."""

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.database import Merchant

CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "merchants.json"


@lru_cache
def load_catalog() -> dict[str, dict[str, Any]]:
    data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return {m["merchant_id"]: m for m in data["merchants"]}


@dataclass(frozen=True)
class Plan:
    name: str
    price_inr: float
    period: str | None = None


@dataclass(frozen=True)
class MerchantRules:
    """Everything the offer guard needs to know about one merchant. Defaults are the strictest."""

    merchant_id: str
    name: str
    max_discount_inr: float = 0.0
    max_grace_days: int = 0
    auto_escalation_limit: float = 50_000.0
    plans: tuple[Plan, ...] = ()
    split_schedule_pct: tuple[float, ...] = ()
    split_min_invoice_inr: float = 0.0
    partial_settlement_pct: float | None = None

    def lower_plans(self, invoice_amount: float) -> list[Plan]:
        return [p for p in self.plans if p.price_inr < invoice_amount]

    def split_allowed(self, invoice_amount: float) -> bool:
        return len(self.split_schedule_pct) > 1 and invoice_amount >= self.split_min_invoice_inr

    def split_amounts(self, invoice_amount: float) -> list[float]:
        parts = [round(invoice_amount * pct / 100, 2) for pct in self.split_schedule_pct[:-1]]
        return [*parts, round(invoice_amount - sum(parts), 2)]

    def partial_amount(self, invoice_amount: float) -> float | None:
        if not self.partial_settlement_pct:
            return None
        return round(invoice_amount * self.partial_settlement_pct / 100, 2)


def rules_from_merchant(m: Merchant) -> MerchantRules:
    return MerchantRules(
        merchant_id=m.merchant_id,
        name=m.name,
        max_discount_inr=float(m.max_discount_inr or 0),
        max_grace_days=int(m.max_grace_days or 0),
        auto_escalation_limit=float(m.auto_escalation_limit or 50_000),
        plans=tuple(Plan(p.name, float(p.price_inr), p.period) for p in m.plans),
        split_schedule_pct=tuple(float(x) for x in (m.split_schedule_pct or [])),
        split_min_invoice_inr=float(m.split_min_invoice_inr or 0),
        partial_settlement_pct=float(m.partial_settlement_pct) if m.partial_settlement_pct else None,
    )


def get_merchant_rules(db: Session, merchant_id: str) -> MerchantRules | None:
    merchant = db.get(Merchant, merchant_id)
    return rules_from_merchant(merchant) if merchant else None
