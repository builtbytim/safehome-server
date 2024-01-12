from fastapi import APIRouter, HTTPException
from libs.config.settings import get_settings
from models.misc import *
from libs.db import _db, Collections
from libs.utils.api_helpers import find_record
from libs.utils.pure_functions import *
from libs.huey_tasks.tasks import task_send_mail
from libs.utils.security import generate_totp, validate_totp
from models.users import ActionIdentifiers


settings = get_settings()


router = APIRouter(responses={
    404: {"description": "The resource you requested does not exist!"}
}, tags=["Miscellaneous"])


@router.post("/waitlist/confirm", status_code=200)
async def confirm_waitlist_email(body:  WaitlistEmailConfirmationInput):

    otp, uid = await generate_totp(ActionIdentifiers.WAITLIST_EMAIL_CONFIRMATION, body.email)

    # Check if email already exists

    if await find_record(WaitlistApplication, Collections.waitlist_applications, "email", body.email, raise_404=False):
        raise HTTPException(
            status_code=400, detail="You have already applied for the waitlist with this email!")

    # Send email to applicant

    task_send_mail("waitlist_email_confirmation", body.email,
                   {"otp": otp, "uid": uid})

    return {
        "uid": uid,
    }


@router.post("/waitlist", status_code=201)
async def add_waitlist_applicant(body:  WaitlistApplicationInput):

    # Validate OTP

    totp_obj, _ = await validate_totp(body.uid)

    is_valid = totp_obj.verify(body.code)

    if not is_valid:
        raise HTTPException(400, "Invalid Code, please try again!")

    # Check if email already exists
    if await find_record(WaitlistApplication, Collections.waitlist_applications, "email", body.email, raise_404=False):
        raise HTTPException(
            status_code=400, detail="You have already applied for the waitlist with this email!")

    # Check if phone already exists
    if await find_record(WaitlistApplication, Collections.waitlist_applications, "phone", body.phone, raise_404=False):
        raise HTTPException(
            status_code=400, detail="You have already applied for the waitlist with this phone number!")

    application = WaitlistApplication(**body.model_dump())

    await _db[Collections.waitlist_applications].insert_one(application.model_dump())

    # Send email to applicant

    task_send_mail("joined_waitlist", application.email,
                   {"full_name":  application.full_name})

    return {"message": "Application submitted successfully!"}
