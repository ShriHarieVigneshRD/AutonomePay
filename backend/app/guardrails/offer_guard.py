"""Deterministic (non-LLM) checks on every proposed offer.

The amount returned in `corrected_offer["proposed_amount"]` is the only amount a
payment link may ever be created for.
"""

from typing import Any

from pydantic import BaseModel, field_validator

from app.core.catalog import MerchantRules

ACTIONS = {
    "PROPOSE_SETTLEMENT",
    "PLAN_DOWNGRADE",
    "MILESTONE_SPLIT",
    "PARTIAL_SETTLEMENT",
    "EXTEND_GRACE",
    "HUMAN_ESCALATION",
    "GRACEFUL_DISCONTINUATION",
}
NO_PAYMENT_ACTIONS = {"HUMAN_ESCALATION", "GRACEFUL_DISCONTINUATION"}
TOLERANCE_INR = 0.5  # LLMs round amounts; anything closer than this is the same amount


def to_amount(value: Any) -> float | None:
    """Best-effort number parsing for LLM output ("1,499", "INR 279", 279.0)."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace(",", "").replace("INR", "").replace("₹", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


class SettlementOfferSchema(BaseModel):
    """The LLM's offer, coerced: missing or malformed values become safe defaults, never errors."""

    proposed_amount: float | None = None
    grace_days: int = 0
    split_amounts: list[float] = []

    @field_validator("proposed_amount", mode="before")
    @classmethod
    def _amount(cls, v: Any) -> float | None:
        return to_amount(v)

    @field_validator("grace_days", mode="before")
    @classmethod
    def _grace(cls, v: Any) -> int:
        days = to_amount(v)
        return max(0, int(days)) if days is not None else 0

    @field_validator("split_amounts", mode="before")
    @classmethod
    def _splits(cls, v: Any) -> list[float]:
        if not isinstance(v, list):
            return []
        return [x for x in (to_amount(i) for i in v) if x is not None and x > 0]


def parse_offer(raw: Any) -> SettlementOfferSchema:
    return SettlementOfferSchema.model_validate(raw if isinstance(raw, dict) else {})


