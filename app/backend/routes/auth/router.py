import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response

from sqlalchemy import delete
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database import get_db
from security import hash_password, verify_password

from models.users import User
from schemas.user import UserResponse
from models.sessions import UserSession
from schemas.auth import LoginRequest, RegisterRequest

from dependencies.auth import (
    COOKIE_NAME,
    IDLE_TIMEOUT,
    get_current_user,
    hash_session_token,
    require_trusted_origin,
    set_session_cookie,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# creates a dummy bcrypt hash so login still checks a password when the email doesn’t exist, 
# making response times more consistent and helping hide which emails are registered.
DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(32))

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    user = User(
        email=str(data.email),
        username=data.username,
        password_hash=hash_password(data.password),
        display_name=data.display_name,
    )

    db.add(user)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()

        # PostgreSQL code for a unique constraint violation.
        if getattr(error.orig, "sqlstate", None) == "23505":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email or username is already registered.",
            ) from error

        raise

    db.refresh(user)
    return user

@router.post("/login", response_model=UserResponse, dependencies=[Depends(require_trusted_origin)])
def login(data: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=str(data.email)).first()

    password_hash = (user.password_hash if user is not None else DUMMY_PASSWORD_HASH)
    password_matches = verify_password(data.password, password_hash)

    if user is None or not password_matches or not user.is_active:
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    # Replace a previous session supplied by this browser.
    previous_token = request.cookies.get(COOKIE_NAME)

    if previous_token:
        db.execute(delete(UserSession).where(UserSession.token_hash == hash_session_token(previous_token)))

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + IDLE_TIMEOUT

    db.add(UserSession(user_id=user.id, token_hash=hash_session_token(token), expires_at=expires_at))
    db.commit()

    set_session_cookie(response, token, expires_at)
    response.headers["Cache-Control"] = "no-store"

    return user

@router.get("/me", response_model=UserResponse)
def me(response: Response, user: User = Depends(get_current_user)):
    response.headers["Cache-Control"] = "no-store"
    return user

@router.post("/logout", dependencies=[Depends(require_trusted_origin)])
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(COOKIE_NAME)

    if token:
        db.execute(
            delete(UserSession).where(
                UserSession.token_hash == hash_session_token(token)
            )
        )
        db.commit()

    response.delete_cookie(COOKIE_NAME, path="/")
    response.headers["Cache-Control"] = "no-store"

    return {"message": "Signed out."}