from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.db.database import get_db
from backend.db.models import User, Category, Email, GmailAccount
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
def delete_emails(email_ids: List[int], db: Session = Depends(get_db)):
    db.query(Email).filter(Email.id.in_(email_ids)).delete(synchronize_session=False)
    db.commit()
    return {"deleted": len(email_ids)}


@router.post("/api/emails/unsubscribe")
def unsubscribe_emails(email_ids: List[int], db: Session = Depends(get_db)):
    """Unsubscribe from emails using AI agent"""
    from backend.utils.gmail_utils import get_gmail_service, find_unsubscribe_link

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
            unsubscribe_link = find_unsubscribe_link(email.body, headers)

            if unsubscribe_link:
                results.append(
                    {"email_id": email_id, "success": True, "url": unsubscribe_link}
                )
            else:
                results.append(
                    {
                        "email_id": email_id,
                        "success": False,
                        "error": "No unsubscribe link found",
                    }
                )
        except Exception as e:
            results.append({"email_id": email_id, "success": False, "error": str(e)})

    return {"results": results}
