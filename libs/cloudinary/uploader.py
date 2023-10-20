from libs.config.settings import get_settings
from libs.logging import Logger
from fastapi import HTTPException
import cloudinary
import cloudinary.uploader
import cloudinary.api

logger = Logger(f"{__package__}.{__name__}")

settings = get_settings()


config = cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name, api_key=settings.cloudinary_api_key, api_secret=settings.cloudinary_api_secret,  secure=True)


def upload_image(image, options):
    try:
        res = cloudinary.uploader.upload(image, **options)

        result = {
            "url": res["url"],
            "public_id": res["public_id"],
            "secure_url": res["secure_url"]
        }

        return result

    except Exception as e:

        if settings.debug:
            logger.critical("Cloudinary upload error")
            print(e)

        raise HTTPException(
            500, "An error occured while trying to upload resource.")
