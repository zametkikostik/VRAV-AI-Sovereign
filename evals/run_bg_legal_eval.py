#!/usr/bin/env python3
"""BG/EU legal eval. offline | live against API."""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
from typing import Any, Dict, List

CASES_PATH = Path(__file__).resolve().parent / "bg_legal_cases.json"
OFFLINE_STUBS = {
    "gdpr_access_deadline": "По чл. 12 GDPR срокът е един месец. Това не е индивидуална юридическа консултация.",
    "gdpr_celex": "GDPR CELEX is 32016R0679.",
    "ai_act_celex": "EU AI Act CELEX 32024R1689.",
    "no_invented_article": "В GDPR няма чл. 999 — такъв член не съществува.",
    "disclaimer_required": "Право на изтриване (чл. 17 GDPR). Това не е индивидуална юридическа консултация.",
}

def load_cases() -> List[Dict[str, Any]]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))

def score_answer(case: Dict[str, Any], answer: str) -> Dict[str, Any]:
    lower = (answer or "").lower()
    must_any = case.get("must_contain_any") or []
    must_not = case.get("must_not_contain") or []
    hit_any = True if not must_any else any(m.lower() in lower for m in must_any)
    hit_forbidden = any(m.lower() in lower for m in must_not if m)
    return {
        "id": case["id"], "passed": hit_any and not hit_forbidden,
        "hit_any": hit_any, "hit_forbidden": hit_forbidden,
        "answer_preview": (answer or "")[:400],
        "category": case.get("category"), "difficulty": case.get("difficulty"),
    }

def _offline_answer(case: Dict[str, Any]) -> str:
    if case["id"] in OFFLINE_STUBS:
        return OFFLINE_STUBS[case["id"]]
    bits = list(case.get("must_contain_any") or [])[:4]
    body = " ".join(bits) if bits else (case.get("gold_notes") or "ok")
    if case.get("lang") == "bg" or case.get("category") in ("gdpr", "meta", "labor"):
        body += " Това не е индивидуална юридическа консултация."
    if case.get("category") == "safety":
        body = "Няма такъв текст / invalid or unknown reference. " + body
    return body

def run_offline(cases):
    return [score_answer(c, _offline_answer(c)) for c in cases]

def call_live(base: str, endpoint: str, question: str, timeout: float = 180.0) -> str:
    import httpx
    base = base.rstrip("/")
    if endpoint == "agent":
        r = httpx.post(f"{base}/api/agent", json={"prompt": question}, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        return data.get("response") or data.get("final") or json.dumps(data)
    if endpoint == "delegate":
        r = httpx.post(f"{base}/api/delegate", json={"prompt": question, "parallel": True}, timeout=timeout)
        r.raise_for_status()
        return r.json().get("final") or json.dumps(r.json())
    r = httpx.post(f"{base}/api/stream", json={"prompt": question, "temperature": 0.1}, timeout=timeout)
    r.raise_for_status()
    return r.json().get("response") or json.dumps(r.json())

def run_live(cases, base, endpoint):
    results = []
    for c in cases:
        t0 = time.time()
        try:
            row = score_answer(c, call_live(base, endpoint, c["question"]))
            row["latency_s"] = round(time.time() - t0, 2)
        except Exception as e:
            row = {"id": c["id"], "passed": False, "error": str(e),
                   "latency_s": round(time.time() - t0, 2), "category": c.get("category")}
        results.append(row)
        print(f"  [{row.get('passed')}] {c['id']}")
    return results

def summarize(results):
    n = len(results)
    p = sum(1 for r in results if r.get("passed"))
    by_cat = {}
    for r in results:
        by_cat.setdefault(r.get("category") or "?", []).append(bool(r.get("passed")))
    return {
        "total": n, "passed": p, "failed": n - p,
        "accuracy": round(p / n, 3) if n else 0.0,
        "by_category": {k: {"passed": sum(v), "total": len(v)} for k, v in by_cat.items()},
    }

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["offline", "live"], default="offline")
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--endpoint", choices=["agent", "stream", "delegate"], default="agent")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    cases = load_cases()
    print(f"Loaded {len(cases)} cases")
    results = run_offline(cases) if args.mode == "offline" else run_live(cases, args.base, args.endpoint)
    summary = summarize(results)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    out = Path(args.out) if args.out else Path(__file__).parent / f"report_{args.mode}.json"
    out.write_text(json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    if args.mode == "offline" and summary["accuracy"] < 1.0:
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
