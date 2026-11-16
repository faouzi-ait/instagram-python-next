import logging
import secrets
from typing import Annotated
from rate_limit import limiter
from datetime import datetime, timezone
from fastapi import (File, UploadFile)
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response

from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from database import get_db
from security import hash_password, verify_password
from services.avatar import delete_avatar, upload_avatar

from models.users import User
from models.sessions import UserSession
from schemas.user import UserResponse, AvatarResponse
from schemas.auth import LoginRequest, RegisterRequest

from dependencies.auth import (
    COOKIE_NAME,
    IDLE_TIMEOUT,
    get_current_user,
    hash_session_token,
    require_trusted_origin,
    set_session_cookie,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])

# creates a dummy bcrypt hash so login still checks a password when the email doesn’t exist, 
# making response times more consistent and helping hide which emails are registered.
DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(32))

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/hour")
def register(request: Request, data: RegisterRequest, db: Session = Depends(get_db)):
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
@limiter.limit("5/minute")
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

@router.get("/me/avatar", response_model=AvatarResponse)
def get_avatar(
    response: Response,
    current_user: Annotated[User, Depends(get_current_user)],
):
    response.headers["Cache-Control"] = "no-store"

    return AvatarResponse(avatar_url=current_user.avatar_url)

@router.put("/me/avatar", response_model=UserResponse, dependencies=[Depends(require_trusted_origin)])
def update_avatar(response: Response, image: Annotated[UploadFile, File()], current_user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    user_id = current_user.id
    uploaded_avatar = None

    try:
        # Serialize avatar replacements for this user.
        user = db.scalar(
            select(User)
            .where(User.id == user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

        if user is None or not user.is_active:
            raise HTTPException(status_code=401, detail="Please sign in.")

        previous_public_id = user.avatar_public_id

        uploaded_avatar = upload_avatar(image, user_id=user_id)

        user.avatar_url = uploaded_avatar["avatar_url"]
        user.avatar_public_id = uploaded_avatar["avatar_public_id"]

        db.flush()
        db.refresh(user)

        result = UserResponse.model_validate(user)

    except Exception:
        db.rollback()

        if uploaded_avatar is not None:
            try:
                delete_avatar(uploaded_avatar["avatar_public_id"])
            except Exception:
                logger.exception(
                    "Failed to clean up new avatar %s",
                    uploaded_avatar["avatar_public_id"],
                )
        raise

    try:
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()

        logger.exception(
            "Avatar commit failed for user %s; check asset %s",
            user_id,
            uploaded_avatar["avatar_public_id"],
        )

        raise HTTPException(
            status_code=503,
            detail="Could not confirm that the avatar was saved.",
        ) from error

    # Delete the previous image only after the new reference has committed.
    if previous_public_id:
        try:
            delete_avatar(previous_public_id)
        except Exception:
            logger.exception(
                "Failed to delete previous avatar %s for user %s",
                previous_public_id,
                user_id,
            )

    response.headers["Cache-Control"] = "no-store"
    return result