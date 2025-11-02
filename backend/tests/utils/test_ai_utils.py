import pytest
from unittest.mock import patch, MagicMock

import builtins

from backend.utils import ai_utils as ai


# -------------------------------
# Fixtures
# -------------------------------
@pytest.fixture
def sample_categories():
    class Cat:
        def __init__(self, id, name, desc):
            self.id = id
            self.name = name
            self.description = desc

    return [
        Cat(1, "Promotions", "discount sale offer buy now"),
        Cat(2, "Work", "project meeting client task report"),
        Cat(3, "Social", "friend event party invitation"),
    ]


# -------------------------------
# categorize_email_keywords
# -------------------------------
def test_categorize_email_keywords_basic(sample_categories):
    email = "Huge discount offer! Buy now and save big."
    result = ai.categorize_email_keywords(email, sample_categories)
    assert result == 1  # Promotions should match


def test_categorize_email_keywords_no_match(sample_categories):
    email = "Just random text without context"
    result = ai.categorize_email_keywords(email, sample_categories)
    assert result is None


def test_categorize_email_keywords_ties(sample_categories):
    email = "Project client discount sale offer"
    result = ai.categorize_email_keywords(email, sample_categories)
    assert result in [1, 2]  # could be promotions or work depending on scores


# -------------------------------
# categorize_email (Anthropic disabled)
# -------------------------------
@patch.object(ai, "anthropic_client", None)
def test_categorize_email_without_anthropic(sample_categories):
    email = "Let's discuss project report in meeting"
    result = ai.categorize_email(email, sample_categories)
    assert result == 2  # "Work" category by keywords


# -------------------------------
# categorize_email (Anthropic enabled)
# -------------------------------
@patch.object(ai, "anthropic_client")
def test_categorize_email_with_anthropic(mock_client, sample_categories):
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text="Work")]
    mock_client.messages.create.return_value = mock_msg

    email = "We have a meeting with the client tomorrow."
    result = ai.categorize_email(email, sample_categories)

    mock_client.messages.create.assert_called_once()
    assert result == 2  # Work category


@patch.object(ai, "anthropic_client")
def test_categorize_email_with_anthropic_none(mock_client, sample_categories):
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text="NONE")]
    mock_client.messages.create.return_value = mock_msg

    result = ai.categorize_email("Unrelated spam text", sample_categories)
    assert result is None


@patch.object(ai, "anthropic_client")
@patch("builtins.print")
def test_categorize_email_anthropic_exception(
    mock_print, mock_client, sample_categories
):
    mock_client.messages.create.side_effect = Exception("Network fail")
    email = "Buy now offer!"
    result = ai.categorize_email(email, sample_categories)
    assert result is None
    mock_print.assert_called()


# -------------------------------
# summarize_email_basic
# -------------------------------
def test_summarize_email_basic_with_subject():
    email = "Subject: Meeting Tomorrow\nWe will discuss next steps in the project."
    result = ai.summarize_email_basic(email)
    assert "Meeting Tomorrow" in result
    assert "project" in result


def test_summarize_email_basic_no_subject():
    email = "This is a test email body only"
    result = ai.summarize_email_basic(email)
    assert "This is a test" in result


def test_summarize_email_basic_empty():
    assert ai.summarize_email_basic("") == "Email received"


# -------------------------------
# summarize_email (Anthropic disabled)
# -------------------------------
@patch.object(ai, "anthropic_client", None)
def test_summarize_email_without_anthropic():
    email = "Subject: Hello\nJust wanted to say hi."
    result = ai.summarize_email(email)
    assert "Hello" in result


# -------------------------------
# summarize_email (Anthropic enabled)
# -------------------------------
@patch.object(ai, "anthropic_client")
def test_summarize_email_with_anthropic(mock_client):
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text="This is a short summary.")]
    mock_client.messages.create.return_value = mock_msg

    result = ai.summarize_email("Long email content...")
    mock_client.messages.create.assert_called_once()
    assert "short summary" in result


@patch.object(ai, "anthropic_client")
@patch("builtins.print")
def test_summarize_email_anthropic_exception(mock_print, mock_client):
    mock_client.messages.create.side_effect = Exception("API error")

    result = ai.summarize_email("Subject: Hello\nBody content here.")
    assert "Hello" in result  # falls back to summarize_email_basic
    mock_print.assert_called()
