"""Offline scorer tests for BG legal eval harness."""
from evals.run_bg_legal_eval import load_cases, run_offline, score_answer, summarize

def test_cases_file_valid():
    cases = load_cases()
    assert len(cases) >= 5
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids))

def test_scorer_gdpr_celex():
    case = {"id": "x", "must_contain_any": ["32016R0679"], "must_not_contain": ["32016L0680"]}
    assert score_answer(case, "CELEX 32016R0679 is GDPR")["passed"]
    assert not score_answer(case, "wrong 32016L0680 only")["passed"]

def test_offline_suite_perfect():
    results = run_offline(load_cases())
    s = summarize(results)
    assert s["accuracy"] == 1.0
    assert s["failed"] == 0
