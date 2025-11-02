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

from datetime import datetime
from unittest.mock import MagicMock, Mock, call, patch

import pytest
from sqlalchemy.orm import Session

from backend.db.models import Category, Email, GmailAccount
from backend.email_processing import (
    get_or_create_uncategorized_category,
    process_new_emails,
)


class MockGmailService:
    """Mock Gmail API service that handles chained method calls"""

    def __init__(self):
        self.list_response = {"messages": []}
        self.get_response = {}
        self.modify_response = {}
        self.list_called_with = []
        self.get_called_with = []
        self.modify_called_with = []

    def users(self):
        return self

    def messages(self):
        return self

    def list(self, **kwargs):
        self.list_called_with.append(kwargs)
        mock_request = MagicMock()
        mock_request.execute.return_value = self.list_response
        return mock_request

    def get(self, **kwargs):
        self.get_called_with.append(kwargs)
        mock_request = MagicMock()
        mock_request.execute.return_value = self.get_response
        return mock_request

    def modify(self, **kwargs):
        self.modify_called_with.append(kwargs)
        mock_request = MagicMock()
        mock_request.execute.return_value = self.modify_response
        return mock_request


@pytest.fixture
def mock_db_session():
    """Create a mock database session"""
    session = MagicMock(spec=Session)
    return session


@pytest.fixture
def mock_category():
    """Create a mock Category object"""
    category = MagicMock(spec=Category)
    category.id = 1
    category.user_id = 100
    category.name = "Uncategorized"
    category.description = "Emails that don't match any specific category"
    return category


@pytest.fixture
def mock_gmail_account():
    """Create a mock GmailAccount object"""
    account = MagicMock(spec=GmailAccount)
    account.id = 1
    account.user_id = 100
    account.email = "test@example.com"
    account.credentials = {"token": "test_token"}
    return account


@pytest.fixture
def mock_email():
    """Create a mock Email object"""
    email = MagicMock(spec=Email)
    email.id = 1
    email.gmail_account_id = 1
    email.category_id = 1
    email.gmail_message_id = "msg123"
    email.subject = "Test Subject"
    email.sender = "sender@example.com"
    email.body = "Test body"
    email.summary = "Test summary"
    email.received_at = datetime.utcnow()
    return email


@pytest.fixture
def mock_gmail_message():
    """Create a mock Gmail message"""
    return {
        "id": "msg123",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Test Email Subject"},
                {"name": "From", "value": "sender@example.com"},
            ]
        },
    }


class TestGetOrCreateUncategorizedCategory:
    """Tests for get_or_create_uncategorized_category function"""

    def test_returns_existing_category(self, mock_db_session, mock_category):
        """Test that existing Uncategorized category is returned"""
        # Arrange
        user_id = 100
        mock_query = mock_db_session.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = mock_category

        # Act
        result = get_or_create_uncategorized_category(user_id, mock_db_session)

        # Assert
        assert result == mock_category.id
        mock_db_session.query.assert_called_once_with(Category)
        mock_db_session.add.assert_not_called()
        mock_db_session.commit.assert_not_called()

    def test_creates_new_category_when_not_exists(self, mock_db_session):
        """Test that new Uncategorized category is created when it doesn't exist"""
        # Arrange
        user_id = 100
        mock_query = mock_db_session.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = None

        new_category = MagicMock(spec=Category)
        new_category.id = 2

        def set_category_id(category):
            category.id = 2

        mock_db_session.refresh.side_effect = set_category_id

        # Act
        with patch("backend.email_processing.Category") as mock_category_class:
            mock_category_class.return_value = new_category
            result = get_or_create_uncategorized_category(user_id, mock_db_session)

        # Assert
        assert result == 2
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    def test_creates_category_with_correct_attributes(self, mock_db_session):
        """Test that created category has correct attributes"""
        # Arrange
        user_id = 100
        mock_query = mock_db_session.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = None

        # Act
        with patch("backend.email_processing.Category") as mock_category_class:
            get_or_create_uncategorized_category(user_id, mock_db_session)

            # Assert
            mock_category_class.assert_called_once_with(
                user_id=user_id,
                name="Uncategorized",
                description="Emails that don't match any specific category",
            )


