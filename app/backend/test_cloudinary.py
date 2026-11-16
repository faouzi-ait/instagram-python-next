from pathlib import Path
from starlette.datastructures import UploadFile

from services.images import (
    delete_post_image,
    get_post_image_url,
    upload_post_image,
)

path = Path("/Users/admin/Desktop/IMG_3152.jpg")

with path.open("rb") as image:
    result = upload_post_image(
        UploadFile(file=image, filename=path.name),
        user_id=1,
    )

try:
    print("Uploaded:", result)
    print("Temporary URL:", get_post_image_url(result["image_public_id"]))
    input("Open the URL, then press Enter to delete the test image.")
finally:
    delete_post_image(result["image_public_id"])
    print("Test image deleted.")