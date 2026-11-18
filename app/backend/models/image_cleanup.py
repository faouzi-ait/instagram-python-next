from datetime import datetime

from sqlalchemy import DateTime, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class ImageCleanupTask(Base):
    __tablename__ = "image_cleanup_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)

    image_public_id: Mapped[str] = mapped_column(
        Text,
        unique=True,
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )

    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
