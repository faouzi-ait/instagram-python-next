import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database import get_db
from dependencies.auth import get_current_user, require_trusted_origin
from models.follow import Follow
from models.users import User
from rate_limit import limiter
from schemas.follow import (
    FollowRequestResponse,
    FollowResponse,
    FollowStatusResponse,
    FollowUserResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/users",
    tags=["Follows"],
)


def get_follow_target(db: Session, user_id: int) -> User:
    target = db.scalar(
        select(User)
        .where(User.id == user_id, User.is_active.is_(True))
        .with_for_update()
    )
    if target is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return target


@router.put(
    "/{user_id}/follow",
    response_model=FollowResponse,
    dependencies=[Depends(require_trusted_origin)],
)
@limiter.limit("30/minute")
def follow_user(
    request: Request,
    response: Response,
    user_id: Annotated[int, Path(gt=0)],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="You cannot follow yourself.")

    try:
        target = get_follow_target(db, user_id)
        initial_status = "pending" if target.is_private else "accepted"

        statement = (
            insert(Follow)
            .values(follower_id=user.id, following_id=target.id, status=initial_status)
            .on_conflict_do_nothing(
                index_elements=[Follow.follower_id, Follow.following_id]
            )
        )

        db.execute(statement)

        # Return the existing status if this relationship was already present.
        status = db.scalar(
            select(Follow.status).where(
                Follow.follower_id == user.id,
                Follow.following_id == target.id,
            )
        )

        result = FollowResponse(user_id=target.id, status=status)
        db.commit()

    except SQLAlchemyError as error:
        db.rollback()
        logger.exception("Could not confirm follow of user %s", user_id)

        raise HTTPException(
            status_code=503, detail="Could not confirm the follow request."
        ) from error

    response.headers["Cache-Control"] = "no-store"
    return result


@router.delete(
    "/{user_id}/follow",
    status_code=204,
    response_class=Response,
    dependencies=[Depends(require_trusted_origin)],
)
@limiter.limit("30/minute")
def unfollow_user(
    request: Request,
    response: Response,
    user_id: Annotated[int, Path(gt=0)],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="You cannot unfollow yourself.")

    try:
        get_follow_target(db, user_id)
        db.execute(
            delete(Follow).where(
                Follow.follower_id == user.id, Follow.following_id == user_id
            )
        )
        db.commit()

    except SQLAlchemyError as error:
        db.rollback()
        logger.exception("Could not confirm unfollow of user %s", user_id)

        raise HTTPException(
            status_code=503, detail="Could not confirm the unfollow request."
        ) from error

    response.status_code = 204
    response.headers["Cache-Control"] = "no-store"

    return response


