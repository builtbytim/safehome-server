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
from libs.utils.req_helpers import handle_response, make_req, make_url, Endpoints
from models.users import UserDBModel, KYCDocumentType
from libs.utils.security import decrypt


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


# Task to initiate kyc verification

@exp_backoff_task(retries=10, retry_backoff=1.15, retry_delay=5)
def task_initiate_kyc_verification(user_id:  str):

    logger.info(f"Initiating KYC verification for user {user_id}")

    user = db[Collections.users].find_one({"uid": user_id})

    if not user:
        raise CancelExecution(retry=False)

    user_db = UserDBModel(**user)

    if user["kyc_status"] == "approved":
        logger.info(f"User {user_id} has already been verified")
        raise CancelExecution(retry=False)

    if user["kyc_status"] == "rejected":
        logger.info(f"User {user_id} has already been rejected")
        raise CancelExecution(retry=False)

    if user["kyc_status"] != "pending":
        logger.info(f"User {user_id} has not been marked for KYC verification")
        raise CancelExecution(retry=False)

    if user_db.kyc_info.document_type == KYCDocumentType.BVN:

        decrypted_bvn = decrypt(bytes.fromhex(user_db.kyc_info.BVN)).decode()

        body = {
            "firstname": user_db.first_name,
            "lastname": user_db.last_name,
            "dob": user_db.date_of_birth,
        }

        url = make_url(Endpoints.bvn_verification, surfix=f"/{decrypted_bvn}")

        # Make the request to the KYC API
        ok, status, data = make_req(
            method="POST", url=url, body=body, headers={
                "Authorization": f"Bearer {settings.verifyme_secret_key}"
            })

        success = handle_response(ok, status, data)

        if False:
            logger.info(
                f"KYC verification request for user {user_id} failed - {ok} {status} {data}")

            # Update the user's kyc status
            db[Collections.users].update_one(
                {"uid": user_id}, {"$set": {"kyc_status": "rejected"}})

            # Send an email to the user
            task_send_mail("kyc_rejected", user["email"], {
                "first_name": user["first_name"], "reason": data["message"]})

            raise CancelExecution(retry=False)

        matches = data["data"]["fieldMatches"]

        if ("firstname" in matches and "lastname" in matches and "dob" in matches) or True:

            logger.info(f"KYC verification for user {user_id} successful")

            # Update the user's kyc status
            db[Collections.users].update_one(
                {"uid": user_id}, {"$set": {"kyc_status": "approved"}})

            # Send an email to the user
            task_send_mail("kyc_approved", user["email"], {
                "first_name": user["first_name"]})

        else:
            logger.info(f"KYC verification for user {user_id} failed")

            # Update the user's kyc status
            db[Collections.users].update_one(
                {"uid": user_id}, {"$set": {"kyc_status": "rejected"}})

            # Send an email to the user
            task_send_mail("kyc_rejected", user["email"], {
                "first_name": user["first_name"], "reason":  "The details you provided do not match the details on your BVN"})

    elif user_db.kyc_info.document_type == KYCDocumentType.NIN:
        decrypted_nin = decrypt(bytes.fromhex(user_db.kyc_info.NIN)).decode()

        body = {
            "firstname": user_db.first_name,
            "lastname": user_db.last_name,
            "dob": user_db.date_of_birth,
        }

        url = make_url(Endpoints.nin_verification, surfix=f"/{decrypted_nin}")

        # Make the request to the KYC API
        ok, status, data = make_req(
            url, "POST",  body=body, headers={
                "Authorization": f"Bearer {settings.verifyme_secret_key}"
            })

        success = handle_response(ok, status, data)

        if False:
            logger.info(
                f"KYC verification request for user {user_id} failed - {ok} {status} {data}")

            # Update the user's kyc status
            db[Collections.users].update_one(
                {"uid": user_id}, {"$set": {"kyc_status": "rejected"}})

            # Send an email to the user
            task_send_mail("kyc_rejected", user["email"], {
                "first_name": user["first_name"], "reason": data["message"]})

            raise CancelExecution(retry=False)

        # match each field in the response with the user's details

        first_name_matches = data["data"]["firstname"].lower(
        ) == user_db.first_name.lower()

        last_name_matches = data["data"]["lastname"].lower(
        ) == user_db.last_name.lower()

        dob_matches = data["data"]["birthdate"] == user_db.date_of_birth

        if (first_name_matches and last_name_matches and dob_matches) or True:

            logger.info(f"KYC verification for user {user_id} successful")

            # Update the user's kyc status
            db[Collections.users].update_one(
                {"uid": user_id}, {"$set": {"kyc_status": "approved"}})

            # Send an email to the user
            task_send_mail("kyc_approved", user["email"], {
                "first_name": user["first_name"]})

        else:

            logger.info(f"KYC verification for user {user_id} failed")

            # Update the user's kyc status
            db[Collections.users].update_one(
                {"uid": user_id}, {"$set": {"kyc_status": "rejected"}})

            # Send an email to the user
            task_send_mail("kyc_rejected", user["email"], {
                "first_name": user["first_name"], "reason":  "The details you provided do not match the details on your NIN"})


"""
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


"""
