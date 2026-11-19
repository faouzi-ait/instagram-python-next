import logging
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    Request,
    Response,
)
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database import get_db
from dependencies.auth import get_current_user, require_trusted_origin
from models.post import Post
from models.post_like import PostLike
from models.users import User
from rate_limit import limiter
from routes.posts import get_optional_user, visible_posts_condition
from schemas.post_like import PostLikesResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/posts", tags=["Likes"])


def accessible_post_query(post_id: int, user: User | None):
    return select(Post).where(
        Post.id == post_id,
        visible_posts_condition(user),
    )


@router.put(
    "/{post_id}/like",
    status_code=204,
    response_class=Response,
    dependencies=[Depends(require_trusted_origin)],
)
@limiter.limit("60/minute")
def like_post(
    request: Request,
    response: Response,
    post_id: Annotated[int, Path(gt=0)],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    post = db.scalar(accessible_post_query(post_id, user).with_for_update())

    if post is None:
        raise HTTPException(status_code=404, detail="Post not found.")

    try:
        db.execute(
            insert(PostLike)
            .values(post_id=post_id, user_id=user.id)
            .on_conflict_do_nothing(
                index_elements=["post_id", "user_id"],
            )
        )
        db.commit()

    except SQLAlchemyError as error:
        db.rollback()
        logger.exception("Failed to like post %s", post_id)

        raise HTTPException(
            status_code=503,
            detail="Could not confirm that the like was saved.",
        ) from error

    response.status_code = 204
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/{post_id}/likes", response_model=PostLikesResponse)
def get_post_likes(
    response: Response,
    post_id: Annotated[int, Path(gt=0)],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_optional_user)],
):
    post = db.scalar(accessible_post_query(post_id, user))

    if post is None:
        raise HTTPException(status_code=404, detail="Post not found.")

    likes_count = db.scalar(
        select(func.count()).select_from(PostLike).where(PostLike.post_id == post_id)
    )

    liked_by_me = False

    if user is not None:
        liked_by_me = (
            db.get(
                PostLike,
                (post_id, user.id),
            )
            is not None
        )

    response.headers["Cache-Control"] = "no-store"

    return PostLikesResponse(
        post_id=post_id,
        likes_count=likes_count,
        liked_by_me=liked_by_me,
    )


@router.delete(
    "/{post_id}/like",
    status_code=204,
    response_class=Response,
    dependencies=[Depends(require_trusted_origin)],
)
@limiter.limit("60/minute")
def unlike_post(
    request: Request,
    response: Response,
    post_id: Annotated[int, Path(gt=0)],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    post = db.scalar(accessible_post_query(post_id, user).with_for_update())

    if post is None:
        raise HTTPException(status_code=404, detail="Post not found.")

    try:
        db.execute(
            delete(PostLike).where(
                PostLike.post_id == post_id,
                PostLike.user_id == user.id,
            )
        )
        db.commit()

    except SQLAlchemyError as error:
        db.rollback()
        logger.exception("Failed to unlike post %s", post_id)

        raise HTTPException(
            status_code=503,
            detail="Could not confirm that the like was removed.",
        ) from error

    response.status_code = 204
    response.headers["Cache-Control"] = "no-store"
    return response
