import os
from pathlib import Path

import cloudinary
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

cloudinary.config(
    cloud_name=os.environ["CLOUDINARY_NAME"],
    api_key=os.environ["CLOUDINARY_API_KEY"],
    api_secret=os.environ["CLOUDINARY_API_SECRET"],
    secure=True,
)