class TestProcessNewEmails:
    """Tests for process_new_emails function"""

    @patch("backend.email_processing.get_gmail_service")
    @patch("backend.email_processing.extract_email_content")
    @patch("backend.email_processing.categorize_email")
    @patch("backend.email_processing.summarize_email")
    @patch("backend.email_processing.get_or_create_uncategorized_category")
    def test_process_no_gmail_accounts(
        self,
        mock_get_uncategorized,
        mock_summarize,
        mock_categorize,
        mock_extract,
        mock_get_service,
        mock_db_session,
    ):
        """Test processing when no Gmail accounts exist"""
        # Arrange
        mock_query = mock_db_session.query.return_value
        mock_query.all.return_value = []

        # Act
        process_new_emails(mock_db_session)

        # Assert
        mock_get_service.assert_not_called()
        mock_db_session.commit.assert_not_called()

    @patch("backend.email_processing.get_gmail_service")
    @patch("backend.email_processing.extract_email_content")
    @patch("backend.email_processing.categorize_email")
    @patch("backend.email_processing.summarize_email")
    def test_process_account_with_no_messages(
        self,
        mock_summarize,
        mock_categorize,
        mock_extract,
        mock_get_service,
        mock_db_session,
        mock_gmail_account,
    ):
        """Test processing account with no unread messages"""
        # Arrange
        mock_service = MagicMock()
        mock_users = MagicMock()
        mock_messages = MagicMock()

        mock_service.users.return_value = mock_users
        mock_users.messages.return_value = mock_messages

        mock_list = MagicMock()
        mock_list.execute.return_value = {"messages": []}
        mock_messages.list.return_value = mock_list

        mock_get_service.return_value = mock_service

        mock_query = mock_db_session.query.return_value
        mock_query.all.return_value = [mock_gmail_account]

        # Act
        process_new_emails(mock_db_session)

        # Assert
        mock_get_service.assert_called_once_with(mock_gmail_account.credentials)
        mock_extract.assert_not_called()
        mock_db_session.commit.assert_called_once()

    @patch("backend.email_processing.get_gmail_service")
    @patch("backend.email_processing.extract_email_content")
    @patch("backend.email_processing.categorize_email")
    @patch("backend.email_processing.summarize_email")
    @patch("backend.email_processing.get_or_create_uncategorized_category")
    def test_process_skips_existing_emails(
        self,
        mock_get_uncategorized,
        mock_summarize,
        mock_categorize,
        mock_extract,
        mock_get_service,
        mock_db_session,
        mock_gmail_account,
        mock_email,
    ):
        """Test that already processed emails are skipped"""
        # Arrange
        mock_service = MagicMock()
        mock_users = MagicMock()
        mock_messages = MagicMock()

        mock_service.users.return_value = mock_users
        mock_users.messages.return_value = mock_messages

        mock_list = MagicMock()
        mock_list.execute.return_value = {"messages": [{"id": "msg123"}]}
        mock_messages.list.return_value = mock_list

        mock_get_service.return_value = mock_service

        def query_side_effect(model):
            mock_query = MagicMock()
            if model == GmailAccount:
                mock_query.all.return_value = [mock_gmail_account]
            elif model == Email:
                mock_filter = mock_query.filter.return_value
                mock_filter.first.return_value = mock_email
            return mock_query

        mock_db_session.query.side_effect = query_side_effect

        # Act
        process_new_emails(mock_db_session)

        # Assert
        mock_extract.assert_not_called()
        mock_categorize.assert_not_called()

    @patch("backend.email_processing.get_gmail_service")
    @patch("backend.email_processing.extract_email_content")
    @patch("backend.email_processing.categorize_email")
    @patch("backend.email_processing.summarize_email")
    @patch("backend.email_processing.get_or_create_uncategorized_category")
    def test_process_new_email_with_categories(
        self,
        mock_get_uncategorized,
        mock_summarize,
        mock_categorize,
        mock_extract,
        mock_get_service,
        mock_db_session,
        mock_gmail_account,
        mock_category,
        mock_gmail_message,
    ):
        """Test processing a new email with existing categories"""
        # Arrange
        mock_gmail_service = MockGmailService()
        mock_gmail_service.list_response = {"messages": [{"id": "msg123"}]}
        mock_gmail_service.get_response = mock_gmail_message
        mock_get_service.return_value = mock_gmail_service

        mock_extract.return_value = "Email body content"
        mock_categorize.return_value = 5
        mock_summarize.return_value = "Email summary"

        def query_side_effect(model):
            mock_query = MagicMock()
            if model == GmailAccount:
                mock_query.all.return_value = [mock_gmail_account]
            elif model == Email:
                mock_filter = mock_query.filter.return_value
                mock_filter.first.return_value = None
            elif model == Category:
                mock_filter = mock_query.filter.return_value
                mock_category.id = 5
                mock_filter.all.return_value = [mock_category]
            return mock_query

        mock_db_session.query.side_effect = query_side_effect

        # Act
        with patch("backend.email_processing.Email") as mock_email_class:
            process_new_emails(mock_db_session)

        # Assert
        mock_extract.assert_called_once_with(mock_gmail_message)
        mock_categorize.assert_called_once_with("Email body content", [mock_category])
        mock_summarize.assert_called_once_with("Email body content")
        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called_once()

        # Verify email was archived
        assert len(mock_gmail_service.modify_called_with) == 1
        assert mock_gmail_service.modify_called_with[0] == {
            "userId": "me",
            "id": "msg123",
            "body": {"removeLabelIds": ["UNREAD", "INBOX"]},
        }

    @patch("backend.email_processing.get_gmail_service")
    @patch("backend.email_processing.extract_email_content")
    @patch("backend.email_processing.categorize_email")
    @patch("backend.email_processing.summarize_email")
    @patch("backend.email_processing.get_or_create_uncategorized_category")
    def test_process_email_no_category_match(
        self,
        mock_get_uncategorized,
        mock_summarize,
        mock_categorize,
        mock_extract,
        mock_get_service,
        mock_db_session,
        mock_gmail_account,
        mock_category,
        mock_gmail_message,
    ):
        """Test processing email when no category matches"""
        # Arrange
        mock_service = MagicMock()
        mock_users = MagicMock()
        mock_messages = MagicMock()

        mock_service.users.return_value = mock_users
        mock_users.messages.return_value = mock_messages

        mock_list = MagicMock()
        mock_list.execute.return_value = {"messages": [{"id": "msg123"}]}
        mock_messages.list.return_value = mock_list

        mock_get = MagicMock()
        mock_get.execute.return_value = mock_gmail_message
        mock_messages.get.return_value = mock_get

        mock_modify = MagicMock()
        mock_modify.execute.return_value = {}
        mock_messages.modify.return_value = mock_modify

        mock_get_service.return_value = mock_service

        mock_extract.return_value = "Email body content"
        mock_categorize.return_value = None  # No category match
        mock_summarize.return_value = "Email summary"
        mock_get_uncategorized.return_value = 99

        def query_side_effect(model):
            mock_query = MagicMock()
            if model == GmailAccount:
                mock_query.all.return_value = [mock_gmail_account]
            elif model == Email:
                mock_filter = mock_query.filter.return_value
                mock_filter.first.return_value = None
            elif model == Category:
                mock_filter = mock_query.filter.return_value
                mock_filter.all.return_value = [mock_category]
            return mock_query

        mock_db_session.query.side_effect = query_side_effect

        # Act
        with patch("backend.email_processing.Email") as mock_email_class:
            process_new_emails(mock_db_session)

        # Assert
        mock_get_uncategorized.assert_called_once_with(
            mock_gmail_account.user_id, mock_db_session
        )

    @patch("backend.email_processing.get_gmail_service")
    @patch("backend.email_processing.extract_email_content")
    @patch("backend.email_processing.categorize_email")
    @patch("backend.email_processing.summarize_email")
    @patch("backend.email_processing.get_or_create_uncategorized_category")
    def test_process_email_no_categories_exist(
        self,
        mock_get_uncategorized,
        mock_summarize,
        mock_categorize,
        mock_extract,
        mock_get_service,
        mock_db_session,
        mock_gmail_account,
        mock_gmail_message,
    ):
        """Test processing email when no categories exist"""
        # Arrange
        mock_service = MagicMock()
        mock_users = MagicMock()
        mock_messages = MagicMock()

        mock_service.users.return_value = mock_users
        mock_users.messages.return_value = mock_messages

        mock_list = MagicMock()
        mock_list.execute.return_value = {"messages": [{"id": "msg123"}]}
        mock_messages.list.return_value = mock_list

        mock_get = MagicMock()
        mock_get.execute.return_value = mock_gmail_message
        mock_messages.get.return_value = mock_get

        mock_modify = MagicMock()
        mock_modify.execute.return_value = {}
        mock_messages.modify.return_value = mock_modify

        mock_get_service.return_value = mock_service

        mock_extract.return_value = "Email body content"
        mock_summarize.return_value = "Email summary"
        mock_get_uncategorized.return_value = 99

        def query_side_effect(model):
            mock_query = MagicMock()
            if model == GmailAccount:
                mock_query.all.return_value = [mock_gmail_account]
            elif model == Email:
                mock_filter = mock_query.filter.return_value
                mock_filter.first.return_value = None
            elif model == Category:
                mock_filter = mock_query.filter.return_value
                mock_filter.all.return_value = []  # No categories
            return mock_query

        mock_db_session.query.side_effect = query_side_effect

        # Act
        with patch("backend.email_processing.Email") as mock_email_class:
            process_new_emails(mock_db_session)

        # Assert
        mock_categorize.assert_not_called()
        mock_get_uncategorized.assert_called_once_with(
            mock_gmail_account.user_id, mock_db_session
        )

    @patch("backend.email_processing.get_gmail_service")
    @patch("backend.email_processing.extract_email_content")
    def test_process_emails_handles_exceptions(
        self,
        mock_extract,
        mock_get_service,
        mock_db_session,
        mock_gmail_account,
    ):
        """Test that exceptions are handled and database is rolled back"""
        # Arrange
        mock_get_service.side_effect = Exception("Gmail API Error")

        mock_query = mock_db_session.query.return_value
        mock_query.all.return_value = [mock_gmail_account]

        # Act
        process_new_emails(mock_db_session)

        # Assert
        mock_db_session.rollback.assert_called_once()

    @patch("backend.email_processing.get_gmail_service")
    @patch("backend.email_processing.extract_email_content")
    @patch("backend.email_processing.categorize_email")
    @patch("backend.email_processing.summarize_email")
    def test_process_multiple_emails(
        self,
        mock_summarize,
        mock_categorize,
        mock_extract,
        mock_get_service,
        mock_db_session,
        mock_gmail_account,
        mock_gmail_message,
    ):
        """Test processing multiple emails in one run"""
        # Arrange
        mock_service = MagicMock()
        mock_users = MagicMock()
        mock_messages = MagicMock()

        mock_service.users.return_value = mock_users
        mock_users.messages.return_value = mock_messages

        mock_list = MagicMock()
        mock_list.execute.return_value = {
            "messages": [{"id": "msg1"}, {"id": "msg2"}, {"id": "msg3"}]
        }
        mock_messages.list.return_value = mock_list

        mock_get = MagicMock()
        mock_get.execute.return_value = mock_gmail_message
        mock_messages.get.return_value = mock_get

        mock_modify = MagicMock()
        mock_modify.execute.return_value = {}
        mock_messages.modify.return_value = mock_modify

        mock_get_service.return_value = mock_service

        mock_extract.return_value = "Email body content"
        mock_categorize.return_value = 1
        mock_summarize.return_value = "Email summary"

        def query_side_effect(model):
            mock_query = MagicMock()
            if model == GmailAccount:
                mock_query.all.return_value = [mock_gmail_account]
            elif model == Email:
                mock_filter = mock_query.filter.return_value
                mock_filter.first.return_value = None
            elif model == Category:
                mock_filter = mock_query.filter.return_value
                mock_category = MagicMock()
                mock_category.id = 1
                mock_filter.all.return_value = [mock_category]
            return mock_query

        mock_db_session.query.side_effect = query_side_effect

        # Act
        with patch("backend.email_processing.Email"):
            process_new_emails(mock_db_session)

        # Assert
        assert mock_extract.call_count == 3
        assert mock_categorize.call_count == 3
        assert mock_summarize.call_count == 3
        assert mock_messages.modify.call_count == 3

    @patch("backend.email_processing.get_gmail_service")
    @patch("backend.email_processing.extract_email_content")
    @patch("backend.email_processing.categorize_email")
    @patch("backend.email_processing.summarize_email")
    def test_email_archived_in_gmail(
        self,
        mock_summarize,
        mock_categorize,
        mock_extract,
        mock_get_service,
        mock_db_session,
        mock_gmail_account,
        mock_gmail_message,
    ):
        """Test that emails are properly archived in Gmail"""
        # Arrange
        mock_service = MagicMock()
        mock_users = MagicMock()
        mock_messages = MagicMock()

        mock_service.users.return_value = mock_users
        mock_users.messages.return_value = mock_messages

        mock_list = MagicMock()
        mock_list.execute.return_value = {"messages": [{"id": "msg123"}]}
        mock_messages.list.return_value = mock_list

        mock_get = MagicMock()
        mock_get.execute.return_value = mock_gmail_message
        mock_messages.get.return_value = mock_get

        mock_modify = MagicMock()
        mock_modify.execute.return_value = {}
        mock_messages.modify.return_value = mock_modify

        mock_get_service.return_value = mock_service

        mock_extract.return_value = "Email body content"
        mock_categorize.return_value = 1
        mock_summarize.return_value = "Email summary"

        def query_side_effect(model):
            mock_query = MagicMock()
            if model == GmailAccount:
                mock_query.all.return_value = [mock_gmail_account]
            elif model == Email:
                mock_filter = mock_query.filter.return_value
                mock_filter.first.return_value = None
            elif model == Category:
                mock_filter = mock_query.filter.return_value
                mock_category = MagicMock()
                mock_category.id = 1
                mock_filter.all.return_value = [mock_category]
            return mock_query

        mock_db_session.query.side_effect = query_side_effect

        # Act
        with patch("backend.email_processing.Email"):
            process_new_emails(mock_db_session)

        # Assert
        mock_messages.modify.assert_called_once_with(
            userId="me",
            id="msg123",
            body={"removeLabelIds": ["UNREAD", "INBOX"]},
        )

    @patch("backend.email_processing.get_gmail_service")
    def test_process_multiple_gmail_accounts(
        self,
        mock_get_service,
        mock_db_session,
    ):
        """Test processing multiple Gmail accounts"""
        # Arrange
        account1 = MagicMock(spec=GmailAccount)
        account1.email = "test1@example.com"
        account1.credentials = {"token": "token1"}

        account2 = MagicMock(spec=GmailAccount)
        account2.email = "test2@example.com"
        account2.credentials = {"token": "token2"}

        mock_service = MagicMock()
        mock_users = MagicMock()
        mock_messages = MagicMock()

        mock_service.users.return_value = mock_users
        mock_users.messages.return_value = mock_messages

        mock_list = MagicMock()
        mock_list.execute.return_value = {"messages": []}
        mock_messages.list.return_value = mock_list

        mock_get_service.return_value = mock_service

        mock_query = mock_db_session.query.return_value
        mock_query.all.return_value = [account1, account2]

        # Act
        process_new_emails(mock_db_session)

        # Assert
        assert mock_get_service.call_count == 2
        mock_get_service.assert_any_call(account1.credentials)
        mock_get_service.assert_any_call(account2.credentials)
