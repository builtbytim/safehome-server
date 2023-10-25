from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File, Response
from libs.config.settings import get_settings
from models.users import *
from libs.db import _db, Collections
from libs.utils.pure_functions import *
from libs.utils.security import scrypt_hash
from libs.utils.api_helpers import update_record, find_record, _validate_email_from_db, _validate_phone_from_db
from libs.huey_tasks.tasks import task_send_mail, task_initiate_kyc_verification, task_post_user_registration, task_create_notification
from models.notifications import NotificationTypes
from libs.utils.security import generate_totp, validate_totp, encode_to_base64, scrypt_verify, _create_access_token
from libs.deps.users import get_auth_context, get_auth_code, only_paid_users
from fastapi.security import OAuth2PasswordRequestForm
from libs.utils.security import encrypt
from libs.cloudinary.uploader import upload_image


settings = get_settings()


router = APIRouter(responses={
    404: {"description": "The resource you requested does not exist!"}
}, tags=["Users"], )


@router.post("",  response_model=UserDBModel, response_model_by_alias=True, response_model_exclude=USER_EXLUCUDE_FIELDS)
async def user_sign_up(response:  Response, body:  UserInputModel):

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

    # Queue additinonal tasks

    task_post_user_registration(user_db.uid)

    # create verify email auth code

    verify_email_auth_code = AuthCode(
        user_id=user_db.uid, action=ActionIdentifiers.VERIFY_EMAIL, )

    await _db[Collections.authcodes].insert_one(verify_email_auth_code.model_dump())

    response.headers["X-AUTH-CODE"] = verify_email_auth_code.code

    return user_db


@router.put("",  response_model=UserDBModel, response_model_by_alias=True, response_model_exclude=USER_EXLUCUDE_FIELDS)
async def update_user(body:  UserUpdateModel, paid_membership_fee: bool = Depends(only_paid_users), auth_context:  AuthenticationContext = Depends(get_auth_context)):

    user:  UserOutputModel = auth_context.user

    if get_utc_timestamp() - user.profile_updated_at < (60 * 2):
        raise HTTPException(
            400, "Profile was updated recently, please try again later")

    if user.kyc_status == KYCStatus.PENDING:
        raise HTTPException(400, "KYC is pending, please contact support.")

    if user.kyc_status == KYCStatus.APPROVED:
        raise HTTPException(
            400, "KYC is approved, you cannot update your details.")

    # update the user object

    user.first_name = body.first_name
    user.last_name = body.last_name
    user.phone = body.phone

    if body.gender:
        user.gender = body.gender
    if body.date_of_birth:
        user.date_of_birth = body.date_of_birth

    user.kyc_info.residential_address = body.residential_address
    user.kyc_info.state = body.state
    user.address = body.residential_address
    user.state = body.state

    user.profile_updated_at = get_utc_timestamp()

    updated_user = await update_record(UserDBModel, user.model_dump(), Collections.users, "uid", refresh_from_db=True)

    task_create_notification(
        user.uid, NotificationTypes.account, "Profile Updated", f"You updated your profile", )

    return updated_user


@router.post("/emails/verify", status_code=200, response_model=RequestEmailOrSMSVerificationOutput)
async def email_verify(body: RequestEmailOrSMSVerificationInput, auth_code:  AuthCode = Depends(get_auth_code)):

    v = auth_code.verify_action(ActionIdentifiers.VERIFY_EMAIL)

    if not v:
        raise HTTPException(400, "Invalid Auth Code")

    user: UserDBModel = await find_record(UserDBModel, Collections.users, "email", body.email, raise_404=True)

    if user.uid != auth_code.user_id:
        raise HTTPException(400, "Invalid Auth Code")

    if user.email_verified:
        raise HTTPException(400, "email already verified")

    otp, uid = await generate_totp(ActionIdentifiers.VERIFY_EMAIL, user.uid)

    # send email

    url = f"{settings.app_url}/verify-email/{user.email}?uid={uid}&token={encode_to_base64(otp)}&authCode={auth_code.code}"

    task_send_mail(
        "verify_email", user.email, {"otp": otp, "url": url})

    if settings.debug:
        print("URL:", url, "OTP:", otp)

    return RequestEmailOrSMSVerificationOutput(uid=uid, channel=Channels.EMAIL, pk=user.email)


@router.post("/emails/confirm", status_code=200, response_model=AuthCode)
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

    kyc_doc_auth_code = AuthCode(
        user_id=user.uid, action=ActionIdentifiers.ADD_KYC_INFO, )

    await _db[Collections.authcodes].insert_one(kyc_doc_auth_code.model_dump())

    # send email

    url = f"{settings.app_url}/kyc?uid={user.uid}&authCode={kyc_doc_auth_code.code}"

    task_send_mail(
        "verify_email_done", user.email, {"url": url})

    return kyc_doc_auth_code


@router.post("/sign-in", response_model=AccessToken)
async def sign_in(body:  OAuth2PasswordRequestForm = Depends()):

    user:  UserDBModel = await find_record(UserDBModel, Collections.users, "email", body.username.lower(), raise_404=False)

    if user is None:
        raise HTTPException(
            404, "We could not find an account with that email.")

    auth_code = AuthCode(
        user_id=user.uid, action=ActionIdentifiers.AUTHENTICATION, )

    email_auth_code = AuthCode(
        user_id=user.uid, action=ActionIdentifiers.VERIFY_EMAIL, )

    await _db[Collections.authcodes].insert_one(auth_code.model_dump())
    await _db[Collections.authcodes].insert_one(email_auth_code.model_dump())

    if not user.email_verified:
        raise HTTPException(
            400, "Account is not verified yet, please verify your email.", headers={"WWW-Authenticate": "Bearer", "X-ACTION": "VERIFY_EMAIL", "X-AUTH-CODE": email_auth_code.code})

    if not user.is_active:
        raise HTTPException(
            400, "Account is  inactive, please contact support.",  headers={"WWW-Authenticate": "Bearer", "X-ACTION": "VERIFY_EMAIL", "X-AUTH-CODE": email_auth_code.code})

    is_correct_password = scrypt_verify(
        body.password, user.password_hash, user.uid)

    if not is_correct_password:
        raise HTTPException(401, "Invalid Credentials. ")

    user.last_login = user.true_last_login
    user.true_last_login = get_utc_timestamp()

    # Create new auth session

    token = await _create_access_token(user.uid)

    await update_record(UserDBModel, user.model_dump(), Collections.users, "uid")

    # send email

    task_send_mail(
        "sign_in_notification", user.email, {"support_email": settings.support_email})

    return {
        "access_token": token,
    }


@router.get("/session", response_model=AuthenticationContext, response_model_by_alias=True)
async def get_session(auth_context:  AuthenticationContext = Depends(get_auth_context)):
    return AuthenticationContext(
        user=UserOutputModel(**auth_context.get_user_dict()),
        session=auth_context.session,
    )


@router.post("/sign-out", status_code=200)
async def sign_out(auth_context:  AuthenticationContext = Depends(get_auth_context)):

    auth_context.session.is_valid = False

    await update_record(AuthSession, auth_context.session.model_dump(), Collections.authsessions, "uid")

    # await update_record(UserDBModel, auth_context.user.model_dump(), Collections.users, "uid")


@router.post("/password/change", status_code=200)
async def change_password(body:  PasswordChangeInput,  paid_membership_fee: bool = Depends(only_paid_users), auth_context:  AuthenticationContext = Depends(get_auth_context)):

    user:  UserDBModel = find_record(
        UserDBModel, Collections.users, "uid", auth_context.user.uid, raise_404=True)

    if get_utc_timestamp() - user.password_changed_at < (60 * 5):
        raise HTTPException(
            400, "Password was changed recently, please try again later")

    err1, input_current_password_hash = scrypt_hash(
        body.current_password, user.uid)

    if err1:
        raise HTTPException(500, str(err1))

    if user.password_hash != input_current_password_hash:
        raise HTTPException(
            400, "The current password you entered is incorrect")

    err2, input_new_password_hash = scrypt_hash(body.new_password, user.uid)

    if err2:
        raise HTTPException(500, str(err2))

    if input_new_password_hash == user.password_hash:
        raise HTTPException(
            400, "New password cannot be the same as old password")

    user.password_hash = input_new_password_hash

    user.password_changed_at = get_utc_timestamp()

    await update_record(UserDBModel, user.model_dump(), Collections.users, "uid")

    # invalidate all user sessions

    await _db[Collections.authsessions].update_many({"user_id": user.uid}, {"$set": {"is_valid": False}})

    task_create_notification(
        user.uid, NotificationTypes.security, "Password Changed", f"You recently changed your password")

    # send email

    task_send_mail(
        "password_changed", user.email, {"first_name": user.first_name, "support_email":  settings.support_email, "reset_link": f"{settings.app_url}/password/reset"})


@router.post("/password/reset", status_code=200)
async def password_reset(body:  RequestPasswordResetInput):

    user: UserDBModel = await find_record(UserDBModel, Collections.users, "email", body.email, raise_404=False)

    # ignore the reset request of the user does not exist
    if user is None:
        return

    if not user.email_verified:
        raise HTTPException(
            400, "Account is not verified, please verify your email.")

    if not user.is_active:
        raise HTTPException(
            400, "Account is not active, please contact support.")

    if not user.kyc_status == KYCStatus.APPROVED:
        raise HTTPException(
            400, "Your KYC has not been approved, please contact support.")

    if get_utc_timestamp() - user.password_reset_at < (60 * 2):
        raise HTTPException(
            400, "Password was recovered recently, please try again later")

    err, hash = scrypt_hash(body.new_password, user.uid)

    if err:
        raise HTTPException(500, str(err))

    reset_store = PasswordResetStore(
        user_id=user.uid, new_password_hash=hash, channel=Channels.EMAIL,
    )

    # save store to db
    await _db[Collections.passwordresetstores].insert_one(reset_store.model_dump())

    token = reset_store.token

    # send email

    url = f"{settings.app_url}/password/save?uid={user.uid}&token={token}"

    task_send_mail(
        "reset_password", user.email, {"url": url, "first_name": user.first_name})

    if settings.debug:
        print("URL:", url, )


@router.post("/password/confirm-reset", status_code=200)
async def password_save(body:  PasswordResetSaveInput):

    user: UserDBModel = await find_record(UserDBModel, Collections.users, "uid", body.uid, raise_404=False)

    if user is None:
        raise HTTPException(400, "Reset token does not exist in the system")

    if not user.email_verified:
        raise HTTPException(
            400, "You have not verified your email, please verify your email.")

    if not user.is_active:
        raise HTTPException(
            400, "Your account is not active, please contact support.")

    if not user.kyc_status == KYCStatus.APPROVED:
        raise HTTPException(
            400, "Your KYC has not been approved, please contact support.")

    reset_store: PasswordResetStore | None = await find_record(PasswordResetStore, Collections.passwordresetstores, "token", body.token, raise_404=False)

    if reset_store is None:
        raise HTTPException(400, "Reset token does not exist in the system")

    if get_utc_timestamp() - user.password_reset_at < (60 * 5):
        raise HTTPException(
            400, "Password was recovered recently, please try again later")

    if reset_store.user_id != user.uid:
        raise HTTPException(400, "The reset token is not for this user")

    if not reset_store.valid:
        raise HTTPException(400, "The reset token is not valid")

    if get_utc_timestamp() > reset_store.created_at + (60 * 10):
        raise HTTPException(400, "The reset token has expired")

    user.password_hash = reset_store.new_password_hash
    user.password_reset_at = get_utc_timestamp()

    await update_record(UserDBModel, user.model_dump(), Collections.users, "uid")

    await _db[Collections.passwordresetstores].delete_one({"user_id": user.uid, "token": body.token})

    task_send_mail(
        "reset_password_done", user.email, {"first_name": user.first_name, "support_email":  settings.support_email})


@router.post("/avatar", status_code=200, )
async def avatar_upload(paid_membership_fee: bool = Depends(only_paid_users), avatar: UploadFile = File(...),   auth_context: AuthenticationContext = Depends(get_auth_context)):

    user = auth_context.user

    upload_res = upload_image(avatar.file, {
        "folder": f"{settings.images_dir}/{user.uid}"
    })

    user.avatar_url = upload_res["secure_url"]

    await update_record(UserDBModel, user.model_dump(), Collections.users, "uid")


@router.get("/next-of-kin", status_code=200, response_model=NextOfKinInfo | None)
async def get_next_of_kin(paid_membership_fee: bool = Depends(only_paid_users), auth_context:  AuthenticationContext = Depends(get_auth_context)):

    user: UserDBModel = auth_context.user

    next_of_kin = await _db[Collections.next_of_kins].find_one({"user_id": user.uid})

    return next_of_kin


@router.post("/next-of-kin", status_code=200)
async def set_next_of_kin(body:  NextOfKinInput,  paid_membership_fee: bool = Depends(only_paid_users), auth_context:  AuthenticationContext = Depends(get_auth_context)):
    user: UserDBModel = auth_context.user

    next_of_kin = NextOfKinInfo(**body.model_dump(), user_id=user.uid)

    # attempt for fetch an existing next of kin for user

    existing_next_of_kin = await _db[Collections.next_of_kins].find_one({"user_id": user.uid})

    if not existing_next_of_kin:
        await _db[Collections.next_of_kins].insert_one(next_of_kin.model_dump())
        # send a notification
        task_create_notification(
            user.uid, NotificationTypes.account, "Next of Kin Added", f"You added a next of kin", )
        return

    if body.replace:
        # send a notification

        task_create_notification(
            user.uid, NotificationTypes.account, "Next of Kin Updated", f"You  updated your next of kin")

        await _db[Collections.next_of_kins].update_one(
            {"user_id": user.uid}, {"$set": next_of_kin.model_dump()})
        return

    raise HTTPException(400, "Failed, you have already set your next of kin.")


@router.post("/security-questions", status_code=200)
async def set_security_questions(body:  UserSecurityQuestionsInput,  paid_membership_fee: bool = Depends(only_paid_users), auth_context:  AuthenticationContext = Depends(get_auth_context)):
    user: UserDBModel = auth_context.user

    input_data = UserSecurityQuestions(question1=body.question1, question2=body.question2, answer1=encrypt(
        body.answer1.encode()).hex(), answer2=encrypt(body.answer2.encode()).hex())

    if body.replace:
        # send a notification

        task_create_notification(
            user.uid,  NotificationTypes.account, "Security Questions Updated", f"You updated your security questions")

        user.security_questions = input_data

    elif user.security_questions is None:
        # send a notification

        task_create_notification(
            user.uid, NotificationTypes.account, "Security Questions Added", f"You have added security questions")

        user.security_questions = input_data

    else:
        raise HTTPException(
            400, "Failed, you have already set your security questions.")

    await update_record(UserDBModel, user.model_dump(), Collections.users, "uid")


@router.post("/kyc", status_code=200)
async def add_kyc_info(body:  KYCVerificationInput,  paid_membership_fee: bool = Depends(only_paid_users), auth_context:  AuthenticationContext = Depends(get_auth_context)):

    user: UserDBModel = auth_context.user

    if user.kyc_status == KYCStatus.APPROVED:
        raise HTTPException(400, "Your KYC is already approved.")

    if user.kyc_status == KYCStatus.PENDING:
        raise HTTPException(
            400, "You already have a pending KYC submission.")

    kyc_info = UserKYCInfo(
        residential_address=body.residential_address,
        state=body.state,
        document_type=body.document_type,
        BVN=body.BVN,
        IDNumber=body.IDNumber
    )

    kyc_info.IDNumber = encrypt(body.IDNumber.encode()).hex()

    kyc_info.BVN = encrypt(body.BVN.encode()).hex()

    user.kyc_info = kyc_info

    await update_record(UserDBModel, user.model_dump(), Collections.users, "uid")


@router.post("/kyc/upload", status_code=200, )
async def kyc_doc_upload(file: UploadFile = File(...),  paid_membership_fee: bool = Depends(only_paid_users),   auth_context:  AuthenticationContext = Depends(get_auth_context)):

    user = auth_context.user

    if user.kyc_status == KYCStatus.APPROVED:
        raise HTTPException(400, "Your KYC is already approved.")

    if user.kyc_status == KYCStatus.PENDING:
        raise HTTPException(
            400, "You already have a pending KYC submission.")

    if user.kyc_info is None:
        raise HTTPException(
            400, "You have not submitted your KYC information.")

    # check if kyc info has been uploaded before here
    if (user.kyc_info.BVN is None) or (user.kyc_info.IDNumber is None) or (user.kyc_info.document_type is None) or (user.kyc_info.state is None) or (user.kyc_info.residential_address is None):
        raise HTTPException(
            400, "You have not submitted your KYC information.")

    upload_res = upload_image(file.file, {
        "folder": f"{settings.images_dir}/{user.uid}"
    })

    user.kyc_info.document_url = encrypt(
        upload_res["secure_url"].encode()).hex()

    user.kyc_status = KYCStatus.PENDING

    user.state = user.kyc_info.state
    user.address = user.kyc_info.residential_address

    await update_record(UserDBModel, user.model_dump(), Collections.users, "uid")

    task_initiate_kyc_verification(user.uid)


"""

@router.post("/kyc/document", status_code=200, response_model=AuthCode, response_model_by_alias=True)
async def kyc_document(document_type:  DocumentTypes = Form(alias='documentType'), document_number:  str | None = Form(default=None, alias="documentNumber"), file: UploadFile = File(...), auth_code: AuthCode = Depends(get_auth_code)):

    v = auth_code.verify_action(ActionIdentifiers.VERIFY_KYC_DOCUMENT)

    if not v:
        raise HTTPException(400, "Invalid Auth Code")

    user: UserDBModel = await find_record(UserDBModel, Collections.users, "uid", auth_code.user_id, raise_404=True)

    if user.kyc_document is not None:
        raise HTTPException(400, "KYC identity document uploaded already")

    upload_res = upload_image(file.file, {
        "folder": f"{settings.images_dir}/{user.uid}"
    })

    doc = IdentityDocument(
        document_type=document_type, document_number=document_number, document_url=upload_res["secure_url"], user_id=user.uid)

    user.kyc_document = doc

    user.kyc_status = KYCStatus.PENDING

    await update_record(UserDBModel, user.model_dump(), Collections.users, "uid")

    kyc_photo_auth_code = AuthCode(
        user_id=user.uid, action=ActionIdentifiers.VERIFY_KYC_PHOTO, )

    await _db[Collections.authcodes].insert_one(kyc_photo_auth_code.model_dump())

    return kyc_photo_auth_code


    """
