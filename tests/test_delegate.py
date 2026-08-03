from core.delegate.coordinator import MultiAgentDelegate, AGENT_SPECS, ALL_PRIMARY

def test_plan_legal():
    assert "legal" in MultiAgentDelegate().plan_agents("GDPR CELEX регламент")

def test_plan_coding():
    assert "coding" in MultiAgentDelegate().plan_agents("Write a Python function")

def test_plan_math():
    assert "math" in MultiAgentDelegate().plan_agents("Solve the equation x^2")

def test_plan_devops():
    assert "devops" in MultiAgentDelegate().plan_agents("nginx docker deploy")

def test_plan_translator():
    assert "translator" in MultiAgentDelegate().plan_agents("translate преведи to english")

def test_agent_specs_complete():
    for name in list(ALL_PRIMARY) + ["critic"]:
        assert name in AGENT_SPECS

def test_max_parallel_positive():
    d = MultiAgentDelegate()
    assert d.max_parallel >= 1 and d.agent_timeout > 0
