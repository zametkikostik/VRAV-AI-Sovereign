"""Multi-agent delegate unit tests (offline planning)."""

from core.delegate.coordinator import MultiAgentDelegate, AGENT_SPECS


def test_plan_legal():
    d = MultiAgentDelegate()
    agents = d.plan_agents("Какво казва GDPR и CELEX регламент?")
    assert "legal" in agents
    assert "critic" in agents


def test_plan_coding():
    d = MultiAgentDelegate()
    agents = d.plan_agents("Write a Python function to parse JSON")
    assert "coding" in agents


def test_plan_default_research():
    d = MultiAgentDelegate()
    agents = d.plan_agents("Tell me about the weather in general terms")
    assert "research" in agents or "critic" in agents


def test_agent_specs_complete():
    for name in ("legal", "research", "coding", "critic"):
        assert name in AGENT_SPECS
        assert "system" in AGENT_SPECS[name]
