from datetime import datetime
from schemas.comment import CommentCreate, CommentResponse, CommentUpdate

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base

class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (
        CheckConstraint(
            "char_length(trim(content)) > 0",
            name="ck_comments_content_not_empty",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"),
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )

    content: Mapped[str] = mapped_column(String(2200))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )