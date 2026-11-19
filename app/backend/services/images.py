import io
import time
import warnings
from uuid import uuid4

import cloudinary.uploader
import cloudinary.utils
from cloudinary.exceptions import Error as CloudinaryError
from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

import cloudinary_config  # noqa: F401 — loads your Cloudinary configuration

MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_PIXELS = 20_000_000
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


def upload_post_image(file: UploadFile, user_id: int) -> dict:
    file.file.seek(0)
    contents = file.file.read(MAX_FILE_SIZE + 1)

    if not contents:
        raise HTTPException(status_code=400, detail="The image is empty.")

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="The image must be at most 10 MB.",
        )

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)

            with Image.open(io.BytesIO(contents)) as image:
                if image.format not in ALLOWED_FORMATS:
                    raise HTTPException(
                        status_code=415,
                        detail="Use a JPEG, PNG, or WebP image.",
                    )

                if image.width * image.height > MAX_PIXELS:
                    raise HTTPException(
                        status_code=413,
                        detail="The image must be at most 20 megapixels.",
                    )

                if getattr(image, "n_frames", 1) > 1:
                    raise HTTPException(
                        status_code=415,
                        detail="Animated images are not supported.",
                    )

                image.load()

    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(status_code=413, detail="The image is too large.")
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid image file.")

    public_id = f"posts/{user_id}/{uuid4().hex}"

    try:
        result = cloudinary.uploader.upload(
            io.BytesIO(contents),
            public_id=public_id,
            resource_type="image",
            type="authenticated",
            format="webp",
            overwrite=False,
            timeout=60,
        )
    except CloudinaryError as error:
        raise HTTPException(
            status_code=502,
            detail="Image upload failed. Please try again.",
        ) from error

    return {
        "image_public_id": result["public_id"],
        "image_width": result["width"],
        "image_height": result["height"],
    }


def get_post_image_url(public_id: str) -> str:
    return cloudinary.utils.private_download_url(
        public_id,
        "webp",
        resource_type="image",
        type="authenticated",
        expires_at=int(time.time()) + 300,
        attachment=False,
    )


def delete_post_image(public_id: str) -> None:
    try:
        result = cloudinary.uploader.destroy(
            public_id,
            resource_type="image",
            type="authenticated",
            invalidate=True,
            timeout=60,
        )
    except CloudinaryError as error:
        raise HTTPException(
            status_code=502,
            detail="Image deletion failed. Please try again.",
        ) from error

    if result.get("result") not in {"ok", "not found"}:
        raise HTTPException(
            status_code=502,
            detail="Image deletion could not be confirmed.",
        )
