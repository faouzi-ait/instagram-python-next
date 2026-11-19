# Command to run this cleanup script => ./.venv/bin/python cleanup_images.py
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

import models  # noqa: F401
from database import engine
from models.image_cleanup import ImageCleanupTask
from services.images import delete_post_image

logger = logging.getLogger(__name__)


def process_image_cleanup(limit: int = 50) -> None:
    deleted = 0
    failed = 0

    for _ in range(limit):
        with Session(engine) as db:
            with db.begin():
                task = db.scalar(
                    select(ImageCleanupTask)
                    .where(ImageCleanupTask.next_attempt_at <= func.now())
                    .order_by(ImageCleanupTask.next_attempt_at, ImageCleanupTask.id)
                    .with_for_update(skip_locked=True)
                    .limit(1)
                )

                if task is None:
                    break

                try:
                    delete_post_image(task.image_public_id)

                except Exception:
                    task.attempts += 1

                    # with a maximum delay of 60 minutes. Retry after 1, 2, 4, 8... minutes,
                    delay_minutes = min(2 ** min(task.attempts - 1, 6), 60)

                    task.next_attempt_at = datetime.now(timezone.utc) + timedelta(
                        minutes=delay_minutes
                    )
                    logger.exception(
                        "Image cleanup failed for %s; attempt %s",
                        task.image_public_id,
                        task.attempts,
                    )
                    failed += 1

                else:
                    logger.info("Deleted Cloudinary image %s", task.image_public_id)
                    db.delete(task)
                    deleted += 1

    logger.info("Cleanup finished: %s deleted, %s failed", deleted, failed)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    process_image_cleanup()
