"""Provider routing prefers sovereign Ollama."""
from core.orchestrator import AgentOrchestrator
from config.settings import settings

def test_default_is_ollama():
    o = AgentOrchestrator()
    provider, model = o._detect_provider("Hello world")
    assert provider == "ollama"
    assert model == settings.ollama_default_model

def test_bg_routes_bggpt():
    o = AgentOrchestrator()
    provider, model = o._detect_provider("Какъв е GDPR в България?")
    assert provider == "ollama"
    assert model == settings.bggpt_model

def test_explicit_ollama_prefix():
    o = AgentOrchestrator()
    provider, model = o._detect_provider("hi", requested="ollama/llama3.1")
    assert provider == "ollama"
    assert model == "llama3.1"
