import base64
import json
import re
from typing import Optional
from urllib.parse import unquote
from bs4 import BeautifulSoup

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def get_gmail_service(credentials_json):
    """Build Gmail service from credentials"""
    creds_dict = json.loads(credentials_json)
    credentials = Credentials.from_authorized_user_info(creds_dict)
    return build("gmail", "v1", credentials=credentials)


def extract_email_content(message):
    """Extract text content from Gmail message"""
    if "payload" not in message:
        return ""

    payload = message["payload"]

    # Get subject
    subject = ""
    for header in payload.get("headers", []):
        if header["name"] == "Subject":
            subject = header["value"]
            break

    # Get body
    body = ""
    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain":
                if "data" in part["body"]:
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode(
                        "utf-8"
                    )
                    break
    elif "body" in payload and "data" in payload["body"]:
        body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

    return f"Subject: {subject}\n\n{body}"


def find_unsubscribe_link(email_body: str, email_headers: list) -> Optional[str]:
    """
    Find unsubscribe link using BeautifulSoup for HTML parsing
    Handles tracking links where URL doesn't contain 'unsubscribe' but text does
    """

    print(f"\n{'='*60}")
    print("SEARCHING FOR UNSUBSCRIBE LINK")
    print(f"{'='*60}")

    # 1. Check List-Unsubscribe header first (most reliable)
    for header in email_headers:
        header_name = header.get("name", "").lower()
        header_value = header.get("value", "")

        if header_name == "list-unsubscribe":
            print(f"✓ Found List-Unsubscribe header")

            # Use BeautifulSoup to parse header value (in case it contains HTML)
            soup_header = BeautifulSoup(header_value, "html.parser")
            links = soup_header.find_all("a", href=True)

            if links:
                url = links[0]["href"]
                if url.startswith("http"):
                    print(f"✓ Extracted URL from header: {url[:80]}...")
                    return url

            # Fallback: extract from text
            import re

            url_match = re.search(r"<?(https?://[^>,\s]+)>?", header_value)
            if url_match:
                url = url_match.group(1)
                print(f"✓ Extracted URL from header: {url[:80]}...")
                return url

    # 2. Parse HTML body with BeautifulSoup
    print(f"Parsing HTML body ({len(email_body)} chars)...")

    try:
        soup = BeautifulSoup(email_body, "html.parser")

        # Find all links
        all_links = soup.find_all("a", href=True)
        print(f"Found {len(all_links)} links in email")

        # Unsubscribe keywords to look for
        unsubscribe_keywords = [
            "unsubscribe",
            "opt-out",
            "opt out",
            "optout",
            "remove",
            "stop receiving",
            "stop emails",
            "cancel subscription",
            "email preferences",
            "manage preferences",
            "update preferences",
            "do not send",
            "leave this list",
            "update subscription",
            "email settings",
        ]

        # First pass: Check link TEXT (catches tracking links)
        for idx, link in enumerate(all_links):
            href = link.get("href", "").strip()

            # Skip non-http links
            if not href.startswith("http"):
                continue

            # Skip mailto links
            if href.startswith("mailto:"):
                continue

            # Get all text in the link (including nested elements)
            link_text = link.get_text(strip=True).lower()

            # Check if link text contains any unsubscribe keyword
            for keyword in unsubscribe_keywords:
                if keyword in link_text:
                    print(f"✓ Found unsubscribe link by TEXT: '{link_text[:50]}'")
                    print(f"  URL: {href[:80]}...")
                    return unquote(href)

        # Second pass: Check link HREF (for direct unsubscribe URLs)
        for idx, link in enumerate(all_links):
            href = link.get("href", "").strip().lower()

            # Skip non-http links
            if not href.startswith("http"):
                continue

            # Skip mailto links
            if href.startswith("mailto:"):
                continue

            # Check if URL contains unsubscribe keyword
            for keyword in unsubscribe_keywords:
                if keyword in href:
                    print(f"✓ Found unsubscribe link by URL keyword: '{keyword}'")
                    print(f"  URL: {href[:80]}...")
                    return unquote(href)

        # Third pass: Check parent elements (sometimes text is in <td>, not <a>)
        # Look for table cells or divs containing "unsubscribe"
        for element in soup.find_all(["td", "div", "p", "span"]):
            text = element.get_text(strip=True).lower()

            # Check if element text contains unsubscribe
            for keyword in unsubscribe_keywords:
                if keyword in text:
                    # Find any link within this element
                    links_in_element = element.find_all("a", href=True)
                    for link in links_in_element:
                        href = link.get("href", "").strip()
                        if href.startswith("http") and not href.startswith("mailto:"):
                            print(
                                f"✓ Found unsubscribe link in parent element with text: '{text[:50]}'"
                            )
                            print(f"  URL: {href[:80]}...")
                            return unquote(href)

        print("⚠ HTML parsed successfully but no unsubscribe link found")

    except Exception as e:
        print(f"⚠ Error parsing HTML with BeautifulSoup: {e}")
        return None

    # 4. Last resort: If "unsubscribe" text exists, look for any nearby link
    if "unsubscribe" in email_body.lower():
        print("Found 'unsubscribe' text in email, searching for nearby links...")

        # Parse again and get all links
        soup = BeautifulSoup(email_body, "html.parser")
        all_links = soup.find_all("a", href=True)

        # Filter out social media links
        social_domains = [
            "facebook.com",
            "twitter.com",
            "linkedin.com",
            "instagram.com",
            "youtube.com",
            "pinterest.com",
        ]

        filtered_links = []
        for link in all_links:
            href = link.get("href", "")
            if href.startswith("http") and not href.startswith("mailto:"):
                if not any(domain in href.lower() for domain in social_domains):
                    filtered_links.append(href)

        if filtered_links:
            # Return last link (unsubscribe usually at bottom)
            last_link = filtered_links[-1]
            print(f"⚠ Using last non-social link as fallback")
            print(f"  URL: {last_link[:80]}...")
            return unquote(last_link)

    print("✗ No unsubscribe link found")
    print(f"{'='*60}\n")
    return None


def extract_email_html(message: dict) -> str:
    """
    Extract HTML content from Gmail message
    Preserves hyperlinks and HTML elements for unsubscribe detection
    """
    if "payload" not in message:
        return ""

    payload = message["payload"]

    def decode_part(part_data):
        """Decode base64 email content"""
        try:
            return base64.urlsafe_b64decode(part_data).decode("utf-8", errors="ignore")
        except Exception:
            return ""

    # Check if message has parts (multipart)
    if "parts" in payload:
        for part in payload["parts"]:
            mime_type = part.get("mimeType", "")

            # Look for HTML content first
            if mime_type == "text/html":
                if "data" in part.get("body", {}):
                    return decode_part(part["body"]["data"])

            # Check nested parts
            elif "parts" in part:
                for subpart in part["parts"]:
                    if subpart.get("mimeType") == "text/html":
                        if "data" in subpart.get("body", {}):
                            return decode_part(subpart["body"]["data"])

    # If no parts, try direct body
    elif "body" in payload and "data" in payload["body"]:
        return decode_part(payload["body"]["data"])

    return ""
