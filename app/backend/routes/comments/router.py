import logging
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Path, Response, Query
from sqlalchemy import or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database import get_db
from dependencies.auth import get_current_user, require_trusted_origin
from models.comment import Comment
from models.post import Post
from models.users import User
from schemas.comment import CommentCreate, CommentResponse, CommentUpdate
from routes.posts import get_optional_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/comments", tags=["Comments"])

@router.post(
    "/{post_id}/comments",
    response_model=CommentResponse,
    status_code=201,
    dependencies=[Depends(require_trusted_origin)],
)
def create_comment(
    response: Response,
    post_id: Annotated[int, Path(gt=0)],
    data: CommentCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    # Lock the post while checking visibility and saving the comment.
    post = db.scalar(
        select(Post)
        .where(
            Post.id == post_id,
            or_(
                Post.visibility == "public",
                Post.user_id == user.id,
            ),
        )
        .with_for_update()
    )

    if post is None:
        raise HTTPException(status_code=404, detail="Post not found.")

    comment = Comment(post_id=post.id, user_id=user.id, content=data.content)

    try:
        db.add(comment)
        db.flush()
        db.refresh(comment)

        result = CommentResponse.model_validate(comment)

        db.commit()

    except SQLAlchemyError as error:
        db.rollback()
        logger.exception("Failed to save comment on post %s", post_id)

        raise HTTPException(
            status_code=503,
            detail="Could not confirm that the comment was saved.",
        ) from error

    response.headers["Cache-Control"] = "no-store"
    return result

@router.get("/{post_id}/comments", response_model=list[CommentResponse])
def list_comments(
    response: Response,
    post_id: Annotated[int, Path(gt=0)],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_optional_user)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    visibility_condition = Post.visibility == "public"

    if user is not None:
        visibility_condition = or_(
            Post.visibility == "public",
            Post.user_id == user.id,
        )

    post = db.scalar(
        select(Post).where(
            Post.id == post_id,
            visibility_condition,
        )
    )

    if post is None:
        raise HTTPException(status_code=404, detail="Post not found.")

    statement = (
        select(Comment)
        .where(Comment.post_id == post_id)
        .order_by(Comment.created_at.asc(), Comment.id.asc())
        .limit(limit)
        .offset(offset)
    )

    comments = db.scalars(statement).all()

    response.headers["Cache-Control"] = "no-store"
    return comments

@router.patch(
    "/{comment_id}",
    response_model=CommentResponse,
    dependencies=[Depends(require_trusted_origin)],
)
def update_comment(
    response: Response,
    comment_id: Annotated[int, Path(gt=0)],
    data: CommentUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    statement = (
        select(Comment)
        .join(Post, Post.id == Comment.post_id)
        .where(
            Comment.id == comment_id,
            or_(
                Post.visibility == "public",
                Post.user_id == user.id,
            ),
        )
        .with_for_update()
    )

    comment = db.scalar(statement)

    if comment is None:
        raise HTTPException(
            status_code=404,
            detail="Comment not found.",
        )

    if comment.user_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only edit your own comments.",
        )

    try:
        comment.content = data.content

        db.flush()
        db.refresh(comment)

        result = CommentResponse.model_validate(comment)

        db.commit()

    except SQLAlchemyError as error:
        db.rollback()
        logger.exception("Failed to update comment %s", comment_id)

        raise HTTPException(
            status_code=503,
            detail="Could not confirm that the comment was updated.",
        ) from error

    response.headers["Cache-Control"] = "no-store"
    return result

@router.delete(
    "/{comment_id}",
    status_code=204,
    response_class=Response,
    dependencies=[Depends(require_trusted_origin)],
)
def delete_comment(
    response: Response,
    comment_id: Annotated[int, Path(gt=0)],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    statement = (
        select(Comment, Post)
        .join(Post, Post.id == Comment.post_id)
        .where(
            Comment.id == comment_id,
            or_(
                Post.visibility == "public",
                Post.user_id == user.id,
            ),
        )
        .with_for_update()
    )

    row = db.execute(statement).first()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Comment not found.",
        )

    comment, post = row

    if comment.user_id != user.id and post.user_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="You cannot delete this comment.",
        )

    try:
        db.delete(comment)
        db.commit()

    except SQLAlchemyError as error:
        db.rollback()
        logger.exception("Failed to delete comment %s", comment_id)

        raise HTTPException(
            status_code=503,
            detail="Could not confirm that the comment was deleted.",
        ) from error

    response.status_code = 204
    response.headers["Cache-Control"] = "no-store"
    return response