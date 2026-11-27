from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_returns_healthy_status() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "application": "FixIt API",
    }


def test_root_endpoint_returns_api_information() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["application"] == "FixIt API"
    assert response.json()["health"] == "/api/v1/health"
