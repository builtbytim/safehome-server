from fastapi import APIRouter, HTTPException
from libs.config.settings import get_settings
from models.misc import *
from libs.db import _db, Collections
from libs.utils.api_helpers import find_record
from libs.utils.pure_functions import *
from libs.huey_tasks.tasks import task_send_mail


settings = get_settings()


router = APIRouter(responses={
    404: {"description": "The resource you requested does not exist!"}
}, tags=["Miscellaneous"])


@router.post("/waitlist", status_code=201)
async def add_waitlist_applicant(body:  WaitlistApplicationInput):

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
