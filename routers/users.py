from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.security import OAuth2PasswordRequestForm
from lib.config.settings import get_settings
from models.users import *
from lib.db import _db, Collections
from lib.utils.pure_functions import *
from lib.utils.security import scrypt_hash
from lib.utils.api_helpers import update_record, find_record, _validate_email_from_db, _validate_phone_from_db
from lib.huey_tasks.tasks import task_send_mail
from lib.utils.security import generate_totp, validate_totp, encode_to_base64
import datetime


settings = get_settings()

USER_EXLUCUDE_FIELDS = {"password_hash", "true_last_login",
                        "is_superuser"}


router = APIRouter(responses={
    404: {"description": "The resource you requested does not exist!"}
}, tags=["Users"])


@router.post("", response_model=UserDBModel, response_model_by_alias=True, response_model_exclude=USER_EXLUCUDE_FIELDS)
async def user_sign_up(body:  UserInputModel):

    if not await _validate_email_from_db(body.email):
        raise HTTPException(400, "user with email exists already")

    if not await _validate_phone_from_db(body.phone):
        raise HTTPException(400, "user with phone number exists already")

    user_dict = body.model_dump()

    prospective_id = get_uuid4()

    err, password_hash = scrypt_hash(body.password, prospective_id)

    if err:
        raise HTTPException(500, str(err))

    user_db = UserDBModel(
        **user_dict, uid=prospective_id, password_hash=password_hash
    )

    # save into data base
    await _db[Collections.users].insert_one(user_db.model_dump())

    return user_db


@router.post("/emails/verify", status_code=200, response_model=RequestEmailOrSMSVerificationOutput)
async def email_verify(body: RequestEmailOrSMSVerificationInput):

    user: UserDBModel = await find_record(UserDBModel, Collections.users, "email", body.email, raise_404=True)

    if user.email_verified:
        raise HTTPException(400, "email already verified")

    otp, uid = await generate_totp(ActionIdentifiers.VERIFY_EMAIL, user.uid)

    # send email

    url = f"{settings.app_url}/verify-email/{user.email}?uid={uid}&token={encode_to_base64(otp)}"

    task_send_mail(
        "verify_email", user.email, {"otp": otp, "url": url})

    return RequestEmailOrSMSVerificationOutput(uid=uid, channel=Channels.EMAIL, pk=user.email)


@router.post("/emails/confirm", status_code=200)
async def email_confirm(body: VerifyEmailOrSMSConfirmationInput):

    user: UserDBModel = await find_record(UserDBModel, Collections.users, "email", body.foreign_key, raise_404=True)

    if user.email_verified:
        raise HTTPException(400, "email already verified")

    totp_obj, _ = await validate_totp(body.uid)

    is_valid = totp_obj.verify(body.token)

    if not is_valid:
        raise HTTPException(400, "Invalid Code Detected")

    user.email_verified = True

    await update_record(UserDBModel, user.model_dump(), Collections.users, "uid")