def run_post_llm_guardrail(
    offer_data: Any, rules: MerchantRules, original_amount: float, action: str = "PROPOSE_SETTLEMENT"
) -> dict[str, Any]:
    offer = parse_offer(offer_data)
    action = action if action in ACTIONS else "PROPOSE_SETTLEMENT"
    amount = offer.proposed_amount if offer.proposed_amount and offer.proposed_amount > 0 else original_amount
    violations: list[str] = []
    checks: list[dict[str, str]] = []
    splits: list[float] = []
    discount = 0.0

    def record(check_id: str, label: str, ok: bool, detail: str) -> None:
        checks.append(
            {"id": check_id, "label": label, "status": "passed" if ok else "corrected", "detail": detail}
        )
        if not ok:
            violations.append(detail)

    def same(a: float, b: float) -> bool:
        return abs(a - b) <= TOLERANCE_INR

    # An exact policy amount announced as a plain settlement is that policy option.
    partial = rules.partial_amount(original_amount)
    if action == "PROPOSE_SETTLEMENT":
        if partial and same(amount, partial):
            action = "PARTIAL_SETTLEMENT"
        elif rules.split_allowed(original_amount) and same(amount, rules.split_amounts(original_amount)[0]):
            action = "MILESTONE_SPLIT"

    if action in NO_PAYMENT_ACTIONS:
        amount = original_amount
        checks.append(
            {"id": "amount", "label": "Offer amount", "status": "skipped", "detail": "No payment requested."}
        )

    elif action == "PLAN_DOWNGRADE":
        lower = rules.lower_plans(original_amount)
        match = next((p for p in lower if same(p.price_inr, amount)), None)
        if match:
            amount = match.price_inr
            record("plan", "Listed plan price", True, f"Downgrade to {match.name} at INR {amount:.2f}.")
        elif lower:
            target = min(lower, key=lambda p: abs(p.price_inr - amount))
            record("plan", "Listed plan price", False,
                   f"Downgrade price INR {amount:.2f} is not a listed plan; using {target.name} at INR {target.price_inr:.2f}.")  # fmt: skip
            amount = target.price_inr
        else:
            record(
                "plan",
                "Listed plan price",
                False,
                "This merchant has no cheaper plan; treated as a discount request.",
            )
            action = "PROPOSE_SETTLEMENT"

    elif action == "MILESTONE_SPLIT":
        if rules.split_allowed(original_amount):
            splits = rules.split_amounts(original_amount)
            pct = "/".join(f"{p:g}" for p in rules.split_schedule_pct)
            record("split", "Approved split schedule", same(amount, splits[0]),
                   f"{pct} split: INR {splits[0]:.2f} due now." if same(amount, splits[0])
                   else f"First instalment INR {amount:.2f} does not match the {pct} schedule; using INR {splits[0]:.2f}.")  # fmt: skip
            amount = splits[0]
        else:
            record("split", "Approved split schedule", False,
                   "Split payments are not permitted for this merchant or invoice size.")  # fmt: skip
            action = "PROPOSE_SETTLEMENT"

    elif action == "PARTIAL_SETTLEMENT":
        if partial:
            floor = round(partial - rules.max_discount_inr, 2)
            ok = floor - TOLERANCE_INR <= amount <= partial + TOLERANCE_INR
            record("partial", "Undisputed portion", ok,
                   f"Undisputed {rules.partial_settlement_pct:g}% portion: INR {amount:.2f}." if ok
                   else f"Partial amount INR {amount:.2f} is outside the policy range; using INR {partial:.2f}.")  # fmt: skip
            amount = amount if ok else partial
            discount = round(partial - amount, 2)
        else:
            record(
                "partial",
                "Undisputed portion",
                False,
                "Partial settlement is not permitted for this merchant.",
            )
            action = "PROPOSE_SETTLEMENT"

    if action in ("PROPOSE_SETTLEMENT", "EXTEND_GRACE"):
        if amount > original_amount + TOLERANCE_INR:
            record("ceiling", "Amount within invoice", False,
                   f"Proposed INR {amount:.2f} is above the invoice; using INR {original_amount:.2f}.")  # fmt: skip
            amount = original_amount
        discount = max(0.0, round(original_amount - amount, 2))
        if discount > rules.max_discount_inr + 0.05:
            record("discount", "Discount ceiling", False,
                   f"Proposed discount (INR {discount:.2f}) exceeds merchant maximum discount ceiling of INR {rules.max_discount_inr:.2f}.")  # fmt: skip
            discount = rules.max_discount_inr
            amount = round(original_amount - discount, 2)
        else:
            record("discount", "Discount ceiling", True,
                   f"Discount INR {discount:.2f} within the INR {rules.max_discount_inr:.2f} ceiling.")  # fmt: skip

    grace_days = offer.grace_days
    if grace_days > rules.max_grace_days:
        record("grace", "Grace period limit", False,
               f"Proposed grace period ({grace_days} days) exceeds merchant threshold ({rules.max_grace_days} days).")  # fmt: skip
        grace_days = rules.max_grace_days
    else:
        record("grace", "Grace period limit", True, f"{grace_days} of {rules.max_grace_days} allowed days.")

    if action != "MILESTONE_SPLIT" and len(offer.split_amounts) > 1:
        split_sum = round(sum(offer.split_amounts), 2)
        if abs(split_sum - amount) > 0.05:
            record("split_sum", "Split amounts add up", False,
                   f"Split amounts sum (INR {split_sum:.2f}) does not equal proposed amount (INR {amount:.2f}).")  # fmt: skip
            part = round(amount / len(offer.split_amounts), 2)
            splits = [part] * (len(offer.split_amounts) - 1)
            splits.append(round(amount - sum(splits), 2))
        else:
            splits = offer.split_amounts

    return {
        "passed": not violations,
        "violations": violations,
        "checks": checks,
        "action": action,
        "corrected_offer": {
            "proposed_amount": round(amount, 2),
            "original_amount": original_amount,
            "discount_inr": round(discount, 2),
            "grace_days": grace_days,
            "split_amounts": splits,
        },
    }
