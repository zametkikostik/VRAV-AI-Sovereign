"""
Token-bucket rate limiter (per API key / IP).

Backend:
  1. Redis (if REDIS_URL set and redis package available) — multi-worker safe
  2. In-memory fallback — single process
"""

from __future__ import annotations

import logging
import time
from threading import Lock
from typing import Dict, Tuple

from config.settings import settings

logger = logging.getLogger("vrav.ratelimit")


class TokenBucket:
    def __init__(self, rate: float = 1.0, capacity: float = 30.0):
        self.rate = rate
        self.capacity = capacity
        self._tokens: Dict[str, float] = {}
        self._updated: Dict[str, float] = {}
        self._lock = Lock()

    def allow(self, key: str, cost: float = 1.0) -> Tuple[bool, float]:
        now = time.monotonic()
        with self._lock:
            if key not in self._updated:
                tokens = self.capacity
            else:
                elapsed = max(0.0, now - self._updated[key])
                tokens = min(self.capacity, self._tokens.get(key, self.capacity) + elapsed * self.rate)
            self._updated[key] = now
            if tokens >= cost:
                self._tokens[key] = tokens - cost
                return True, 0.0
            self._tokens[key] = tokens
            need = cost - tokens
            retry = need / self.rate if self.rate > 0 else 60.0
            return False, round(retry, 2)


class RedisTokenBucket:
    def __init__(self, redis_url: str, rate: float = 0.5, capacity: float = 20.0):
        import redis  # type: ignore

        self.rate = rate
        self.capacity = capacity
        self._r = redis.from_url(redis_url, decode_responses=True)
        self._script = self._r.register_script(
            """
            local key = KEYS[1]
            local rate = tonumber(ARGV[1])
            local capacity = tonumber(ARGV[2])
            local cost = tonumber(ARGV[3])
            local now = tonumber(ARGV[4])
            local data = redis.call('HMGET', key, 'tokens', 'ts')
            local tokens = tonumber(data[1])
            local ts = tonumber(data[2])
            if tokens == nil then tokens = capacity end
            if ts == nil then ts = now end
            local elapsed = now - ts
            if elapsed < 0 then elapsed = 0 end
            tokens = math.min(capacity, tokens + elapsed * rate)
            if tokens >= cost then
              tokens = tokens - cost
              redis.call('HMSET', key, 'tokens', tokens, 'ts', now)
              redis.call('EXPIRE', key, 3600)
              return {1, 0}
            else
              redis.call('HMSET', key, 'tokens', tokens, 'ts', now)
              redis.call('EXPIRE', key, 3600)
              local need = cost - tokens
              local retry = 0
              if rate > 0 then retry = need / rate end
              return {0, retry}
            end
            """
        )

    def allow(self, key: str, cost: float = 1.0) -> Tuple[bool, float]:
        try:
            now = time.time()
            res = self._script(keys=[f"vrav:rl:{key[:128]}"], args=[self.rate, self.capacity, cost, now])
            return int(res[0]) == 1, round(float(res[1] or 0), 2)
        except Exception as e:
            logger.warning("Redis rate limit failed, allowing: %s", e)
            return True, 0.0


def _build_limiter():
    rate = float(getattr(settings, "rate_limit_rate", 0.5) or 0.5)
    capacity = float(getattr(settings, "rate_limit_capacity", 20.0) or 20.0)
    redis_url = getattr(settings, "redis_url", None)
    if redis_url:
        try:
            lim = RedisTokenBucket(redis_url, rate=rate, capacity=capacity)
            lim._r.ping()
            logger.info("Rate limiter: Redis")
            return lim
        except Exception as e:
            logger.warning("Redis unavailable (%s), in-memory limiter", e)
    return TokenBucket(rate=rate, capacity=capacity)


api_limiter = _build_limiter()
