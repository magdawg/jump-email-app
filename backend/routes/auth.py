from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from backend.config import (FRONTEND_URL, GOOGLE_CLIENT_ID,
                            GOOGLE_CLIENT_SECRET, REDIRECT_URI, SCOPES)
from backend.db.database import get_db
from backend.db.models import GmailAccount, User

router = APIRouter()


@router.get("/auth/login")
def login(user_id: int = None):
    print(
        f"DEBUG: GOOGLE_CLIENT_ID = {GOOGLE_CLIENT_ID[:20]}..."
        if GOOGLE_CLIENT_ID
        else "DEBUG: GOOGLE_CLIENT_ID is None"
    )
    print(f"DEBUG: REDIRECT_URI = {REDIRECT_URI}")

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=str(user_id) if user_id else "new",
    )

    return {"auth_url": authorization_url, "state": state}


@router.get("/auth/callback")
def auth_callback(code: str, state: str, db: Session = Depends(get_db)):
    print(f"\n{'='*60}")
    print(f"AUTH CALLBACK RECEIVED")
    print(f"{'='*60}")

    try:
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI,
        )

        flow.fetch_token(code=code)
        credentials = flow.credentials
        print(f"✅ Token fetched successfully")

        # Get user info
        user_info_service = build("oauth2", "v2", credentials=credentials)
        user_info = user_info_service.userinfo().get().execute()
        print(f"✅ User info retrieved: {user_info.get('email')}")

        # Check if this is for an existing user
        if state and state != "new":
            # Adding account to existing user
            try:
                existing_user_id = int(state)
                user = db.query(User).filter(User.id == existing_user_id).first()
                if not user:
                    # Fallback to creating new user if state user doesn't exist
                    user = (
                        db.query(User).filter(User.email == user_info["email"]).first()
                    )
                    if not user:
                        user = User(
                            email=user_info["email"], name=user_info.get("name")
                        )
                        db.add(user)
                        db.commit()
                        db.refresh(user)
            except (ValueError, TypeError):
                # Invalid state, treat as new user
                user = db.query(User).filter(User.email == user_info["email"]).first()
                if not user:
                    user = User(email=user_info["email"], name=user_info.get("name"))
                    db.add(user)
                    db.commit()
                    db.refresh(user)
        else:
            # New user login
            user = db.query(User).filter(User.email == user_info["email"]).first()
            if not user:
                user = User(email=user_info["email"], name=user_info.get("name"))
                db.add(user)
                db.commit()
                db.refresh(user)

        # Add Gmail account - check if this email is already connected to THIS user
        gmail_account = (
            db.query(GmailAccount)
            .filter(
                GmailAccount.user_id == user.id,
                GmailAccount.email == user_info["email"],
            )
            .first()
        )

        if not gmail_account:
            # Check if account exists for different user (shouldn't happen but handle it)
            existing_account = (
                db.query(GmailAccount)
                .filter(GmailAccount.email == user_info["email"])
                .first()
            )

            if existing_account and existing_account.user_id != user.id:
                # Move account to current user or skip
                print(
                    f"⚠️  Account {user_info['email']} already connected to different user"
                )
                # For now, update the credentials anyway
                existing_account.credentials = credentials.to_json()
                db.commit()
                gmail_account = existing_account
            else:
                # Create new gmail account for this user
                is_primary = (
                    db.query(GmailAccount)
                    .filter(GmailAccount.user_id == user.id)
                    .count()
                    == 0
                )
                gmail_account = GmailAccount(
                    user_id=user.id,
                    email=user_info["email"],
                    credentials=credentials.to_json(),
                    is_primary=is_primary,
                )
                db.add(gmail_account)
                db.commit()
                print(f"✅ Gmail account {user_info['email']} added to user {user.id}")
        else:
            # Update existing account credentials
            gmail_account.credentials = credentials.to_json()
            db.commit()
            print(f"✅ Gmail account credentials updated for {user_info['email']}")

        if not gmail_account:
            is_primary = (
                db.query(GmailAccount).filter(GmailAccount.user_id == user.id).count()
                == 0
            )
            gmail_account = GmailAccount(
                user_id=user.id,
                email=user_info["email"],
                credentials=credentials.to_json(),
                is_primary=is_primary,
            )
            db.add(gmail_account)
            db.commit()
        else:
            gmail_account.credentials = credentials.to_json()
            db.commit()

        print(f"{'='*60}\n")
        return RedirectResponse(url=f"{FRONTEND_URL}?user_id={user.id}")

    except Exception as e:
        print(f"ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))
