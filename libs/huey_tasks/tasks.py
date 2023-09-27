from pymongo import MongoClient
from pydantic import EmailStr
from libs.utils.pure_functions import get_utc_timestamp
from libs.config.settings import get_settings
from libs.logging import Logger
from libs.db import Collections
from huey.exceptions import CancelExecution
from huey import crontab
from .utils import exp_backoff_task
from .config import huey
from libs.emails.send_email import dispatch_email


logger = Logger(__name__)

settings = get_settings()

client = MongoClient(settings.db_url)

db = client[settings.db_name]

OTP_TYPE = "otp"


# Task to test the huey consumer
@huey.task(retries=3,  retry_delay=20, name="task_test_huey")
def task_test_huey():

    if not settings.debug:
        raise CancelExecution(retry=False)

    logger.info("\n Huey consumer is running")

    db["huey_test"].insert_one({"ts": get_utc_timestamp()})
    return


# Task to send an email

@exp_backoff_task(retries=10, retry_backoff=1.15, retry_delay=5)
def task_send_mail(email_type:  str, email_to:  EmailStr | list[EmailStr], email_data:  dict):

    logger.info(f"Sending email of type {email_type} to {email_to}")

    dispatch_email(email_to, email_type, email_data)


# Task to mark users who have gone throught kyc as eligible to sign in to the platform
@huey.periodic_task(crontab(minute='*/1'), retries=5, retry_delay=30,)
def make_eligible_users_able_to_sign_in_after_kyc():

    logger.info(f"Making eligible users able to sign in after KYC")

    # Get all users who have gone through KYC
    cursor = db[Collections.users].find(
        {"kyc_status": "pending"}).sort("created_at", -1).limit(100)

    for user in cursor:

        if user["kyc_document"] is not None and user["kyc_photo"] is not None:

            # Update the user's kyc status
            db[Collections.users].update_one(
                {"uid": user["uid"]}, {"$set": {"kyc_status": "approved"}})

            # Send an email to the user
            task_send_mail("kyc_approved", user["email"], {
                           "first_name": user["first_name"]})
