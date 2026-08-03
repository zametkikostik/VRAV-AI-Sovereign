from core.observability.prometheus import render_prometheus
from core.observability.metrics import metrics

def test_prometheus_render_contains_info():
    metrics.inc("test_counter", 1)
    text = render_prometheus()
    assert "vrav_info" in text
    assert "vrav_test_counter" in text

def test_metrics_prometheus_route():
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)
    r = client.get("/api/metrics/prometheus")
    assert r.status_code == 200
    assert "vrav_info" in r.text
