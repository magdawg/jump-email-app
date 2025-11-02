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

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import traceback
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def create_session():
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
    )
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def visit_page(session, url, timeout=15):
    try:
        response = session.get(url, timeout=timeout)
        response.raise_for_status()
        return response.text, response.url
    except Exception as e:
        print(f"Error visiting {url}: {e}")
        return None, url


def parse_unsubscribe_forms(html_text, base_url):
    soup = BeautifulSoup(html_text, "html.parser")
    forms_to_submit = []

    for form in soup.find_all("form"):
        form_text = form.get_text().lower()
        if any(
            keyword in form_text for keyword in ["unsubscribe", "opt out", "remove"]
        ):
            action = form.get("action", "")
            method = form.get("method", "get").lower()
            submit_url = urljoin(base_url, action) if action else base_url

            form_data = {}
            for input_tag in form.find_all("input"):
                name = input_tag.get("name")
                if not name:
                    continue
                value = input_tag.get("value", "")
                input_type = input_tag.get("type", "").lower()
                if input_type in ["checkbox", "radio"]:
                    # Use has_attr() to properly detect boolean attributes
                    if input_tag.has_attr("checked"):
                        form_data[name] = value
                else:
                    form_data[name] = value

            forms_to_submit.append(
                {"url": submit_url, "method": method, "data": form_data}
            )
    return forms_to_submit


def submit_form(session, form):
    try:
        if form["method"] == "post":
            resp = session.post(form["url"], data=form["data"], timeout=15)
        else:
            resp = session.get(form["url"], params=form["data"], timeout=15)
        resp.raise_for_status()
        page_text = resp.text.lower()
        if any(
            word in page_text
            for word in ["unsubscribed", "removed", "success", "confirmed"]
        ):
            return True
        return False
    except Exception as e:
        print(f"Form submission error: {e}")
        print(traceback.format_exc())
        return False


def click_links(session, html_text, base_url):
    soup = BeautifulSoup(html_text, "html.parser")
    for link in soup.find_all("a", href=True):
        link_text = link.get_text().lower()
        if any(
            word in link_text
            for word in ["unsubscribe", "opt out", "remove", "confirm"]
        ):
            click_url = urljoin(base_url, link.get("href"))
            try:
                resp = session.get(click_url, timeout=15)
                resp.raise_for_status()
                if any(
                    word in resp.text.lower()
                    for word in ["unsubscribed", "removed", "success"]
                ):
                    return True
            except Exception as e:
                print(f"Error clicking link {click_url}: {e}")
    return False


def parse_list_unsubscribe(headers):
    """Return a HTTP URL from List-Unsubscribe header if present"""
    for h in headers:
        if h.get("name", "").lower() == "list-unsubscribe":
            value = h.get("value", "")
            # Try to find an HTTP URL first
            import re

            urls = re.findall(r"<(https?://[^>]+)>", value)
            if urls:
                return urls[0]
    return None
