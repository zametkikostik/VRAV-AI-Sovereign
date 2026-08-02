"""Rate limiter unit tests (in-memory)."""

import time

from core.safety.rate_limit import TokenBucket


def test_token_bucket_allows_burst_then_limits():
    b = TokenBucket(rate=10.0, capacity=2.0)
    ok1, _ = b.allow("k")
    ok2, _ = b.allow("k")
    ok3, retry = b.allow("k")
    assert ok1 and ok2
    assert ok3 is False
    assert retry > 0


def test_token_bucket_refills():
    b = TokenBucket(rate=50.0, capacity=1.0)
    assert b.allow("x")[0] is True
    denied, retry = b.allow("x")
    assert denied is False
    time.sleep(max(0.05, (retry or 0.02) + 0.02))
    ok, _ = b.allow("x")
    assert ok is True
