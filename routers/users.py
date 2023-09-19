from fastapi import APIRouter, Depends, HTTPException, Form
from libs.config.settings import get_settings
from models.users import *
from libs.db import _db, Collections
from libs.utils.pure_functions import *
from libs.utils.security import scrypt_hash
from libs.utils.api_helpers import update_record, find_record, _validate_email_from_db, _validate_phone_from_db
from libs.huey_tasks.tasks import task_send_mail
from libs.utils.security import generate_totp, validate_totp, encode_to_base64, scrypt_verify, _create_access_token
from libs.deps.users import get_user_by_email, get_auth_context
from fastapi.security import OAuth2PasswordRequestForm


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
        raise HTTPException(400, "Invalid Code")

    user.email_verified = True
    user.is_active = True

    await update_record(UserDBModel, user.model_dump(), Collections.users, "uid")


@router.post("/sign-in", response_model=AccessToken)
async def sign_in(body:  OAuth2PasswordRequestForm = Depends()):

    user:  UserDBModel = await find_record(UserDBModel, Collections.users, "email", body.username, raise_404=False)

    if user is None:
        raise HTTPException(401, "Account does not exist.")

    if not user.email_verified:
        raise HTTPException(
            400, "Account not verified, please verify your email.", headers={"WWW-Authenticate": "Bearer", "X-ACTION": "VERIFY_EMAIL"})

    if not user.is_active:
        raise HTTPException(
            400, "Account is not active, please contact support.",  headers={"WWW-Authenticate": "Bearer", "X-ACTION": "VERIFY_EMAIL"})

    is_correct_password = scrypt_verify(
        body.password, user.password_hash, user.uid)

    if not is_correct_password:
        raise HTTPException(401, "Invalid Credentials. ")

    user.last_login = user.true_last_login
    user.true_last_login = get_utc_timestamp()

    # Create new auth session

    token = await _create_access_token(user.uid)

    await update_record(UserDBModel, user.model_dump(), Collections.users, "uid")

    return {
        "access_token": token,
    }


@router.get("/session", response_model=AuthenticationContext, response_model_by_alias=True)
async def get_session(ctx:  AuthenticationContext = Depends(get_auth_context)):
    return ctx
