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

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import traceback

from backend.db.database import get_db
from backend.db.models import Category, Email, GmailAccount, User
from backend.utils.gmail_utils import (
    extract_email_html,
    find_unsubscribe_link,
    get_gmail_service,
)
from backend.utils.unsubscribe_utils import (
    parse_unsubscribe_forms,
    submit_form,
    click_links,
    create_session,
    visit_page,
    parse_list_unsubscribe,
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
    results = []

    for email_id in email_ids:
        email = db.query(Email).filter(Email.id == email_id).first()
        if not email:
            results.append(
                {"email_id": email_id, "success": False, "error": "Email not found"}
            )
            continue

        try:
            gmail_account = email.gmail_account
            service = get_gmail_service(gmail_account.credentials)
            message = (
                service.users()
                .messages()
                .get(userId="me", id=email.gmail_message_id, format="full")
                .execute()
            )
            headers = message["payload"].get("headers", [])
            html_content = extract_email_html(message)
            content_to_search = html_content if html_content else email.body

            # --- Step 1: Try List-Unsubscribe header ---
            list_unsub_url = parse_list_unsubscribe(headers)
            if list_unsub_url:
                if list_unsub_url.startswith("mailto:"):
                    results.append(
                        {
                            "email_id": email_id,
                            "success": False,
                            "error": "List-Unsubscribe requires sending email (cannot automate)",
                        }
                    )
                    continue
                else:
                    session = create_session()
                    page_text, final_url = visit_page(session, list_unsub_url)
                    if page_text and any(
                        word in page_text.lower()
                        for word in ["unsubscribed", "removed", "success"]
                    ):
                        results.append(
                            {
                                "email_id": email_id,
                                "success": True,
                                "message": "Unsubscribed via List-Unsubscribe header",
                            }
                        )
                        continue
                    else:
                        results.append(
                            {
                                "email_id": email_id,
                                "success": "partial",
                                "message": "List-Unsubscribe URL visited but JS or login may be required",
                                "url": list_unsub_url,
                            }
                        )
                        continue

            # --- Step 2: Fallback to link in email body ---
            unsubscribe_link = find_unsubscribe_link(content_to_search, headers)
            if not unsubscribe_link:
                results.append(
                    {
                        "email_id": email_id,
                        "success": False,
                        "error": "No unsubscribe link found",
                    }
                )
                continue

            if unsubscribe_link.startswith("mailto:"):
                results.append(
                    {
                        "email_id": email_id,
                        "success": False,
                        "error": "Requires sending email (cannot automate)",
                    }
                )
                continue

            session = create_session()
            page_text, final_url = visit_page(session, unsubscribe_link)
            if not page_text:
                results.append(
                    {
                        "email_id": email_id,
                        "success": False,
                        "error": "Failed to visit page",
                    }
                )
                continue

            # Check if already unsubscribed
            if any(
                word in page_text.lower()
                for word in ["unsubscribed", "removed", "no longer receive"]
            ):
                results.append(
                    {
                        "email_id": email_id,
                        "success": True,
                        "message": "Already unsubscribed or one-click successful",
                    }
                )
                continue

            # Try forms first
            forms = parse_unsubscribe_forms(page_text, final_url)
            unsub_done = False
            for form in forms:
                if submit_form(session, form):
                    results.append(
                        {
                            "email_id": email_id,
                            "success": True,
                            "message": "Unsubscribed via form submission",
                        }
                    )
                    unsub_done = True
                    break

            # Try links if forms failed
            if not unsub_done and click_links(session, page_text, final_url):
                results.append(
                    {
                        "email_id": email_id,
                        "success": True,
                        "message": "Unsubscribed via confirmation link",
                    }
                )
                unsub_done = True

            if not unsub_done:
                # --- Step 3: JS/login required ---
                results.append(
                    {
                        "email_id": email_id,
                        "success": "partial",
                        "message": "Page may require login or JS to unsubscribe; manual or browser automation needed",
                        "url": unsubscribe_link,
                    }
                )

        except Exception as e:
            print(f"Error processing email {email_id}: {e}")
            print(traceback.format_exc())
            results.append({"email_id": email_id, "success": False, "error": str(e)})

    return {"results": results}
