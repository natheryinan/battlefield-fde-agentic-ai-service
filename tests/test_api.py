from fastapi.testclient import TestClient
from src.deployment.api.main import app

client = TestClient(app)

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

def test_plan_endpoint():
    resp = client.post("/plan", json={"mission": "Test mission"})
    assert resp.status_code == 200
    body = resp.json()
    assert "steps" in body
    assert isinstance(body["steps"], list)
