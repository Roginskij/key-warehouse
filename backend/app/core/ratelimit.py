"""Protection against brute force and request floods.

Sliding-window counters kept in memory. That is enough for one server process.
When the API runs in several processes / servers, swap `MemoryStore` for a
Redis-backed store with the same two methods — nothing else changes.

Three layers:
1. Global per-IP limit on every request (middleware) — stops floods.
2. Per-IP limits on sensitive endpoints (login, register, password reset...).
3. Per-account login lockout: too many wrong passwords for one e-mail → that
   e-mail is locked for a while, whatever IP the attempts come from.
"""

import time
from collections import deque
from dataclasses import dataclass

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.errors import AppError


@dataclass(frozen=True)
class Limit:
    count: int
    seconds: int


class MemoryStore:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}
        self._calls = 0

    def _window(self, key: str, seconds: int, now: float) -> deque[float]:
        q = self._hits.setdefault(key, deque())
        while q and q[0] <= now - seconds:
            q.popleft()
        return q

    def hit(self, key: str, limit: Limit) -> int:
        """Counts a hit. Returns 0 if allowed, else seconds until the next allowed hit."""
        now = time.monotonic()
        self._maybe_cleanup(now)
        q = self._window(key, limit.seconds, now)
        if len(q) >= limit.count:
            return max(1, int(q[0] + limit.seconds - now) + 1)
        q.append(now)
        return 0

    def blocked_for(self, key: str, limit: Limit) -> int:
        """Like hit() but does not count: is the key already over the limit?"""
        now = time.monotonic()
        q = self._window(key, limit.seconds, now)
        if len(q) >= limit.count:
            return max(1, int(q[0] + limit.seconds - now) + 1)
        return 0

    def add(self, key: str) -> None:
        self._hits.setdefault(key, deque()).append(time.monotonic())

    def reset(self, key: str) -> None:
        self._hits.pop(key, None)

    def clear(self) -> None:
        self._hits.clear()

    def _maybe_cleanup(self, now: float) -> None:
        self._calls += 1
        if self._calls % 1000:
            return
        horizon = now - 24 * 3600  # longest window we use
        for key in [k for k, q in self._hits.items() if not q or q[-1] < horizon]:
            del self._hits[key]


store = MemoryStore()

# --- limits ----------------------------------------------------------------------------

GLOBAL = Limit(300, 60)  # any endpoint, per IP
LOGIN_IP = (Limit(20, 60), Limit(100, 3600))
REGISTER_IP = (Limit(10, 3600),)
EMAIL_SENDING_IP = (Limit(5, 900),)  # forgot password, resend verification
TOKEN_IP = (Limit(20, 900),)  # verify-email, reset-password, invitation links
REFRESH_IP = (Limit(60, 60),)
# Per e-mail address
LOGIN_FAILURES = Limit(5, 900)  # 5 wrong passwords → locked 15 min
EMAILS_PER_ADDRESS = Limit(3, 3600)  # at most 3 reset / verify mails per hour


class TooManyRequests(AppError):
    def __init__(self, retry_after: int, code: str = "rate_limited") -> None:
        super().__init__(
            code, 429, "Too many requests, try again later", {"retry_after": retry_after}
        )


def client_ip(request: Request) -> str:
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check(key: str, *limits: Limit) -> None:
    """Raise 429 if any limit is exceeded."""
    if not settings.rate_limit_enabled:
        return
    for i, limit in enumerate(limits):
        wait = store.hit(f"{key}:{i}", limit)
        if wait:
            raise TooManyRequests(wait)


def limit_ip(name: str, *limits: Limit):
    """FastAPI dependency: per-IP limit for one endpoint."""

    async def dependency(request: Request) -> None:
        check(f"{name}:{client_ip(request)}", *limits)

    return dependency


# --- login lockout per account ---------------------------------------------------------


def login_locked_for(email: str) -> int:
    if not settings.rate_limit_enabled:
        return 0
    return store.blocked_for(f"login-fail:{email}", LOGIN_FAILURES)


def login_failed(email: str) -> None:
    if settings.rate_limit_enabled:
        store.add(f"login-fail:{email}")


def login_succeeded(email: str) -> None:
    store.reset(f"login-fail:{email}")


def email_send_allowed(kind: str, email: str) -> bool:
    """Silently caps mails to one address (the endpoint still answers 204, so it
    can't be used to bomb someone's mailbox or to find out which e-mails exist)."""
    if not settings.rate_limit_enabled:
        return True
    return store.hit(f"mail:{kind}:{email}", EMAILS_PER_ADDRESS) == 0


# --- global middleware -----------------------------------------------------------------


class GlobalRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if settings.rate_limit_enabled and request.url.path != "/health":
            wait = store.hit(f"global:{client_ip(request)}", GLOBAL)
            if wait:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "rate_limited",
                            "message": "Too many requests, try again later",
                            "params": {"retry_after": wait},
                        }
                    },
                    headers={"Retry-After": str(wait)},
                )
        return await call_next(request)
