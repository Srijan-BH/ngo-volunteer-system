"""
Boilerplate test file.
Run: pytest tests/ -v
"""

import pytest
from app import create_app
from config.settings import TestingConfig


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app(TestingConfig)
    app.config.update({"TESTING": True})
    yield app


@pytest.fixture
def client(app):
    """Test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """CLI runner."""
    return app.test_cli_runner()


# ─── Health Check ─────────────────────────────────────────────────────────────

class TestHealthCheck:
    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "healthy"

    def test_root_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "healthy"


# ─── Auth ─────────────────────────────────────────────────────────────────────

class TestAuth:
    def test_register_missing_fields(self, client):
        response = client.post("/api/auth/signup", json={})
        assert response.status_code == 422

    def test_login_invalid_credentials(self, client):
        response = client.post("/api/auth/login", json={
            "email": "nonexistent@test.com",
            "password": "WrongPass123!"
        })
        assert response.status_code == 401

    def test_protected_route_without_token(self, client):
        response = client.get("/api/auth/me")
        assert response.status_code == 401
