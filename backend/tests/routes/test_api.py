# /*
#  * -----------------------------------------------------------------------------
#  *  Copyright (c) 2025 Magda Kowalska. All rights reserved.
#  *
#  *  This software and its source code are the intellectual property of
#  *  Magda Kowalska. Unauthorized copying, reproduction, or use of this
#  *  software, in whole or in part, is strictly prohibited without express
#  *  written permission.
#  *
#  *  This software is protected under the Berne Convention for the Protection
#  *  of Literary and Artistic Works, EU copyright law, and international
#  *  copyright treaties.
#  *
#  *  Author: Magda Kowalska
#  *  Created: 2025-11-02
#  *  Last Modified: 2025-11-02
#  * -----------------------------------------------------------------------------
#  */

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app

client = TestClient(app)


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return MagicMock(spec=Session)


# -----------------------
# User Endpoints
# -----------------------


def test_get_user_found(mock_db, monkeypatch):
    mock_user = MagicMock(id=1, email="test@example.com", name="Test User")
    mock_db.query().filter().first.return_value = mock_user

    # Patch get_db dependency
    monkeypatch.setattr("backend.routes.api.get_db", lambda: mock_db)

    response = client.get("/api/user/1")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"


def test_get_user_not_found(mock_db, monkeypatch):
    mock_db.query().filter().first.return_value = None
    monkeypatch.setattr("backend.routes.api.get_db", lambda: mock_db)

    response = client.get("/api/user/999")
    assert response.status_code == 404


# -----------------------
# Gmail Accounts
# -----------------------


def test_get_gmail_accounts(mock_db, monkeypatch):
    mock_accounts = [
        MagicMock(id=1, email="a@gmail.com", is_primary=True),
        MagicMock(id=2, email="b@gmail.com", is_primary=False),
    ]
    mock_db.query().filter().all.return_value = mock_accounts
    monkeypatch.setattr("backend.routes.api.get_db", lambda: mock_db)

    response = client.get("/api/user/1/gmail-accounts")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["email"] == "a@gmail.com"


# -----------------------
# Categories
# -----------------------


def test_create_category(mock_db, monkeypatch):
    from backend.db.models import Category

    new_category = MagicMock(id=1, name="News", description="Newsletters")
    mock_db.add = MagicMock()
    mock_db.commit = MagicMock()
    mock_db.refresh = MagicMock()

    monkeypatch.setattr("backend.routes.api.get_db", lambda: mock_db)
    monkeypatch.setattr("backend.routes.api.Category", Category)

    payload = {"name": "News", "description": "Newsletters"}

    response = client.post("/api/user/1/categories", json=payload)
    assert response.status_code == 200 or response.status_code == 201


def test_get_categories(mock_db, monkeypatch):
    mock_category = MagicMock(id=1, name="Work", description="Work emails")
    mock_db.query().filter().all.return_value = [mock_category]
    mock_db.query().filter().count.return_value = 5
    monkeypatch.setattr("backend.routes.api.get_db", lambda: mock_db)

    response = client.get("/api/user/1/categories")
    assert response.status_code == 200
    data = response.json()
    assert data[0]["name"] == "Work"
    assert "email_count" in data[0]


# -----------------------
# Emails
# -----------------------


def test_get_email_found(mock_db, monkeypatch):
    mock_email = MagicMock(
        id=1,
        subject="Hello",
        sender="sender@example.com",
        body="Body text",
        summary="Summary",
        received_at=MagicMock(isoformat=lambda: "2025-01-01T00:00:00"),
    )
    mock_db.query().filter().first.return_value = mock_email
    monkeypatch.setattr("backend.routes.api.get_db", lambda: mock_db)

    response = client.get("/api/email/1")
    assert response.status_code == 200
    assert response.json()["subject"] == "Hello"


def test_get_email_not_found(mock_db, monkeypatch):
    mock_db.query().filter().first.return_value = None
    monkeypatch.setattr("backend.routes.api.get_db", lambda: mock_db)

    response = client.get("/api/email/99")
    assert response.status_code == 404


def test_delete_emails(mock_db, monkeypatch):
    mock_db.query().filter().delete.return_value = 2
    monkeypatch.setattr("backend.routes.api.get_db", lambda: mock_db)

    response = client.post("/api/emails/delete", json=[1, 2])
    assert response.status_code == 200
    assert response.json()["deleted"] == 2


# -----------------------
# Unsubscribe (Mocked)
# -----------------------


@patch("backend.routes.api.requests.Session")
@patch("backend.routes.api.get_gmail_service")
@patch("backend.routes.api.extract_email_html")
@patch("backend.routes.api.find_unsubscribe_link")
def test_unsubscribe_emails(
    mock_find, mock_extract, mock_service, mock_requests, mock_db, monkeypatch
):
    mock_email = MagicMock(
        id=1,
        gmail_message_id="abc123",
        body="",
        gmail_account=MagicMock(credentials="fake-creds"),
    )
    mock_db.query().filter().first.return_value = mock_email
    monkeypatch.setattr("backend.routes.api.get_db", lambda: mock_db)

    mock_service.return_value.users.return_value.messages.return_value.get.return_value.execute.return_value = {
        "payload": {"headers": []}
    }
    mock_extract.return_value = "<html><body>Unsubscribe here</body></html>"
    mock_find.return_value = "https://unsubscribe.example.com"

    mock_session = MagicMock()
    mock_session.get.return_value.status_code = 200
    mock_session.get.return_value.text = "unsubscribed"
    mock_requests.return_value = mock_session

    response = client.post("/api/emails/unsubscribe", json=[1])
    assert response.status_code == 200
    results = response.json()["results"]
    assert results[0]["success"]
