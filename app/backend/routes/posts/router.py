import logging
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Path,
    Query,
    Request,
    Response,
    UploadFile,
)
from sqlalchemy import or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database import get_db
from dependencies.auth import (
    COOKIE_NAME,
    get_current_user,
    require_trusted_origin,
)
from models.post import Post
from models.users import User
from schemas.post import PostCreate, PostResponse, PostVisibility
from services.images import (
    delete_post_image,
    get_post_image_url,
    upload_post_image,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/posts", tags=["Posts"])

def get_optional_user(request: Request, response: Response, db: Annotated[Session, Depends(get_db)]) -> User | None:
    if not request.cookies.get(COOKIE_NAME):
        return None

    return get_current_user(
        request=request,
        response=response,
        db=db,
    )

def visible_posts_condition(user: User | None):
    if user is None:
        return Post.visibility == "public"

    return or_(
        Post.visibility == "public",
        Post.user_id == user.id,
    )

def build_post_response(post: Post) -> PostResponse:
    return PostResponse(
        id=post.id,
        user_id=post.user_id,
        caption=post.caption,
        visibility=post.visibility,
        image_url=get_post_image_url(post.image_public_id),
        image_width=post.image_width,
        image_height=post.image_height,
        created_at=post.created_at,
        updated_at=post.updated_at,
    )

@router.post("", response_model=PostResponse, status_code=201, dependencies=[Depends(require_trusted_origin)])
def create_post(
    response: Response,
    image: Annotated[UploadFile, File()],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    caption: Annotated[str | None, Form(max_length=2200)] = None,
    visibility: Annotated[PostVisibility, Form()] = "public",
):
    data = PostCreate(caption=caption, visibility=visibility)
    uploaded_image = upload_post_image(image, user_id=user.id)

    try:
        post = Post(
            user_id=user.id,
            caption=data.caption,
            visibility=data.visibility,
            **uploaded_image,
        )

        db.add(post)
        db.flush()
        db.refresh(post)

        result = build_post_response(post)

    except Exception:
        db.rollback()

        try:
            delete_post_image(uploaded_image["image_public_id"])
        except Exception:
            logger.exception(
                "Failed to clean up uploaded image %s",
                uploaded_image["image_public_id"],
            )

        raise

    # Capture the ID before rollback could expire the ORM object's attributes.
    post_id = post.id

    try:
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()

        logger.exception(
            "Post commit failed; check post %s and Cloudinary asset %s",
            post_id,
            uploaded_image["image_public_id"],
        )

        raise HTTPException(
            status_code=503,
            detail="Could not confirm that the post was saved.",
        ) from error

    response.headers["Cache-Control"] = "no-store"
    return result

@router.get("", response_model=list[PostResponse])
def list_posts(
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_optional_user)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    statement = (
        select(Post)
        .where(visible_posts_condition(user))
        .order_by(Post.created_at.desc(), Post.id.desc())
        .limit(limit)
        .offset(offset)
    )

    posts = db.scalars(statement).all()

    response.headers["Cache-Control"] = "no-store"
    return [build_post_response(post) for post in posts]

@router.get("/{post_id}", response_model=PostResponse)
def get_post(
    response: Response,
    post_id: Annotated[int, Path(gt=0)],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_optional_user)],
):
    statement = select(Post).where(
        Post.id == post_id,
        visible_posts_condition(user),
    )

    post = db.scalar(statement)

    if post is None:
        raise HTTPException(
            status_code=404,
            detail="Post not found.",
        )

    response.headers["Cache-Control"] = "no-store"
    return build_post_response(post)