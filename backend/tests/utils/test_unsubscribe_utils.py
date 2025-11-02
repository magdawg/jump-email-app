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

import pytest
from unittest.mock import Mock, patch, MagicMock
from requests.exceptions import RequestException, HTTPError, Timeout
from backend.utils.unsubscribe_utils import (
    create_session,
    visit_page,
    parse_unsubscribe_forms,
    submit_form,
    click_links,
    parse_list_unsubscribe,
)


class TestCreateSession:
    """Tests for create_session function"""

    def test_creates_session_with_user_agent(self):
        """Should create a session with proper User-Agent header"""
        session = create_session()
        assert "User-Agent" in session.headers
        assert "Mozilla/5.0" in session.headers["User-Agent"]

    def test_configures_retry_logic(self):
        """Should configure retry logic for both http and https"""
        session = create_session()
        assert "http://" in session.adapters
        assert "https://" in session.adapters

    def test_returns_requests_session(self):
        """Should return a requests.Session object"""
        import requests

        session = create_session()
        assert isinstance(session, requests.Session)


class TestVisitPage:
    """Tests for visit_page function"""

    @patch("backend.utils.unsubscribe_utils.requests.Session")
    def test_successful_page_visit(self, mock_session_class):
        """Should return page text and final URL on success"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.text = "<html>Test content</html>"
        mock_response.url = "https://example.com/final"
        mock_session.get.return_value = mock_response

        text, url = visit_page(mock_session, "https://example.com")

        assert text == "<html>Test content</html>"
        assert url == "https://example.com/final"
        mock_session.get.assert_called_once_with("https://example.com", timeout=15)

    @patch("backend.utils.unsubscribe_utils.requests.Session")
    def test_custom_timeout(self, mock_session_class):
        """Should use custom timeout when provided"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.text = "content"
        mock_response.url = "https://example.com"
        mock_session.get.return_value = mock_response

        visit_page(mock_session, "https://example.com", timeout=30)

        mock_session.get.assert_called_once_with("https://example.com", timeout=30)

    @patch("backend.utils.unsubscribe_utils.requests.Session")
    def test_handles_request_exception(self, mock_session_class):
        """Should return None for text and original URL on exception"""
        mock_session = Mock()
        mock_session.get.side_effect = RequestException("Connection error")

        text, url = visit_page(mock_session, "https://example.com")

        assert text is None
        assert url == "https://example.com"

    @patch("backend.utils.unsubscribe_utils.requests.Session")
    def test_handles_timeout(self, mock_session_class):
        """Should handle timeout exceptions gracefully"""
        mock_session = Mock()
        mock_session.get.side_effect = Timeout("Request timed out")

        text, url = visit_page(mock_session, "https://example.com")

        assert text is None
        assert url == "https://example.com"

    @patch("backend.utils.unsubscribe_utils.requests.Session")
    def test_handles_http_error(self, mock_session_class):
        """Should handle HTTP errors (4xx, 5xx) gracefully"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = HTTPError("404 Not Found")
        mock_session.get.return_value = mock_response

        text, url = visit_page(mock_session, "https://example.com")

        assert text is None
        assert url == "https://example.com"


class TestParseUnsubscribeForms:
    """Tests for parse_unsubscribe_forms function"""

    def test_finds_unsubscribe_form_with_post_method(self):
        """Should find form with 'unsubscribe' text and POST method"""
        html = """
        <html>
            <form action="/unsubscribe" method="post">
                <p>Click to unsubscribe</p>
                <input type="hidden" name="token" value="abc123">
                <input type="email" name="email" value="test@example.com">
                <button type="submit">Unsubscribe</button>
            </form>
        </html>
        """
        base_url = "https://example.com"

        forms = parse_unsubscribe_forms(html, base_url)

        assert len(forms) == 1
        assert forms[0]["url"] == "https://example.com/unsubscribe"
        assert forms[0]["method"] == "post"
        assert forms[0]["data"]["token"] == "abc123"
        assert forms[0]["data"]["email"] == "test@example.com"

    def test_finds_opt_out_form(self):
        """Should find form with 'opt out' text"""
        html = """
        <form action="/preferences">
            <p>Opt out of emails</p>
            <input type="hidden" name="action" value="optout">
        </form>
        """
        base_url = "https://example.com"

        forms = parse_unsubscribe_forms(html, base_url)

        assert len(forms) == 1
        assert (
            "opt" in forms[0]["url"].lower() or forms[0]["data"]["action"] == "optout"
        )

    def test_finds_remove_form(self):
        """Should find form with 'remove' text"""
        html = """
        <form action="/remove-subscription" method="get">
            <p>Remove me from this list</p>
            <input name="user_id" value="12345">
        </form>
        """
        base_url = "https://example.com"

        forms = parse_unsubscribe_forms(html, base_url)

        assert len(forms) == 1
        assert forms[0]["method"] == "get"
        assert forms[0]["data"]["user_id"] == "12345"

    def test_handles_relative_action_url(self):
        """Should convert relative action URLs to absolute"""
        html = """
        <form action="unsubscribe.php">
            <p>Unsubscribe here</p>
        </form>
        """
        base_url = "https://example.com/email/"

        forms = parse_unsubscribe_forms(html, base_url)

        assert forms[0]["url"] == "https://example.com/email/unsubscribe.php"

    def test_handles_empty_action(self):
        """Should use base_url when action is empty"""
        html = """
        <form action="" method="post">
            <p>Unsubscribe</p>
            <input name="unsub" value="1">
        </form>
        """
        base_url = "https://example.com/unsub"

        forms = parse_unsubscribe_forms(html, base_url)

        assert forms[0]["url"] == "https://example.com/unsub"

    def test_handles_checkboxes_only_checked(self):
        """Should only include checked checkboxes in form data"""
        html = """
        <form action="/unsubscribe">
            <p>Unsubscribe options</p>
            <input type="checkbox" name="marketing" value="1" checked>
            <input type="checkbox" name="newsletter" value="1">
            <input type="checkbox" name="alerts" value="1" checked>
        </form>
        """
        base_url = "https://example.com"

        forms = parse_unsubscribe_forms(html, base_url)

        assert forms[0]["data"]["marketing"] == "1"
        assert forms[0]["data"]["alerts"] == "1"
        assert "newsletter" not in forms[0]["data"]

    def test_handles_radio_buttons(self):
        """Should only include checked radio buttons"""
        html = """
        <form action="/unsubscribe">
            <p>Unsubscribe preference</p>
            <input type="radio" name="preference" value="all">
            <input type="radio" name="preference" value="some" checked>
        </form>
        """
        base_url = "https://example.com"

        forms = parse_unsubscribe_forms(html, base_url)

        assert forms[0]["data"]["preference"] == "some"

    def test_ignores_inputs_without_name(self):
        """Should ignore input fields without name attribute"""
        html = """
        <form action="/unsubscribe">
            <p>Unsubscribe</p>
            <input type="text" value="test">
            <input type="hidden" name="token" value="abc">
        </form>
        """
        base_url = "https://example.com"

        forms = parse_unsubscribe_forms(html, base_url)

        assert len(forms[0]["data"]) == 1
        assert forms[0]["data"]["token"] == "abc"

    def test_returns_empty_list_for_no_unsubscribe_forms(self):
        """Should return empty list when no unsubscribe forms found"""
        html = """
        <html>
            <form action="/login">
                <input name="username">
                <input name="password">
            </form>
        </html>
        """
        base_url = "https://example.com"

        forms = parse_unsubscribe_forms(html, base_url)

        assert forms == []

    def test_handles_multiple_unsubscribe_forms(self):
        """Should find multiple unsubscribe forms"""
        html = """
        <html>
            <form action="/unsub1"><p>Unsubscribe from emails</p></form>
            <form action="/unsub2"><p>Opt out of notifications</p></form>
        </html>
        """
        base_url = "https://example.com"

        forms = parse_unsubscribe_forms(html, base_url)

        assert len(forms) == 2


class TestSubmitForm:
    """Tests for submit_form function"""

    @patch("backend.utils.unsubscribe_utils.requests.Session")
    def test_submits_post_form_successfully(self, mock_session_class):
        """Should submit POST form and return True on success"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.text = "You have been unsubscribed successfully"
        mock_session.post.return_value = mock_response

        form = {
            "url": "https://example.com/unsubscribe",
            "method": "post",
            "data": {"email": "test@example.com", "token": "abc123"},
        }

        result = submit_form(mock_session, form)

        assert result is True
        mock_session.post.assert_called_once_with(
            "https://example.com/unsubscribe",
            data={"email": "test@example.com", "token": "abc123"},
            timeout=15,
        )

    @patch("backend.utils.unsubscribe_utils.requests.Session")
    def test_submits_get_form_successfully(self, mock_session_class):
        """Should submit GET form and return True on success"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.text = "Email removed from list"
        mock_session.get.return_value = mock_response

        form = {
            "url": "https://example.com/unsubscribe",
            "method": "get",
            "data": {"user_id": "12345"},
        }

        result = submit_form(mock_session, form)

        assert result is True
        mock_session.get.assert_called_once_with(
            "https://example.com/unsubscribe", params={"user_id": "12345"}, timeout=15
        )

    @patch("backend.utils.unsubscribe_utils.requests.Session")
    def test_detects_success_with_confirmed_keyword(self, mock_session_class):
        """Should detect success with 'confirmed' keyword"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.text = "Your request has been confirmed"
        mock_session.post.return_value = mock_response

        form = {"url": "https://example.com/unsub", "method": "post", "data": {}}

        result = submit_form(mock_session, form)

        assert result is True

    @patch("backend.utils.unsubscribe_utils.requests.Session")
    def test_returns_false_when_no_success_keywords(self, mock_session_class):
        """Should return False when response doesn't contain success keywords"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.text = "Please log in to continue"
        mock_session.post.return_value = mock_response

        form = {"url": "https://example.com/unsub", "method": "post", "data": {}}

        result = submit_form(mock_session, form)

        assert result is False

    @patch("backend.utils.unsubscribe_utils.requests.Session")
    def test_handles_http_error(self, mock_session_class):
        """Should return False on HTTP error"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = HTTPError("500 Server Error")
        mock_session.post.return_value = mock_response

        form = {"url": "https://example.com/unsub", "method": "post", "data": {}}

        result = submit_form(mock_session, form)

        assert result is False

    @patch("backend.utils.unsubscribe_utils.requests.Session")
    def test_handles_connection_error(self, mock_session_class):
        """Should return False on connection error"""
        mock_session = Mock()
        mock_session.post.side_effect = RequestException("Connection failed")

        form = {"url": "https://example.com/unsub", "method": "post", "data": {}}

        result = submit_form(mock_session, form)

        assert result is False

    @patch("backend.utils.unsubscribe_utils.requests.Session")
    def test_case_insensitive_success_detection(self, mock_session_class):
        """Should detect success keywords case-insensitively"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.text = "YOU HAVE BEEN UNSUBSCRIBED SUCCESSFULLY"
        mock_session.post.return_value = mock_response

        form = {"url": "https://example.com/unsub", "method": "post", "data": {}}

        result = submit_form(mock_session, form)

        assert result is True


class TestClickLinks:
    """Tests for click_links function"""

    @patch("backend.utils.unsubscribe_utils.requests.Session")
    def test_clicks_unsubscribe_link_successfully(self, mock_session_class):
        """Should click unsubscribe link and return True on success"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.text = "You have been unsubscribed"
        mock_session.get.return_value = mock_response

        html = """
        <html>
            <a href="/confirm-unsub">Click here to unsubscribe</a>
        </html>
        """
        base_url = "https://example.com/unsub"

        result = click_links(mock_session, html, base_url)

        assert result is True
        mock_session.get.assert_called_once()

    @patch("backend.utils.unsubscribe_utils.requests.Session")
    def test_clicks_opt_out_link(self, mock_session_class):
        """Should click opt out link"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.text = "You have been removed from our list"
        mock_session.get.return_value = mock_response

        html = '<a href="/optout">Opt out of emails</a>'
        base_url = "https://example.com"

        result = click_links(mock_session, html, base_url)

        assert result is True

    @patch("backend.utils.unsubscribe_utils.requests.Session")
    def test_clicks_confirm_link(self, mock_session_class):
        """Should click confirm link"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.text = "Success! Unsubscribed"
        mock_session.get.return_value = mock_response

        html = '<a href="/confirm">Confirm unsubscribe</a>'
        base_url = "https://example.com"

        result = click_links(mock_session, html, base_url)

        assert result is True

    @patch("backend.utils.unsubscribe_utils.requests.Session")
    def test_handles_relative_urls(self, mock_session_class):
        """Should convert relative URLs to absolute"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.text = "Unsubscribed successfully"
        mock_session.get.return_value = mock_response

        html = '<a href="confirm.php">Unsubscribe</a>'
        base_url = "https://example.com/emails/"

        result = click_links(mock_session, html, base_url)

        assert result is True
        called_url = mock_session.get.call_args[0][0]
        assert called_url == "https://example.com/emails/confirm.php"

    @patch("backend.utils.unsubscribe_utils.requests.Session")
    def test_stops_after_first_success(self, mock_session_class):
        """Should stop after first successful link click"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.text = "Unsubscribed"
        mock_session.get.return_value = mock_response

        html = """
        <html>
            <a href="/unsub1">Unsubscribe here</a>
            <a href="/unsub2">Or unsubscribe here</a>
        </html>
        """
        base_url = "https://example.com"

        result = click_links(mock_session, html, base_url)

        assert result is True
        assert mock_session.get.call_count == 1

    @patch("backend.utils.unsubscribe_utils.requests.Session")
    def test_tries_next_link_on_failure(self, mock_session_class):
        """Should try next link if first one fails"""
        mock_session = Mock()

        # First call fails, second succeeds
        response1 = Mock()
        response1.text = "Login required"
        response2 = Mock()
        response2.text = "Successfully unsubscribed"

        mock_session.get.side_effect = [response1, response2]

        html = """
        <html>
            <a href="/unsub1">Unsubscribe</a>
            <a href="/unsub2">Remove me</a>
        </html>
        """
        base_url = "https://example.com"

        result = click_links(mock_session, html, base_url)

        assert result is True
        assert mock_session.get.call_count == 2

    @patch("backend.utils.unsubscribe_utils.requests.Session")
    def test_returns_false_when_no_success(self, mock_session_class):
        """Should return False when no link succeeds"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.text = "Login required"
        mock_session.get.return_value = mock_response

        html = '<a href="/unsub">Unsubscribe</a>'
        base_url = "https://example.com"

        result = click_links(mock_session, html, base_url)

        assert result is False

    @patch("backend.utils.unsubscribe_utils.requests.Session")
    def test_handles_request_exception(self, mock_session_class):
        """Should handle request exceptions gracefully"""
        mock_session = Mock()
        mock_session.get.side_effect = RequestException("Connection failed")

        html = '<a href="/unsub">Unsubscribe</a>'
        base_url = "https://example.com"

        result = click_links(mock_session, html, base_url)

        assert result is False

    @patch("backend.utils.unsubscribe_utils.requests.Session")
    def test_ignores_non_unsubscribe_links(self, mock_session_class):
        """Should ignore links without unsubscribe keywords"""
        mock_session = Mock()

        html = """
        <html>
            <a href="/home">Home</a>
            <a href="/contact">Contact Us</a>
            <a href="/about">About</a>
        </html>
        """
        base_url = "https://example.com"

        result = click_links(mock_session, html, base_url)

        assert result is False
        mock_session.get.assert_not_called()


class TestParseListUnsubscribe:
    """Tests for parse_list_unsubscribe function"""

    def test_extracts_http_url_from_header(self):
        """Should extract HTTP URL from List-Unsubscribe header"""
        headers = [
            {"name": "From", "value": "sender@example.com"},
            {
                "name": "List-Unsubscribe",
                "value": "<https://example.com/unsubscribe?id=123>",
            },
        ]

        url = parse_list_unsubscribe(headers)

        assert url == "https://example.com/unsubscribe?id=123"

    def test_extracts_first_http_url_when_multiple(self):
        """Should extract first HTTP URL when multiple URLs present"""
        headers = [
            {
                "name": "List-Unsubscribe",
                "value": "<https://example.com/unsub1>, <https://example.com/unsub2>",
            }
        ]

        url = parse_list_unsubscribe(headers)

        assert url == "https://example.com/unsub1"

    def test_case_insensitive_header_name(self):
        """Should match header name case-insensitively"""
        headers = [
            {"name": "list-unsubscribe", "value": "<https://example.com/unsubscribe>"}
        ]

        url = parse_list_unsubscribe(headers)

        assert url == "https://example.com/unsubscribe"

    def test_handles_mailto_and_http_mixed(self):
        """Should return HTTP URL even when mailto is present"""
        headers = [
            {
                "name": "List-Unsubscribe",
                "value": "<mailto:unsub@example.com>, <https://example.com/unsub>",
            }
        ]

        url = parse_list_unsubscribe(headers)

        assert url == "https://example.com/unsub"

    def test_returns_none_when_no_list_unsubscribe_header(self):
        """Should return None when List-Unsubscribe header not found"""
        headers = [
            {"name": "From", "value": "sender@example.com"},
            {"name": "Subject", "value": "Test email"},
        ]

        url = parse_list_unsubscribe(headers)

        assert url is None

    def test_returns_none_when_only_mailto(self):
        """Should return None when only mailto link present"""
        headers = [{"name": "List-Unsubscribe", "value": "<mailto:unsub@example.com>"}]

        url = parse_list_unsubscribe(headers)

        assert url is None

    def test_handles_empty_header_value(self):
        """Should return None for empty header value"""
        headers = [{"name": "List-Unsubscribe", "value": ""}]

        url = parse_list_unsubscribe(headers)

        assert url is None

    def test_handles_malformed_header(self):
        """Should return None for malformed header"""
        headers = [{"name": "List-Unsubscribe", "value": "not a valid url"}]

        url = parse_list_unsubscribe(headers)

        assert url is None

    def test_extracts_url_without_angle_brackets(self):
        """Should handle URLs without angle brackets"""
        headers = [
            {"name": "List-Unsubscribe", "value": "https://example.com/unsubscribe"}
        ]

        url = parse_list_unsubscribe(headers)

        # This should return None with current implementation since regex looks for < >
        # But if you want to support this, the function would need updating
        assert url is None

    def test_handles_https_url(self):
        """Should extract HTTPS URLs"""
        headers = [
            {
                "name": "List-Unsubscribe",
                "value": "<https://secure.example.com/unsubscribe>",
            }
        ]

        url = parse_list_unsubscribe(headers)

        assert url == "https://secure.example.com/unsubscribe"

    def test_handles_url_with_query_parameters(self):
        """Should preserve query parameters in URL"""
        headers = [
            {
                "name": "List-Unsubscribe",
                "value": "<https://example.com/unsub?email=test@example.com&token=abc123>",
            }
        ]

        url = parse_list_unsubscribe(headers)

        assert url == "https://example.com/unsub?email=test@example.com&token=abc123"


# Integration tests
class TestUnsubscribeWorkflow:
    """Integration tests for complete unsubscribe workflow"""

    @patch("backend.utils.unsubscribe_utils.requests.Session")
    def test_complete_form_submission_workflow(self, mock_session_class):
        """Should complete entire workflow: visit page -> parse form -> submit"""
        mock_session = Mock()

        # Mock visit_page response
        page_html = """
        <form action="/unsubscribe" method="post">
            <p>Unsubscribe from our newsletter</p>
            <input type="hidden" name="token" value="xyz789">
            <input type="email" name="email" value="user@example.com">
        </form>
        """
        mock_response_visit = Mock()
        mock_response_visit.text = page_html
        mock_response_visit.url = "https://example.com/unsubscribe-page"

        # Mock form submission response
        mock_response_submit = Mock()
        mock_response_submit.text = "Successfully unsubscribed"

        mock_session.get.return_value = mock_response_visit
        mock_session.post.return_value = mock_response_submit

        # Step 1: Visit page
        text, final_url = visit_page(mock_session, "https://example.com/unsub")
        assert text == page_html

        # Step 2: Parse forms
        forms = parse_unsubscribe_forms(text, final_url)
        assert len(forms) == 1

        # Step 3: Submit form
        result = submit_form(mock_session, forms[0])
        assert result is True

    @patch("backend.utils.unsubscribe_utils.requests.Session")
    def test_fallback_to_clicking_links(self, mock_session_class):
        """Should fall back to clicking links when no forms found"""
        mock_session = Mock()

        # Page with no forms, only links
        page_html = """
        <html>
            <p>Don't want to receive emails?</p>
            <a href="/confirm-unsub">Click here to unsubscribe</a>
        </html>
        """

        mock_response_visit = Mock()
        mock_response_visit.text = page_html
        mock_response_visit.url = "https://example.com/unsub"

        mock_response_click = Mock()
        mock_response_click.text = "You have been unsubscribed"

        mock_session.get.side_effect = [mock_response_visit, mock_response_click]

        # Visit page
        text, final_url = visit_page(mock_session, "https://example.com/unsub")

        # Try to parse forms (should find none)
        forms = parse_unsubscribe_forms(text, final_url)
        assert len(forms) == 0

        # Fall back to clicking links
        result = click_links(mock_session, text, final_url)
        assert result is True
