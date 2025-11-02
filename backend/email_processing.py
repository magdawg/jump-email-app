from sqlalchemy.orm import Session
from datetime import datetime

from backend.db.models import GmailAccount, Category, Email
from backend.utils.gmail_utils import get_gmail_service, extract_email_content
from backend.utils.ai_utils import categorize_email, summarize_email


def get_or_create_uncategorized_category(user_id: int, db: Session) -> int:
    """Get or create the Uncategorized category for a user"""
    uncategorized = (
        db.query(Category)
        .filter(Category.user_id == user_id, Category.name == "Uncategorized")
        .first()
    )

    if not uncategorized:
        uncategorized = Category(
            user_id=user_id,
            name="Uncategorized",
            description="Emails that don't match any specific category",
        )
        db.add(uncategorized)
        db.commit()
        db.refresh(uncategorized)
        print(f"Created 'Uncategorized' category for user {user_id}")

    return uncategorized.id


def process_new_emails(db: Session):
    """Background job to process new emails"""
    print(f"\n{'='*60}")
    print(f"PROCESSING NEW EMAILS - {datetime.utcnow()}")
    print(f"{'='*60}")

    gmail_accounts = db.query(GmailAccount).all()
    print(f"Found {len(gmail_accounts)} Gmail account(s) to process")

    for account in gmail_accounts:
        print(f"\n--- Processing account: {account.email} ---")
        try:
            service = get_gmail_service(account.credentials)

            results = (
                service.users()
                .messages()
                .list(userId="me", q="is:unread in:inbox", maxResults=10)
                .execute()
            )

            messages = results.get("messages", [])
            print(f"Found {len(messages)} unread email(s)")

            for idx, msg in enumerate(messages, 1):
                print(f"\n  Email {idx}/{len(messages)}:")

                existing = (
                    db.query(Email).filter(Email.gmail_message_id == msg["id"]).first()
                )
                if existing:
                    print(f"Already processed, skipping")
                    continue

                message = (
                    service.users()
                    .messages()
                    .get(userId="me", id=msg["id"], format="full")
                    .execute()
                )

                content = extract_email_content(message)

                headers = message["payload"].get("headers", [])
                subject = ""
                sender = ""
                for header in headers:
                    if header["name"] == "Subject":
                        subject = header["value"]
                    elif header["name"] == "From":
                        sender = header["value"]

                print(f"Subject: {subject[:50]}...")
                print(f"From: {sender}")

                categories = (
                    db.query(Category).filter(Category.user_id == account.user_id).all()
                )
                print(f"Available categories: {len(categories)}")

                if categories:
                    category_id = categorize_email(content, categories)

                    if category_id is None:
                        category_id = get_or_create_uncategorized_category(
                            account.user_id, db
                        )
                        print(f"No match - categorized as: Uncategorized")
                    else:
                        category_name = next(
                            (c.name for c in categories if c.id == category_id),
                            "Unknown",
                        )
                        print(f"Categorized as: {category_name}")
                else:
                    category_id = get_or_create_uncategorized_category(
                        account.user_id, db
                    )
                    print(f"No categories - using: Uncategorized")

                summary = summarize_email(content)
                print(f"Summary: {summary[:60]}...")

                email = Email(
                    gmail_account_id=account.id,
                    category_id=category_id,
                    gmail_message_id=msg["id"],
                    subject=subject,
                    sender=sender,
                    body=content,
                    summary=summary,
                    received_at=datetime.utcnow(),
                )
                db.add(email)

                service.users().messages().modify(
                    userId="me",
                    id=msg["id"],
                    body={"removeLabelIds": ["UNREAD", "INBOX"]},
                ).execute()
                print(f"Archived in Gmail")

            db.commit()
            print(f"\n✅ Successfully processed account: {account.email}")

        except Exception as e:
            print(f"\n❌ Error processing emails for {account.email}: {e}")
            db.rollback()

    print(f"\n{'='*60}")
    print(f"EMAIL PROCESSING COMPLETE")
    print(f"{'='*60}\n")
