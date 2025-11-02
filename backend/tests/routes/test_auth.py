import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
from sqlalchemy.orm import Session
from backend.main import app


client = TestClient(app)


@pytest.fixture
def mock_db():
    """Fixture that returns a mock database session."""
    return MagicMock(spec=Session)


# -----------------------------
# /auth/login endpoint
# -----------------------------
@patch("backend.routes.auth.Flow")
def test_login_creates_auth_url(mock_flow):
    mock_instance = MagicMock()
    mock_instance.authorization_url.return_value = (
        "https://google.com/auth",
        "state123",
    )
    mock_flow.from_client_config.return_value = mock_instance

    response = client.get("/auth/login?user_id=1")

    assert response.status_code == 200
    data = response.json()
    assert "auth_url" in data
    assert data["auth_url"].startswith("https://google.com")
    assert data["state"] == "state123"


# -----------------------------
# /auth/callback endpoint
# -----------------------------
@patch("backend.routes.auth.build")
@patch("backend.routes.auth.Flow")
def test_auth_callback_creates_user_and_account(
    mock_flow, mock_build, mock_db, monkeypatch
):
    """Simulate Google OAuth callback with valid data."""
    # Mock dependencies
    monkeypatch.setattr("backend.routes.auth.get_db", lambda: mock_db)
    mock_flow_instance = MagicMock()
    mock_flow_instance.fetch_token.return_value = None
    mock_flow_instance.credentials = MagicMock(to_json=lambda: '{"token": "abc"}')
    mock_flow.from_client_config.return_value = mock_flow_instance

    # Mock user info returned from Google
    mock_userinfo = {"email": "user@example.com", "name": "Test User"}
    mock_userinfo_service = MagicMock()
    mock_userinfo_service.userinfo().get().execute.return_value = mock_userinfo
    mock_build.return_value = mock_userinfo_service

    # Mock DB models and behavior
    mock_user = MagicMock(id=1, email="user@example.com", name="Test User")
    mock_gmail_account = MagicMock()

    # Simulate new user creation
    mock_db.query().filter().first.side_effect = [None, None, None, None]
    mock_db.query().filter().count.return_value = 0

    # Mock commit and refresh
    mock_db.add = MagicMock()
    mock_db.commit = MagicMock()
    mock_db.refresh = MagicMock(return_value=None)

    response = client.get("/auth/callback?code=abc&state=new")
    assert response.status_code in (200, 307)  # Redirect response
    # FastAPI converts RedirectResponse to 307 Temporary Redirect in TestClient


@patch("backend.routes.auth.build")
@patch("backend.routes.auth.Flow")
def test_auth_callback_existing_user(mock_flow, mock_build, mock_db, monkeypatch):
    """Handle when user already exists in DB."""
    monkeypatch.setattr("backend.routes.auth.get_db", lambda: mock_db)

    # Mock flow
    mock_flow_instance = MagicMock()
    mock_flow_instance.fetch_token.return_value = None
    mock_flow_instance.credentials = MagicMock(to_json=lambda: '{"token": "xyz"}')
    mock_flow.from_client_config.return_value = mock_flow_instance

    # Mock Google user info
    mock_userinfo = {"email": "existing@example.com", "name": "Existing User"}
    mock_userinfo_service = MagicMock()
    mock_userinfo_service.userinfo().get().execute.return_value = mock_userinfo
    mock_build.return_value = mock_userinfo_service

    # Mock DB queries: user exists, gmail account exists
    mock_user = MagicMock(id=2, email="existing@example.com")
    mock_gmail = MagicMock(email="existing@example.com")

    mock_db.query().filter().first.side_effect = [mock_user, mock_gmail]
    mock_db.query().filter().count.return_value = 1

    response = client.get("/auth/callback?code=xyz&state=2")
    assert response.status_code in (200, 307)


@patch("backend.routes.auth.Flow")
def test_auth_callback_failure(mock_flow, mock_db, monkeypatch):
    """Simulate failure during token fetch."""
    monkeypatch.setattr("backend.routes.auth.get_db", lambda: mock_db)

    # Make flow throw exception
    mock_flow.from_client_config.side_effect = Exception("Google API failure")

    response = client.get("/auth/callback?code=bad&state=new")
    assert response.status_code == 500
    assert "detail" in response.json()
    assert "Google API failure" in response.json()["detail"]
