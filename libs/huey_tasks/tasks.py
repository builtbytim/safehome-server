from pymongo import MongoClient
from pydantic import EmailStr
from libs.utils.pure_functions import get_utc_timestamp
from libs.config.settings import get_settings
from libs.logging import Logger
from huey.exceptions import CancelExecution
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