@router.put(
    "/me/follow-requests/{follower_id}/accept",
    status_code=204,
    response_class=Response,
    dependencies=[Depends(require_trusted_origin)],
)
@limiter.limit("30/minute")
def accept_follow_request(
    request: Request,
    response: Response,
    follower_id: Annotated[int, Path(gt=0)],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        # Lock the receiving account, as follow/unfollow already do.
        get_follow_target(db, user.id)

        follow = db.scalar(
            select(Follow)
            .where(Follow.follower_id == follower_id, Follow.following_id == user.id)
            .with_for_update()
        )

        if follow is None:
            raise HTTPException(status_code=404, detail="Follow request not found.")

        # Repeating acceptance is safe.
        follow.status = "accepted"
        db.commit()

    except SQLAlchemyError as error:
        db.rollback()
        logger.exception(
            "Could not confirm acceptance of follow request from %s to %s",
            follower_id,
            user.id,
        )

        raise HTTPException(
            status_code=503, detail="Could not confirm acceptance of the request."
        ) from error

    response.status_code = 204
    response.headers["Cache-Control"] = "no-store"

    return response


@router.delete(
    "/me/follow-requests/{follower_id}",
    status_code=204,
    response_class=Response,
    dependencies=[Depends(require_trusted_origin)],
)
@limiter.limit("30/minute")
def reject_follow_request(
    request: Request,
    response: Response,
    follower_id: Annotated[int, Path(gt=0)],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        get_follow_target(db, user.id)

        follow = db.scalar(
            select(Follow)
            .where(Follow.follower_id == follower_id, Follow.following_id == user.id)
            .with_for_update()
        )

        if follow is not None:
            if follow.status != "pending":
                raise HTTPException(
                    status_code=409, detail="This user is already an accepted follower."
                )
            db.delete(follow)

        # Already rejected or cancelled requests also return 204.
        db.commit()

    except SQLAlchemyError as error:
        db.rollback()
        logger.exception(
            "Could not confirm rejection of follow request from %s to %s",
            follower_id,
            user.id,
        )
        raise HTTPException(
            status_code=503, detail="Could not confirm rejection of the request."
        ) from error

    response.status_code = 204
    response.headers["Cache-Control"] = "no-store"

    return response


@router.get("/me/follow-requests", response_model=list[FollowRequestResponse])
def list_follow_requests(
    response: Response,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    statement = (
        select(
            User.id.label("follower_id"),
            User.username,
            User.display_name,
            User.avatar_url,
            Follow.created_at,
        )
        .join(Follow, Follow.follower_id == User.id)
        .where(
            Follow.following_id == user.id,
            Follow.status == "pending",
            User.is_active.is_(True),
        )
        .order_by(Follow.created_at.desc(), Follow.follower_id.desc())
        .limit(limit)
        .offset(offset)
    )

    requests = db.execute(statement).mappings().all()
    response.headers["Cache-Control"] = "no-store"

    return [FollowRequestResponse.model_validate(item) for item in requests]


@router.get("/{user_id}/follow-status", response_model=FollowStatusResponse)
def get_follow_status(
    response: Response,
    user_id: Annotated[int, Path(gt=0)],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    target = db.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))

    if target is None:
        raise HTTPException(status_code=404, detail="User not found.")

    is_self = target.id == user.id
    status = "none"

    if not is_self:
        follow = db.get(Follow, (user.id, target.id))

        if follow is not None:
            status = follow.status

    response.headers["Cache-Control"] = "no-store"

    return FollowStatusResponse(
        user_id=target.id,
        status=status,
        is_self=is_self,
    )


@router.get("/{user_id}/followers", response_model=list[FollowUserResponse])
def list_followers(
    response: Response,
    user_id: Annotated[int, Path(gt=0)],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    target = db.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))

    if target is None:
        raise HTTPException(status_code=404, detail="User not found.")

    # Private lists require ownership or an accepted follow.
    if target.is_private and target.id != user.id:
        relationship = db.get(Follow, (user.id, target.id))

        if relationship is None or relationship.status != "accepted":
            raise HTTPException(status_code=404, detail="User not found.")

    statement = (
        select(User)
        .join(Follow, Follow.follower_id == User.id)
        .where(
            Follow.following_id == target.id,
            Follow.status == "accepted",
            User.is_active.is_(True),
        )
        .order_by(Follow.created_at.desc(), User.id.desc())
        .limit(limit)
        .offset(offset)
    )

    followers = db.scalars(statement).all()
    response.headers["Cache-Control"] = "no-store"

    return followers


@router.get("/{user_id}/following", response_model=list[FollowUserResponse])
def list_following(
    response: Response,
    user_id: Annotated[int, Path(gt=0)],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    target = db.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))

    if target is None:
        raise HTTPException(status_code=404, detail="User not found.")

    # Private lists require ownership or an accepted follow.
    if target.is_private and target.id != user.id:
        relationship = db.get(Follow, (user.id, target.id))

        if relationship is None or relationship.status != "accepted":
            raise HTTPException(status_code=404, detail="User not found.")

    statement = (
        select(User)
        .join(Follow, Follow.following_id == User.id)
        .where(
            Follow.follower_id == target.id,
            Follow.status == "accepted",
            User.is_active.is_(True),
        )
        .order_by(Follow.created_at.desc(), User.id.desc())
        .limit(limit)
        .offset(offset)
    )

    following = db.scalars(statement).all()
    response.headers["Cache-Control"] = "no-store"

    return following
