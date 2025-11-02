import base64
import pytest
from unittest.mock import patch, MagicMock

from backend.utils import gmail_utils


# --------------------------------------------------------
# get_gmail_service
# --------------------------------------------------------
@patch("backend.utils.gmail_utils.build")
@patch("backend.utils.gmail_utils.Credentials")
def test_get_gmail_service(mock_creds, mock_build):
    mock_creds.from_authorized_user_info.return_value = "mocked_credentials"
    mock_build.return_value = "mocked_service"

    creds_json = '{"token": "fake-token"}'
    service = gmail_utils.get_gmail_service(creds_json)

    mock_creds.from_authorized_user_info.assert_called_once()
    mock_build.assert_called_once_with("gmail", "v1", credentials="mocked_credentials")
    assert service == "mocked_service"


# --------------------------------------------------------
# extract_email_content
# --------------------------------------------------------
def test_extract_email_content_with_plain_text():
    data = base64.urlsafe_b64encode(b"Hello world").decode("utf-8")
    message = {
        "payload": {
            "headers": [{"name": "Subject", "value": "Test Subject"}],
            "parts": [{"mimeType": "text/plain", "body": {"data": data}}],
        }
    }

    content = gmail_utils.extract_email_content(message)
    assert "Test Subject" in content
    assert "Hello world" in content


def test_extract_email_content_no_payload():
    assert gmail_utils.extract_email_content({}) == ""


def test_extract_email_content_no_parts_but_body():
    data = base64.urlsafe_b64encode(b"Body text").decode("utf-8")
    message = {
        "payload": {"headers": [], "body": {"data": data}},
    }
    result = gmail_utils.extract_email_content(message)
    assert "Body text" in result


# --------------------------------------------------------
# find_unsubscribe_link
# --------------------------------------------------------
def test_find_unsubscribe_link_from_header():
    headers = [
        {"name": "List-Unsubscribe", "value": "<https://example.com/unsubscribe>"}
    ]
    body = "<html><body></body></html>"

    result = gmail_utils.find_unsubscribe_link(body, headers)
    assert result == "https://example.com/unsubscribe"


def test_find_unsubscribe_link_from_text_link():
    html = """
        <html><body>
        <a href="https://example.com/track123">Click here to unsubscribe</a>
        </body></html>
    """
    headers = []
    result = gmail_utils.find_unsubscribe_link(html, headers)
    assert result.startswith("https://example.com")


def test_find_unsubscribe_link_from_href_keyword():
    html = """
        <html><body>
        <a href="https://example.com/unsubscribe-now">Manage</a>
        </body></html>
    """
    headers = []
    result = gmail_utils.find_unsubscribe_link(html, headers)
    assert "unsubscribe" in result


def test_find_unsubscribe_link_in_parent_element():
    html = """
        <html><body>
        <div>To unsubscribe <a href="https://example.com/out">click here</a></div>
        </body></html>
    """
    headers = []
    result = gmail_utils.find_unsubscribe_link(html, headers)
    assert result.startswith("https://example.com")


def test_find_unsubscribe_link_fallback_last_link():
    html = """
        <html><body>
        <a href="https://social.twitter.com/x">Twitter</a>
        <a href="https://example.com/unsub-final">Unsubscribe</a>
        </body></html>
    """
    headers = []
    result = gmail_utils.find_unsubscribe_link(html, headers)
    assert result.endswith("unsub-final")


def test_find_unsubscribe_href_link():
    html = "<html><body><a href='https://example.com/nope'>No unsubscribe here</a></body></html>"
    headers = []
    result = gmail_utils.find_unsubscribe_link(html, headers)
    assert result == "https://example.com/nope"


# --------------------------------------------------------
# extract_email_html
# --------------------------------------------------------
def test_extract_email_html_with_html_part():
    html_data = base64.urlsafe_b64encode(b"<html><p>Hi</p></html>").decode("utf-8")
    message = {
        "payload": {
            "parts": [{"mimeType": "text/html", "body": {"data": html_data}}],
        }
    }
    result = gmail_utils.extract_email_html(message)
    assert "<p>Hi</p>" in result


def test_extract_email_html_nested_parts():
    html_data = base64.urlsafe_b64encode(b"<html>Nested</html>").decode("utf-8")
    message = {
        "payload": {
            "parts": [
                {
                    "parts": [{"mimeType": "text/html", "body": {"data": html_data}}],
                }
            ],
        }
    }
    result = gmail_utils.extract_email_html(message)
    assert "Nested" in result


def test_extract_email_html_no_parts_direct_body():
    html_data = base64.urlsafe_b64encode(b"<html><b>Direct</b></html>").decode("utf-8")
    message = {"payload": {"body": {"data": html_data}}}
    result = gmail_utils.extract_email_html(message)
    assert "<b>Direct</b>" in result


def test_extract_email_html_no_payload():
    result = gmail_utils.extract_email_html({})
    assert result == ""
