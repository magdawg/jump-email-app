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

"""
Simple cookie-based session authentication for FastAPI
No external dependencies required - uses built-in Python libraries
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import User

# In-memory session store
# For production with multiple servers, use Redis or database
# Format: {"session_token": {"user_id": 1, "expires": datetime}}
sessions = {}

# Session expiration time (7 days)
SESSION_EXPIRE_DAYS = 7


def create_session(user_id: int) -> str:
    """
    Create a new session for a user

    Args:
        user_id: The user's database ID

    Returns:
        session_token: A random session token
    """
    # Generate secure random token (32 bytes = 256 bits of entropy)
    session_token = secrets.token_urlsafe(32)

    # Store session with expiration
    expires = datetime.utcnow() + timedelta(days=SESSION_EXPIRE_DAYS)
    sessions[session_token] = {"user_id": user_id, "expires": expires}

    return session_token


def get_session(session_token: str) -> Optional[dict]:
    """
    Get session data if valid

    Args:
        session_token: The session token from cookie

    Returns:
        Session data or None if invalid/expired
    """
    if session_token not in sessions:
        return None

    session_data = sessions[session_token]

    # Check if expired
    if datetime.utcnow() > session_data["expires"]:
        # Clean up expired session
        del sessions[session_token]
        return None

    return session_data


def delete_session(session_token: str) -> None:
    """
    Delete a session (logout)

    Args:
        session_token: The session token to delete
    """
    if session_token in sessions:
        del sessions[session_token]


def get_current_user(
    session: Optional[str] = Cookie(None), db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user from cookie

    Usage:
        @router.get("/api/protected")
        def protected_route(current_user: User = Depends(get_current_user)):
            return {"user_id": current_user.id}

    Args:
        session: Session token from cookie
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If not authenticated
    """
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    session_data = get_session(session)
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    user_id = session_data["user_id"]
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    return user


def verify_user_access(current_user: User, resource_user_id: int) -> None:
    """
    Verify user has access to a resource

    Args:
        current_user: The authenticated user
        resource_user_id: The user ID that owns the resource

    Raises:
        HTTPException: If user doesn't have access
    """
    if current_user.id != resource_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this resource",
        )


def set_session_cookie(response: Response, session_token: str) -> None:
    """
    Set session cookie in response

    Args:
        response: FastAPI Response object
        session_token: The session token to set
    """
    response.set_cookie(
        key="session",
        value=session_token,
        httponly=True,  # Prevents JavaScript access (XSS protection)
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",  # CSRF protection
        max_age=SESSION_EXPIRE_DAYS * 24 * 60 * 60,  # 7 days in seconds
    )


def clear_session_cookie(response: Response) -> None:
    """
    Clear session cookie (logout)

    Args:
        response: FastAPI Response object
    """
    response.delete_cookie(key="session")
