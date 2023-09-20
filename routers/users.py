from fastapi import APIRouter, Depends, HTTPException, Form
from libs.config.settings import get_settings
from models.users import *
from libs.db import _db, Collections
from libs.utils.pure_functions import *
from libs.utils.security import scrypt_hash
from libs.utils.api_helpers import update_record, find_record, _validate_email_from_db, _validate_phone_from_db
from libs.huey_tasks.tasks import task_send_mail
from libs.utils.security import generate_totp, validate_totp, encode_to_base64, scrypt_verify, _create_access_token
from pydantic import HttpUrl
from libs.deps.users import get_user_by_email, get_auth_context
from fastapi.security import OAuth2PasswordRequestForm
from libs.cloudinary.uploader import upload_image


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
async def get_session(auth_context:  AuthenticationContext = Depends(get_auth_context)):
    return auth_context


@router.post("/sign-out", status_code=200)
async def sign_out(auth_context:  AuthenticationContext = Depends(get_auth_context)):

    auth_context.session.is_valid = False

    await update_record(AuthSession, auth_context.session.model_dump(), Collections.sessions, "uid")


@router.post("/kyc/id", status_code=200, response_model=IdentityDocument, response_model_by_alias=True)
async def kyc_id(document_type:  DocumentTypes = Form(alias='documentType'), document_number:  str | None = Form(default=None, alias="documentNumber"), file: UploadFile = File(...),  auth_context:  AuthenticationContext = Depends(get_auth_context), ):
    user = auth_context.user

    if user.kyc_id is not None and user.kyc_id_verified:
        raise HTTPException(400, "KYC identity document already verified")

    upload_res = upload_image(file.file, {
        "folder": f"{settings.images_dir}/{user.uid}"
    })

    doc = IdentityDocument(
        document_type=document_type, document_number=document_number, document_url=upload_res["secure_url"], user_id=user.uid)

    user.kyc_id = doc

    await update_record(UserDBModel, user.model_dump(), Collections.users, "uid")

    return doc


@router.post("/kyc/picture", status_code=200, )
async def kyc_picture(file: UploadFile = File(...),  auth_context:  AuthenticationContext = Depends(get_auth_context), ):
    user = auth_context.user

    if user.kyc_picture is not None and user.kyc_picture_verified:
        raise HTTPException(400, "KYC picture already verified")

    upload_res = upload_image(file.file, {
        "folder": f"{settings.images_dir}/{user.uid}"
    })

    user.kyc_picture = HttpUrl(upload_res["secure_url"]).unicode_string()
    user.avatar_url = HttpUrl(upload_res["secure_url"]).unicode_string()

    await update_record(UserDBModel, user.model_dump(), Collections.users, "uid")
