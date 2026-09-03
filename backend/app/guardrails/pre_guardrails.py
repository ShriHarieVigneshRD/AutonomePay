import re
from typing import Dict, Any

ADVERSARIAL_PATTERNS = [
    r"system\s+override",
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"give\s+(me\s+)?100%\s+discount",
    r"free\s+subscription\s+forever",
    r"bypass\s+payment",
    r"act\s+as\s+(dan|developer\s+mode)",
    r"zero\s+rupees\s+payment",
    r"admin\s+mode",
]

def run_pre_llm_guardrail(user_input: str) -> Dict[str, Any]:
    """
    Sanitizes user input for prompt injections, jailbreak attempts, or policy exploit claims.
    """
    cleaned_input = user_input.strip()
    
    for pattern in ADVERSARIAL_PATTERNS:
        if re.search(pattern, cleaned_input, re.IGNORECASE):
            return {
                "passed": False,
                "status": "ADVERSARIAL_INTERCEPTED",
                "refusal_reason": f"Adversarial prompt pattern detected: '{pattern}'",
                "safe_response": "Safety Intercept: Your request contains unauthorized instructions or unauthorized discount override attempts. AutonomePay operates within strict merchant policy bounds."
            }

    return {
        "passed": True,
        "status": "PASSED",
        "refusal_reason": None,
        "safe_response": None
    }
