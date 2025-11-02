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
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import Category, Email, GmailAccount, User
from backend.utils.gmail_utils import (
    extract_email_html,
    find_unsubscribe_link,
    get_gmail_service,
)

from .schema import CategoryCreate

router = APIRouter()


@router.get("/api/user/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {"id": user.id, "email": user.email, "name": user.name}


@router.get("/api/user/{user_id}/gmail-accounts")
def get_gmail_accounts(user_id: int, db: Session = Depends(get_db)):
    accounts = db.query(GmailAccount).filter(GmailAccount.user_id == user_id).all()
    return [
        {"id": a.id, "email": a.email, "is_primary": a.is_primary} for a in accounts
    ]


@router.post("/api/user/{user_id}/categories")
def create_category(
    user_id: int, category: CategoryCreate, db: Session = Depends(get_db)
):
    new_category = Category(
        user_id=user_id, name=category.name, description=category.description
    )
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return {
        "id": new_category.id,
        "name": new_category.name,
        "description": new_category.description,
    }


@router.get("/api/user/{user_id}/categories")
def get_categories(user_id: int, db: Session = Depends(get_db)):
    categories = db.query(Category).filter(Category.user_id == user_id).all()
    result = []
    for cat in categories:
        email_count = db.query(Email).filter(Email.category_id == cat.id).count()
        result.append(
            {
                "id": cat.id,
                "name": cat.name,
                "description": cat.description,
                "email_count": email_count,
            }
        )
    return result


@router.get("/api/category/{category_id}/emails")
def get_category_emails(category_id: int, db: Session = Depends(get_db)):
    emails = (
        db.query(Email)
        .filter(Email.category_id == category_id)
        .order_by(Email.received_at.desc())
        .all()
    )
    return [
        {
            "id": e.id,
            "gmail_message_id": e.gmail_message_id,
            "subject": e.subject,
            "sender": e.sender,
            "summary": e.summary,
            "received_at": e.received_at.isoformat(),
        }
        for e in emails
    ]


@router.get("/api/email/{email_id}")
def get_email(email_id: int, db: Session = Depends(get_db)):
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    return {
        "id": email.id,
        "subject": email.subject,
        "sender": email.sender,
        "body": email.body,
        "summary": email.summary,
        "received_at": email.received_at.isoformat(),
    }


@router.post("/api/emails/delete")
def delete_emails(email_ids: list[int], db: Session = Depends(get_db)):
    db.query(Email).filter(Email.id.in_(email_ids)).delete(synchronize_session=False)
    db.commit()
    return {"deleted": len(email_ids)}


@router.post("/api/emails/unsubscribe")
def unsubscribe_emails(email_ids: list[int], db: Session = Depends(get_db)):
    """Unsubscribe by clicking on the link and follow the forms if any"""

    results = []
    for email_id in email_ids:
        email = db.query(Email).filter(Email.id == email_id).first()
        if not email:
            continue

        gmail_account = email.gmail_account
        service = get_gmail_service(gmail_account.credentials)

        try:
            message = (
                service.users()
                .messages()
                .get(userId="me", id=email.gmail_message_id, format="full")
                .execute()
            )
            headers = message["payload"].get("headers", [])

            html_content = extract_email_html(message)

            content_to_search = html_content if html_content else email.body

            unsubscribe_link = find_unsubscribe_link(content_to_search, headers)

            if unsubscribe_link:
                if unsubscribe_link.startswith("mailto:"):
                    results.append(
                        {
                            "email_id": email_id,
                            "success": False,
                            "error": "Requires email (not automated)",
                        }
                    )
                    continue

                print(f"\n Visiting: {unsubscribe_link}")

                # Step 1: Visit the unsubscribe page
                session = requests.Session()
                session.headers.update(
                    {
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                    }
                )

                response = session.get(unsubscribe_link, timeout=10)

                if response.status_code != 200:
                    results.append(
                        {
                            "email_id": email_id,
                            "success": False,
                            "error": f"HTTP {response.status_code}",
                        }
                    )
                    continue

                # Step 2: Parse the page
                soup = BeautifulSoup(response.text, "html.parser")
                page_text = soup.get_text().lower()

                # Check if already unsubscribed
                if any(
                    word in page_text
                    for word in ["unsubscribed", "removed", "no longer receive"]
                ):
                    print(f"Already unsubscribed!")
                    results.append(
                        {
                            "email_id": email_id,
                            "success": True,
                            "message": "Unsubscribed (one-click or already done)",
                        }
                    )
                    continue

                # Step 3: Look for unsubscribe buttons/forms
                unsubscribe_found = False

                # Look for forms
                forms = soup.find_all("form")
                for form in forms:
                    form_text = form.get_text().lower()
                    if (
                        "unsubscribe" in form_text
                        or "opt out" in form_text
                        or "remove" in form_text
                    ):
                        # Found unsubscribe form!
                        action = form.get("action", "")
                        method = form.get("method", "get").lower()

                        # Build the URL
                        if action:
                            from urllib.parse import urljoin

                            submit_url = urljoin(response.url, action)
                        else:
                            submit_url = response.url

                        # Get form data
                        form_data = {}
                        for input_tag in form.find_all("input"):
                            name = input_tag.get("name")
                            value = input_tag.get("value", "")
                            input_type = input_tag.get("type", "").lower()

                            if name:
                                # For checkboxes/radio, only include if checked
                                if input_type in ["checkbox", "radio"]:
                                    if input_tag.get("checked"):
                                        form_data[name] = value
                                else:
                                    form_data[name] = value

                        print(f"Submitting form to: {submit_url}")

                        # Submit the form
                        if method == "post":
                            form_response = session.post(
                                submit_url, data=form_data, timeout=10
                            )
                        else:
                            form_response = session.get(
                                submit_url, params=form_data, timeout=10
                            )

                        if form_response.status_code == 200:
                            result_text = form_response.text.lower()
                            if any(
                                word in result_text
                                for word in [
                                    "unsubscribed",
                                    "removed",
                                    "success",
                                    "confirmed",
                                ]
                            ):
                                print(f"Form submitted successfully!")
                                results.append(
                                    {
                                        "email_id": email_id,
                                        "success": True,
                                        "message": "Unsubscribed via form submission",
                                    }
                                )
                                unsubscribe_found = True
                                break
                        else:
                            print(
                                f"Form submission got status {form_response.status_code}"
                            )

                # Look for unsubscribe links/buttons if no form found
                if not unsubscribe_found:
                    links = soup.find_all("a", href=True)
                    for link in links:
                        link_text = link.get_text().lower()
                        href = link.get("href", "")

                        if any(
                            word in link_text
                            for word in ["unsubscribe", "opt out", "remove", "confirm"]
                        ):
                            # Click this link
                            click_url = urljoin(response.url, href)
                            print(f"Clicking link: {click_url}")

                            click_response = session.get(click_url, timeout=10)

                            if click_response.status_code == 200:
                                result_text = click_response.text.lower()
                                if any(
                                    word in result_text
                                    for word in ["unsubscribed", "removed", "success"]
                                ):
                                    print(f"Successfully unsubscribed via link!")
                                    results.append(
                                        {
                                            "email_id": email_id,
                                            "success": True,
                                            "message": "Unsubscribed via confirmation link",
                                        }
                                    )
                                    unsubscribe_found = True
                                    break

                if not unsubscribe_found:
                    results.append(
                        {
                            "email_id": email_id,
                            "success": "partial",
                            "message": "Visited page but couldn't auto-complete (may need manual action)",
                            "url": unsubscribe_link,
                        }
                    )

        except Exception as e:
            print(f"Error: {e}")
            results.append({"email_id": email_id, "success": False, "error": str(e)})

    return {"results": results}
