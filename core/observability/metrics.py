"""Lightweight in-process metrics for VRAV."""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Any, Dict, List


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.counters: Dict[str, int] = defaultdict(int)
        self.latencies: Dict[str, List[float]] = defaultdict(list)

    def inc(self, name: str, n: int = 1) -> None:
        with self._lock:
            self.counters[name] += n

    def observe_ms(self, name: str, ms: float) -> None:
        with self._lock:
            bucket = self.latencies[name]
            bucket.append(float(ms))
            if len(bucket) > 500:
                del bucket[: len(bucket) - 500]

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            lats = {}
            for k, vals in self.latencies.items():
                if not vals:
                    continue
                s = sorted(vals)
                lats[k] = {
                    "count": len(s),
                    "p50_ms": s[len(s) // 2],
                    "p95_ms": s[int(len(s) * 0.95)] if len(s) > 1 else s[0],
                    "max_ms": s[-1],
                }
            return {"counters": dict(self.counters), "latencies": lats}


metrics = Metrics()


class timed:
    def __init__(self, name: str):
        self.name = name
        self.t0 = 0.0

    def __enter__(self):
        self.t0 = time.perf_counter()
        return self

    def __exit__(self, *exc):
        ms = (time.perf_counter() - self.t0) * 1000
        metrics.observe_ms(self.name, ms)
        metrics.inc(f"{self.name}.calls")
