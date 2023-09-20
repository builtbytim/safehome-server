from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from libs.config.settings import get_settings
from models.uploads import *
from libs.utils.pure_functions import *
from models.users import AuthenticationContext
from libs.utils.security import scrypt_hash
from libs.utils.api_helpers import update_record, find_record, _validate_email_from_db, _validate_phone_from_db
from libs.deps.users import get_user_by_email, get_auth_context_optionally
from libs.cloudinary.uploader import upload_image


settings = get_settings()


router = APIRouter(responses={
    404: {"description": "The resource you requested does not exist!"}
}, tags=["Media Uploads"])


@router.post("/images", status_code=201, response_model=UploadImageOutput)
async def upload_image_to_cloudinary(
    file: UploadFile = File(...),
    auth_context: AuthenticationContext | None = Depends(get_auth_context_optionally), folder_id: str | None = Query(default_factory=get_uuid4)
):

    if file.content_type not in settings.allowed_image_content_types:
        raise HTTPException(400, "invalid image content type")

    if auth_context:
        file_group = auth_context.user.uid
    else:
        file_group = folder_id

    result = upload_image(file.file, {
        "folder": f"{settings.images_dir}/{file_group}"
    })

    return UploadImageOutput(**result)
