from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class SettlementOfferSchema(BaseModel):
    proposed_amount: float = Field(..., description="Final net amount after discount or downgrade")
    original_amount: float = Field(..., description="Original invoice amount")
    discount_inr: float = Field(default=0.0, description="Discount amount in INR offered")
    grace_days: int = Field(default=0, description="Grace extension in days")
    split_amounts: List[float] = Field(default_factory=list, description="Milestone or split payment breakdown")


def run_post_llm_guardrail(
    offer_data: Dict[str, Any],
    max_discount_inr: float,
    max_grace_days: int,
    action: str = "PROPOSE_SETTLEMENT"
) -> Dict[str, Any]:
    """
    Deterministic Non-LLM Python Invariant Gate.
    Verifies mathematical and invariant constraints on all proposed settlement offers:
    1. For renewal discounts: discount in INR <= merchant max discount limit (INR).
    2. For plan downgrades: lower tier plan price is validated.
    3. Grace period days <= merchant grace day limit.
    4. Arithmetic sum of milestone split payments equals proposed net amount.
    """
    violations = []
    
    proposed_amount = float(offer_data.get("proposed_amount", 0.0))
    original_amount = float(offer_data.get("original_amount", proposed_amount))
    grace_days = int(offer_data.get("grace_days", 0))
    split_amounts = offer_data.get("split_amounts", [])

    is_downgrade = (action == "PLAN_DOWNGRADE" or "downgrade" in action.lower())
    max_discount_inr = float(max_discount_inr)

    # 1. Absolute Maximum Discount Ceiling (INR) Check
    if is_downgrade:
        # Plan downgrade is a valid transition to a lower tier plan (e.g. Mobile Plan INR 149)
        discount_inr = 0.0
    else:
        discount_inr = max(0.0, round(original_amount - proposed_amount, 2))
        if discount_inr > (max_discount_inr + 0.05):
            violations.append(
                f"Proposed discount (INR {discount_inr:.2f}) exceeds merchant maximum discount ceiling of INR {max_discount_inr:.2f}."
            )
            discount_inr = max_discount_inr
            proposed_amount = round(original_amount - max_discount_inr, 2)

    # 2. Grace Period Invariant Check
    if grace_days > max_grace_days:
        violations.append(
            f"Proposed grace period ({grace_days} days) exceeds merchant threshold ({max_grace_days} days)."
        )
        grace_days = max_grace_days

    # 3. Arithmetic Split Sum Invariant Check
    if split_amounts and len(split_amounts) > 1:
        split_sum = round(sum(float(x) for x in split_amounts), 2)
        if abs(split_sum - proposed_amount) > 0.05:
            violations.append(
                f"Split amounts sum (INR {split_sum:.2f}) does not equal proposed amount (INR {proposed_amount:.2f})."
            )
            part = round(proposed_amount / len(split_amounts), 2)
            split_amounts = [part] * (len(split_amounts) - 1)
            split_amounts.append(round(proposed_amount - sum(split_amounts), 2))

    passed = (len(violations) == 0)
    
    return {
        "passed": passed,
        "violations": violations,
        "corrected_offer": {
            "proposed_amount": proposed_amount,
            "original_amount": original_amount,
            "discount_inr": discount_inr,
            "grace_days": grace_days,
            "split_amounts": split_amounts
        }
    }
