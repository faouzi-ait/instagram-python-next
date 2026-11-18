from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Post(Base):
    __tablename__ = "posts"

    __table_args__ = (
        CheckConstraint(
            "visibility IN ('public', 'private')",
            name="ck_posts_visibility",
        ),
        CheckConstraint(
            "image_width > 0 AND image_height > 0",
            name="ck_posts_image_dimensions",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )

    caption: Mapped[str | None] = mapped_column(Text)

    visibility: Mapped[str] = mapped_column(
        String(20),
        server_default="public",
    )

    image_public_id: Mapped[str] = mapped_column(Text, unique=True)
    image_width: Mapped[int] = mapped_column()
    image_height: Mapped[int] = mapped_column()

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
