import os
import hashlib

from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, Request, Response

from sqlalchemy import update
from sqlalchemy.orm import Session

from database import get_db
from models.sessions import UserSession
from models.users import User

COOKIE_NAME = "session"
IDLE_TIMEOUT = timedelta(hours=24)
MAX_LIFETIME = timedelta(days=7)
RENEWAL_THRESHOLD = timedelta(hours=12)

def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def set_session_cookie(
    response: Response,
    token: str,
    expires_at: datetime,
):
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        expires=expires_at,
        httponly=True,
        secure=os.environ.get("APP_ENV") == "production",
        samesite="lax",
        path="/",
    )

def require_trusted_origin(request: Request):
    allowed_origins = {
        origin.strip()
        for origin in os.environ["AUTH_ALLOWED_ORIGINS"].split(",")
        if origin.strip()
    }

    if request.headers.get("origin") not in allowed_origins:
        raise HTTPException(
            status_code=403,
            detail="Request origin is not allowed.",
        )

def get_current_user(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> User:
    token = request.cookies.get(COOKIE_NAME)

    if not token:
        raise HTTPException(status_code=401, detail="Please sign in.")

    session = db.query(UserSession).filter_by(
        token_hash=hash_session_token(token),
    ).first()

    now = datetime.now(timezone.utc)

    if session is None:
        raise HTTPException(status_code=401, detail="Please sign in.")

    absolute_expiry = session.created_at + MAX_LIFETIME

    if session.expires_at <= now or absolute_expiry <= now:
        raise HTTPException(
            status_code=401,
            detail="Session expired. Please sign in again.",
        )

    user = db.get(User, session.user_id)

    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Please sign in.")

    if session.expires_at - now < RENEWAL_THRESHOLD:
        new_expiry = min(now + IDLE_TIMEOUT, absolute_expiry)

        renewed_session_id = db.execute(
            update(UserSession)
            .where(
                UserSession.id == session.id,
                UserSession.expires_at > now,
            )
            .values(expires_at=new_expiry)
            .returning(UserSession.id)
        ).scalar_one_or_none()

        if renewed_session_id is None:
            db.rollback()
            raise HTTPException(status_code=401, detail="Please sign in.")

        db.commit()
        set_session_cookie(response, token, new_expiry)

    return user