from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from libs.config.settings import get_settings
from models.uploads import *
from libs.utils.pure_functions import *
from models.users import AuthenticationContext
from libs.deps.users import get_auth_context
from libs.cloudinary.uploader import upload_image
from libs.logging import Logger


logger = Logger(f"{__package__}.{__name__}")

settings = get_settings()


router = APIRouter(responses={
    404: {"description": "The resource you requested does not exist!"}
}, tags=["Media Uploads"])


@router.post("/images", status_code=201, response_model=UploadImageOutput)
async def upload_image_to_cloudinary(
    file: UploadFile = File(...),
    auth_context: AuthenticationContext | None = Depends(get_auth_context)
):

    if file.content_type not in settings.allowed_image_content_types:
        raise HTTPException(400, "invalid image content type")

    folder_name = f"{settings.images_dir}/{auth_context.user.uid}"

    result = upload_image(file.file, {
        "folder": folder_name
    })

    return UploadImageOutput(**result)
