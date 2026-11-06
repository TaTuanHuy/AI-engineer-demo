from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_read_root() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Welcome to Demo AI API",
        "docs_url": "/docs",
    }


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_swagger_is_available() -> None:
    response = client.get("/docs")

    assert response.status_code == 200
    assert "swagger-ui" in response.text.lower()


def test_config_status_does_not_expose_api_key() -> None:
    response = client.get("/config/status")

    assert response.status_code == 200
    assert response.json()["environment"] == "development"
    assert "gemini_api_key" not in response.json()


def test_demo_service() -> None:
    response = client.post("/api/demo", json={"name": "Ada"})

    assert response.status_code == 200
    assert response.json() == {
        "message": "Hello, Ada! The demo service is working.",
        "received_name": "Ada",
        "service": "local-demo-service",
    }


def test_demo_page_has_button() -> None:
    response = client.get("/demo")

    assert response.status_code == 200
    assert "Call service" in response.text
    assert "/api/demo" in response.text

