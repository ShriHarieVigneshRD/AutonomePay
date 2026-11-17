import hmac
import threading
import time
from collections import defaultdict, deque

from fastapi import Header, HTTPException, Request

from app.core.config import settings


class RateLimiter:
    """Sliding-window limit per client IP.

    shortcut: in-process memory, so limits are per server instance; move to Redis if scaled out.
    """

    def __init__(self, limit_per_minute: int, window_s: float = 60.0):
        self.limit = limit_per_minute
        self.window = window_s
        self._hits: defaultdict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def __call__(self, request: Request) -> None:
        key = request.client.host if request.client else "unknown"
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                raise HTTPException(status_code=429, detail="Too many requests. Please wait a moment.")
            hits.append(now)


chat_rate_limit = RateLimiter(settings.CHAT_RATE_LIMIT_PER_MIN)


def require_admin(x_admin_token: str | None = Header(None)) -> None:
    """Only enforced when ADMIN_TOKEN is configured (e.g. on a public deployment)."""
    if settings.ADMIN_TOKEN and not hmac.compare_digest(x_admin_token or "", settings.ADMIN_TOKEN):
        raise HTTPException(status_code=403, detail="Benchmark runs are disabled on this deployment.")
