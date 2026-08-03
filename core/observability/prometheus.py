"""Prometheus text exposition."""
from __future__ import annotations
from typing import List
from core.observability.metrics import metrics

def render_prometheus() -> str:
    snap = metrics.snapshot()
    lines: List[str] = [
        "# HELP vrav_info VRAV AI process info",
        "# TYPE vrav_info gauge",
        'vrav_info{version="0.9.3"} 1',
    ]
    for name, val in sorted((snap.get("counters") or {}).items()):
        safe = name.replace(".", "_").replace("-", "_")
        lines.append(f"# TYPE vrav_{safe} counter")
        lines.append(f"vrav_{safe} {int(val)}")
    for name, stats in sorted((snap.get("latencies") or {}).items()):
        safe = name.replace(".", "_").replace("-", "_")
        lines.append(f"# TYPE vrav_{safe}_p50_ms gauge")
        lines.append(f"vrav_{safe}_p50_ms {float(stats.get('p50_ms') or 0)}")
        lines.append(f"# TYPE vrav_{safe}_p95_ms gauge")
        lines.append(f"vrav_{safe}_p95_ms {float(stats.get('p95_ms') or 0)}")
    lines.append("")
    return "\n".join(lines)
