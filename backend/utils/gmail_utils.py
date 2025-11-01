from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import json
import base64
import re
from typing import List, Optional


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
    """Find unsubscribe link in email"""
    # Check List-Unsubscribe header
    for header in email_headers:
        if header["name"].lower() == "list-unsubscribe":
            match = re.search(r"<(https?://[^>]+)>", header["value"])
            if match:
                return match.group(1)

    # Search in body
    unsubscribe_patterns = [
        r'<a[^>]*href=["\']([^"\']*unsubscribe[^"\']*)["\']',
        r'(https?://[^\s<>"]+unsubscribe[^\s<>"]*)',
    ]

    for pattern in unsubscribe_patterns:
        match = re.search(pattern, email_body, re.IGNORECASE)
        if match:
            return match.group(1)

    return None
