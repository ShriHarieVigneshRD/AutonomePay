import hashlib
import json
import logging
from typing import Any

import litellm

from app.core.config import settings

logger = logging.getLogger(__name__)


class LiteLLMGateway:
    def __init__(self):
        self.semantic_cache: dict[str, str] = {}
        self.session_token_usage: dict[str, int] = {}

    def _hash_prompt(self, messages: list[dict[str, str]], system_prompt: str = "") -> str:
        raw_text = json.dumps(messages, sort_keys=True) + "||" + system_prompt
        return hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    def check_token_budget(self, session_id: str, new_tokens: int = 200) -> bool:
        current_tokens = self.session_token_usage.get(session_id, 0)
        return (current_tokens + new_tokens) <= settings.MAX_SESSION_TOKEN_BUDGET

    def completion(
        self,
        messages: list[dict[str, str]],
        system_prompt: str = "",
        session_id: str = "default_session",
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        # 1. Semantic Cache Lookup
        cache_key = self._hash_prompt(messages, system_prompt)
        if cache_key in self.semantic_cache:
            logger.info("Semantic cache HIT for key: %s", cache_key[:8])
            return {
                "content": self.semantic_cache[cache_key],
                "cached": True,
                "model_used": "semantic_cache",
                "tokens_used": 0,
            }

        # 2. Token Budget Check
        if not self.check_token_budget(session_id):
            return {
                "content": "Token spend budget threshold reached for this session (4,000 token limit). Request throttled.",
                "cached": False,
                "model_used": "none",
                "tokens_used": 0,
                "error": "TOKEN_BUDGET_EXCEEDED",
            }

        # Format full messages
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        # 3. Call LiteLLM, trying each model in the fallback chain
        content = None
        model_used = None
        tokens = 150

        for m_name in settings.model_chain:
            # Ensure model starts with openrouter/ prefix for LiteLLM routing
            formatted_model = m_name if m_name.startswith("openrouter/") else f"openrouter/{m_name}"
            try:
                logger.info("Attempting LLM call with model: %s", formatted_model)
                response = litellm.completion(
                    model=formatted_model,
                    messages=full_messages,
                    temperature=temperature,
                    max_tokens=settings.LLM_MAX_TOKENS,
                    api_key=settings.OPENROUTER_API_KEY or None,
                )
                content = response.choices[0].message.content
                tokens = getattr(response.usage, "total_tokens", 150)
                model_used = formatted_model
                break
            except Exception as e:
                logger.warning("Model %s failed: %s. Trying next in fallback chain.", formatted_model, e)

        if not content:
            logger.error("All models in fallback chain failed. Returning deterministic safe fallback.")
            model_used = "deterministic_fallback"
            content = json.dumps(
                {
                    "action": "PROPOSE_SETTLEMENT",
                    "reasoning": "Standard policy offer under gateway retry rules.",
                    "offer": {
                        "proposed_amount": 279.0,
                        "discount_pct": 5.0,
                        "grace_days": 3,
                        "split_payments": [],
                    },
                    "message": "We understand your concern. As per policy, we can offer a 5% concession or a 3-day grace period. Would you like a fresh Razorpay payment link?",
                }
            )
            tokens = 50

        # Update cache & token usage
        self.semantic_cache[cache_key] = content
        self.session_token_usage[session_id] = self.session_token_usage.get(session_id, 0) + tokens

        return {
            "content": content,
            "cached": False,
            "model_used": model_used,
            "tokens_used": tokens,
        }


gateway = LiteLLMGateway()
