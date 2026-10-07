"""A sliding-window rate limiter, behind the same swappable-backend shape as
`chat_broker.py` — the in-process counter is per-instance state, so behind a
load balancer N instances allow N x the real limit. Swap `InMemoryRateLimiterBackend`
for a Redis-backed one (`INCR` + `EXPIRE`) when you scale beyond one process.

Where this gets called matters as much as how it works — see chat_router.py's
message loop: the rate check has to run BEFORE content is parsed/validated, or
a flood of garbage frames never consumes any budget and the cap does nothing.
"""

from __future__ import annotations

import time
from typing import Protocol


class RateLimiterBackend(Protocol):
    def hit(self, key: str, window_seconds: int) -> int: ...
    def reset(self, key: str) -> None: ...


class InMemoryRateLimiterBackend:
    """Sliding-window counter in a dict — each `hit()` recounts attempts in the
    trailing `window_seconds`, rather than resetting at fixed clock boundaries.
    Single-instance only, by construction."""

    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = {}

    def hit(self, key: str, window_seconds: int) -> int:
        now = time.monotonic()
        recent = [t for t in self._hits.get(key, []) if now - t < window_seconds]
        recent.append(now)
        self._hits[key] = recent
        return len(recent)

    def reset(self, key: str) -> None:
        self._hits.pop(key, None)


class RateLimiter:
    def __init__(
        self,
        max_attempts: int = 20,
        window_seconds: int = 10,
        backend: RateLimiterBackend | None = None,
    ) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.backend: RateLimiterBackend = backend or InMemoryRateLimiterBackend()

    def check(self, key: str) -> bool:
        """Count this attempt; return True while still under the limit."""
        return self.backend.hit(key, self.window_seconds) <= self.max_attempts
