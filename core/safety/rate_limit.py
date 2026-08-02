"""
Simple in-memory token-bucket rate limiter (per API key / IP).

For multi-worker production, replace store with Redis.
"""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock
from typing import Dict, Tuple


class TokenBucket:
    def __init__(self, rate: float = 1.0, capacity: float = 30.0):
        """rate = tokens per second, capacity = burst size."""
        self.rate = rate
        self.capacity = capacity
        self._tokens: Dict[str, float] = defaultdict(lambda: capacity)
        self._updated: Dict[str, float] = defaultdict(time.monotonic)
        self._lock = Lock()

    def allow(self, key: str, cost: float = 1.0) -> Tuple[bool, float]:
        """Returns (allowed, retry_after_seconds)."""
        now = time.monotonic()
        with self._lock:
            last = self._updated[key]
            tokens = self._tokens[key]
            tokens = min(self.capacity, tokens + (now - last) * self.rate)
            self._updated[key] = now
            if tokens >= cost:
                self._tokens[key] = tokens - cost
                return True, 0.0
            self._tokens[key] = tokens
            need = cost - tokens
            retry = need / self.rate if self.rate > 0 else 60.0
            return False, round(retry, 2)


# Global limiter: ~30 req/min sustained with burst 20
api_limiter = TokenBucket(rate=0.5, capacity=20.0)
