from libs.config.settings import get_settings
import cloudinary
import cloudinary.uploader
import cloudinary.api
import json

settings = get_settings()


config = cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name, api_key=settings.cloudinary_api_key, api_secret=settings.cloudinary_api_secret,  secure=True)


def upload_image(image, options):
    res = cloudinary.uploader.upload(image, **options)

    result = {
        "url": res["url"],
        "public_id": res["public_id"],
        "secure_url": res["secure_url"]
    }

    return result
