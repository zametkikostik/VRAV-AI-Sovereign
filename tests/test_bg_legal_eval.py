from evals.run_bg_legal_eval import load_cases, run_offline, score_answer, summarize

def test_cases_file_valid():
    cases = load_cases()
    assert len(cases) >= 30
    assert len({c["id"] for c in cases}) == len(cases)

def test_scorer_gdpr_celex():
    case = {"id": "x", "must_contain_any": ["32016R0679"], "must_not_contain": ["32016L0680"]}
    assert score_answer(case, "CELEX 32016R0679")["passed"]
    assert not score_answer(case, "only 32016L0680")["passed"]

def test_offline_suite_perfect():
    s = summarize(run_offline(load_cases()))
    assert s["accuracy"] == 1.0
    assert s["total"] >= 30
