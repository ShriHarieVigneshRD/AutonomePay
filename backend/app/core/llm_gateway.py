"""LiteLLM wrapper: model fallback chain, response cache, per-conversation token budget."""

import hashlib
import json
import logging
import time
from collections import OrderedDict
from typing import Any

import litellm

from app.core.config import settings

logger = logging.getLogger(__name__)

MAX_CACHED_RESPONSES = 256
MAX_TRACKED_SESSIONS = 2000
ESTIMATED_TOKENS_PER_CALL = 200
# OpenRouter free tier: 20 requests/min and 50/day without purchased credits.
MIN_PATIENT_INTERVAL_S = 3.5  # ~17 requests/min
RATE_LIMIT_WAITS_S = (15, 30, 60)


class _LRU(OrderedDict):
    def __init__(self, max_size: int):
        super().__init__()
        self.max_size = max_size

    def put(self, key, value) -> None:
        self[key] = value
        self.move_to_end(key)
        while len(self) > self.max_size:
            self.popitem(last=False)


class LiteLLMGateway:
    def __init__(self):
        self.semantic_cache: _LRU = _LRU(MAX_CACHED_RESPONSES)
        self.session_token_usage: _LRU = _LRU(MAX_TRACKED_SESSIONS)
        self._last_call = 0.0  # monotonic time of the last request, for pacing

    @staticmethod
    def _cache_key(messages: list[dict[str, str]], system_prompt: str) -> str:
        raw = json.dumps(messages, sort_keys=True) + "||" + system_prompt
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def tokens_used(self, session_id: str) -> int:
        return self.session_token_usage.get(session_id, 0)

    def check_token_budget(self, session_id: str, new_tokens: int = ESTIMATED_TOKENS_PER_CALL) -> bool:
        return self.tokens_used(session_id) + new_tokens <= settings.MAX_SESSION_TOKEN_BUDGET

    def completion(
        self,
        messages: list[dict[str, str]],
        system_prompt: str = "",
        session_id: str = "default_session",
        temperature: float = 0.2,
        patient: bool = False,
    ) -> dict[str, Any]:
        """Returns {"content", "cached", "model_used", "tokens_used"} plus "error" when no model answered.

        Errors: LLM_NOT_CONFIGURED (no API key), TOKEN_BUDGET_EXCEEDED, LLM_UNAVAILABLE (every model failed),
        RATE_LIMITED, DAILY_LIMIT (free tier). `patient` (benchmark runs) paces requests and waits out
        per-minute rate limits; live chat falls back to the policy heuristic at once.
        """
        cache_key = self._cache_key(messages, system_prompt)
        if cache_key in self.semantic_cache:
            self.semantic_cache.move_to_end(cache_key)
            return {
                "content": self.semantic_cache[cache_key],
                "cached": True,
                "model_used": "cache",
                "tokens_used": 0,
            }

        if not settings.OPENROUTER_API_KEY:
            return self._failure("LLM_NOT_CONFIGURED")
        if not self.check_token_budget(session_id):
            return self._failure("TOKEN_BUDGET_EXCEEDED")

        full_messages = ([{"role": "system", "content": system_prompt}] if system_prompt else []) + messages
        waits = list(RATE_LIMIT_WAITS_S) if patient else []
        while True:
            rate_limited = daily_limit = False
            for name in settings.model_chain:
                model = name if name.startswith("openrouter/") else f"openrouter/{name}"
                if patient:  # stay under the free tier's per-minute limit
                    time.sleep(max(0.0, self._last_call + MIN_PATIENT_INTERVAL_S - time.monotonic()))
                self._last_call = time.monotonic()
                try:
                    response: Any = litellm.completion(
                        model=model,
                        messages=full_messages,
                        temperature=temperature,
                        max_tokens=settings.LLM_MAX_TOKENS,
                        api_key=settings.OPENROUTER_API_KEY,
                    )
                    content = response.choices[0].message.content
                except Exception as e:
                    if getattr(e, "status_code", None) == 429:
                        rate_limited = True
                        daily_limit = daily_limit or "per-day" in str(e).lower()
                    logger.warning("Model %s failed: %s. Trying next in fallback chain.", model, e)
                    continue
                if not content:
                    logger.warning("Model %s returned an empty reply. Trying next in fallback chain.", model)
                    continue
                tokens = int(
                    getattr(getattr(response, "usage", None), "total_tokens", 0) or ESTIMATED_TOKENS_PER_CALL
                )
                self.semantic_cache.put(cache_key, content)
                self.session_token_usage.put(session_id, self.tokens_used(session_id) + tokens)
                return {"content": content, "cached": False, "model_used": model, "tokens_used": tokens}

            if daily_limit:  # waiting won't help until the next UTC day
                logger.error("Free-tier daily LLM limit reached.")
                return self._failure("DAILY_LIMIT")
            if not (rate_limited and waits):
                logger.error("All models in the fallback chain failed.")
                return self._failure("RATE_LIMITED" if rate_limited else "LLM_UNAVAILABLE")
            wait = waits.pop(0)
            logger.warning("Every model is rate-limited; retrying the chain in %ss.", wait)
            time.sleep(wait)

    @staticmethod
    def _failure(error: str) -> dict[str, Any]:
        return {"content": "", "cached": False, "model_used": None, "tokens_used": 0, "error": error}


gateway = LiteLLMGateway()
