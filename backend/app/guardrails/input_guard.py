"""Pre-LLM screen for prompt injection, jailbreaks and discount-exploit attempts."""

import re
from typing import Any

ADVERSARIAL_PATTERNS = [
    r"system\s+(override|prompt)",
    r"(ignore|disregard|forget|override)\s+(all\s+|any\s+|your\s+|the\s+)?(previous|prior|above|earlier|system)\s+(instructions|rules|prompts?|directions)",
    r"\b100\s*(%|percent|per\s*cent)\s*(discount|off)\b",
    r"\bgive\s+(me\s+)?(a\s+)?100\s*(%|percent)",
    r"(set|change|make)\s+(the\s+)?(discount|price|amount|payment)\s+(to\s+)?(zero|0|100\s*%)",
    r"free\s+(subscription|membership|plan)\s+forever",
    r"bypass\s+(the\s+)?(payment|guardrails?|policy|checks?)",
    r"\b(act|behave)\s+as\s+(dan|an?\s+admin|developer\s+mode|root)",
    r"\b(you\s+are\s+now|enable|enter)\s+(dan|admin|developer|god|jailbreak)\s*mode",
    r"\b(admin|developer|jailbreak)\s+mode\b",
    r"(zero|0)\s+(rupees?|inr|₹)\s+(payment|link)",
    r"(reveal|show|print|repeat)\s+(your|the)\s+(system\s+)?(prompt|instructions)",
]
_COMPILED = [re.compile(p, re.IGNORECASE) for p in ADVERSARIAL_PATTERNS]

SAFE_RESPONSE = (
    "Safety Intercept: Your request contains unauthorized instructions or unauthorized discount override "
    "attempts. AutonomePay operates within strict merchant policy bounds."
)


def run_pre_llm_guardrail(user_input: str) -> dict[str, Any]:
    text = user_input.strip()
    for pattern in _COMPILED:
        if pattern.search(text):
            return {
                "passed": False,
                "status": "ADVERSARIAL_INTERCEPTED",
                "refusal_reason": f"Adversarial prompt pattern detected: '{pattern.pattern}'",
                "safe_response": SAFE_RESPONSE,
            }
    return {"passed": True, "status": "PASSED", "refusal_reason": None, "safe_response": None}


def screen_conversation(messages: list[dict[str, str]]) -> dict[str, Any]:
    """Run the input guard over every user turn, not only the latest one."""
    for message in messages:
        if message.get("role") == "user":
            result = run_pre_llm_guardrail(message.get("content", ""))
            if not result["passed"]:
                return result
    return run_pre_llm_guardrail("")
