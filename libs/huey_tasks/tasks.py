from pymongo import MongoClient
from pydantic import EmailStr
from libs.utils.pure_functions import get_utc_timestamp
from libs.config.settings import get_settings
from libs.logging import Logger
from libs.db import Collections
from models.wallets import Wallet
from models.referrals import Referral, UserReferralProfile
from models.affiliates import AffiliateProfile, AffiliateReferral
from huey.exceptions import CancelExecution
from huey import crontab
from models.notifications import Notification, NotificationTypes
from .utils import exp_backoff_task
from .config import huey
from libs.emails.send_email import dispatch_email
from libs.utils.req_helpers import make_req, make_url, Endpoints, handle_response2
from models.users import UserDBModel, KYCDocumentType, KYCStatus
from libs.utils.security import decrypt
from datetime import datetime
import json


logger = Logger(f"{__package__}.{__name__}")

settings = get_settings()

client = MongoClient(settings.db_url)

db = client[settings.db_name]

OTP_TYPE = "otp"


def load_quore_id_api_token():

    token = None

    url = make_url(settings.quore_id_api_url, "/token")

    ok, status, data = make_req(
        url, "POST", {
            'Content-Type': 'application/json'
        }, {
            "clientId":  settings.quore_id_client_id,
            "secret": settings.quore_id_secret_key
        }
    )

    success = handle_response2(ok, status, data)

    if not success:
        logger.critical("\n Failed to get QUORE ID TOKEN ")

    else:

        token = data["accessToken"]
        logger.info("\n Fetched QUORE ID TOKEN successfully ")

        if settings.debug:
            print("Quore ID Details: ", data)

    return token


@huey.task(retries=3,  retry_delay=20, name="task_test_huey")
def task_test_huey():

    if not settings.debug:
        raise CancelExecution(retry=False)

    logger.info("\n Huey consumer is running")

    db["huey_test"].insert_one({"ts": get_utc_timestamp()})
    return


# Task to process affiliate code
@exp_backoff_task(retries=3, retry_backoff=1.15, retry_delay=45)
def task_process_affiliate_code(user_id:  str, affiliate_code: str):

    # get user

    user = db[Collections.users].find_one({"uid": user_id})

    if not user:
        logger.critical(f"User {user_id} does not exist")
        raise CancelExecution(retry=False)

    user = UserDBModel(**user)

    if not user.has_paid_membership_fee:
        logger.info(f"User {user_id} has not paid membership fee")
        raise CancelExecution(retry=False)

    # get affiliate profile that has the ref code

    affiliate_profile = db[Collections.affiliate_profiles].find_one({
        "referral_codes": {

            "$elemMatch": {
                "code": affiliate_code
            }

        }
    })

    if not affiliate_profile:
        logger.info(f"Affiliate code {affiliate_code} does not exist")
        raise CancelExecution(retry=False)

    affiliate_profile = AffiliateProfile(**affiliate_profile)

    # check if the user has already been referred

    affiliate_referral = db[Collections.affiliate_referrals].find_one({
        "referred_user_id": user_id
    })

    if affiliate_referral:
        logger.info(f"User {user_id} has already been referred")
        raise CancelExecution(retry=False)

    # check if the user  referred themselves

    if affiliate_profile.user_id == user_id:

        logger.info(f"User {user_id} has referred themselves")
        raise CancelExecution(retry=False)

    referral_code_obj = next(
        (x for x in affiliate_profile.referral_codes if x.code == affiliate_code), None)

    if not referral_code_obj:
        logger.info(f"Affiliate code {affiliate_code} does not exist")
        raise CancelExecution(retry=False)

    # create a referral

    affiliate_referral = AffiliateReferral(
        affiliate=affiliate_profile.user_id,
        referred_user_id=user_id,
        referred_user_email=user.email,
        referred_user_name=user.get_full_name(),
        referral_code_id=referral_code_obj.uid,
        referral_link=referral_code_obj.link,
        referral_bonus=settings.affiliate_bonus,
        confirmed=True
    )

    db[Collections.affiliate_referrals].insert_one(
        affiliate_referral.model_dump())

    # update the referral profile

    referral_code_obj.count += 1
    referral_code_obj.bonus += settings.affiliate_bonus
    referral_code_obj.total_bonus += settings.affiliate_bonus

    # special bonus for 10, 100 and 250 referrals

    if referral_code_obj.count == 10:
        referral_code_obj.bonus += 20000
        referral_code_obj.total_bonus += 20000

    elif referral_code_obj.count == 100:
        referral_code_obj.bonus += 200000
        referral_code_obj.total_bonus += 200000

    elif referral_code_obj.count == 250:
        referral_code_obj.bonus += 500000
        referral_code_obj.total_bonus += 500000

    db[Collections.affiliate_profiles].update_one(
        {"user_id": affiliate_profile.user_id}, {"$set": affiliate_profile.model_dump()})


# Task to process referral code
@exp_backoff_task(retries=3, retry_backoff=1.15, retry_delay=45)
def task_process_referral_code(user_id:  str, referralCode: str):

    # get user

    user = db[Collections.users].find_one({"uid": user_id})

    if not user:
        logger.critical(f"User {user_id} does not exist")
        raise CancelExecution(retry=False)

    user = UserDBModel(**user)

    if not user.has_paid_membership_fee:
        logger.info(f"User {user_id} has not paid membership fee")
        raise CancelExecution(retry=False)

    # get referral profile that has the ref code

    referral_profile = db[Collections.referral_profiles].find_one({
        "referral_code": referralCode
    })

    if not referral_profile:
        logger.info(f"Referral code {referralCode} does not exist")
        raise CancelExecution(retry=False)

    referral_profile = UserReferralProfile(**referral_profile)

    # check if the user has already been referred

    referral = db[Collections.referrals].find_one({
        "referred_user_id": user_id
    })

    if referral:
        logger.info(f"User {user_id} has already been referred")
        raise CancelExecution(retry=False)

    # check if the user  referred themselves

    if referral_profile.user_id == user_id:

        logger.info(f"User {user_id} has referred themselves")
        raise CancelExecution(retry=False)

    # create a referral

    referral = Referral(
        referred_by=referral_profile.user_id,
        referred_user_id=user_id,
        referred_user_email=user.email,
        referred_user_name=user.get_full_name(),
        referral_code=referral_profile.referral_code,
        referral_link=referral_profile.referral_link,
        referral_bonus=settings.referral_bonus,
        confirmed=True
    )

    db[Collections.referrals].insert_one(referral.model_dump())

    # update the referral profile

    referral_profile.referral_count += 1
    referral_profile.referral_bonus += settings.referral_bonus
    referral_profile.total_referral_bonus += settings.referral_bonus

    db[Collections.referral_profiles].update_one(
        {"user_id": referral_profile.user_id}, {"$set": referral_profile.model_dump()})


# Task to execute  additional actions after a successful user registration
@exp_backoff_task(retries=3, retry_backoff=1.15, retry_delay=45)
def task_post_user_registration(user_id:  str):

    logger.info(f"Executing post-registration actions for user {user_id}")

    user = db[Collections.users].find_one({"uid": user_id})

    if not user:
        logger.info(f"User {user_id} does not exist")
        raise CancelExecution(retry=False)

    # Wallet Creation Task

    # check if user has a wallet already
    wallet = db[Collections.wallets].find_one({"user_id": user_id})

    if not wallet:
        logger.info(f"Creating wallet for user {user_id}")

        # create a wallet for the user

        wallet = Wallet(user_id=user_id)

        db[Collections.wallets].insert_one(wallet.model_dump())


# Task to create a notification for a user

@exp_backoff_task(retries=3, retry_backoff=1.15, retry_delay=15)
def task_create_notification(user_id:  str, notification_type:  NotificationTypes,  title:  str, body:  str, ):

    logger.info(
        f"Creating notification of type {notification_type} for user {user_id}")

    user = db[Collections.users].find_one({"uid": user_id})

    if not user:
        logger.info(f"User {user_id} does not exist")
        raise CancelExecution(retry=False)

    # Create the notification

    notification = Notification(
        user_id=user_id, notification_type=notification_type, title=title, body=body)

    db[Collections.notifications].insert_one(notification.model_dump())


# Task to send an email

@exp_backoff_task(retries=3, retry_backoff=1.15, retry_delay=45)
def task_send_mail(email_type:  str, email_to:  EmailStr | list[EmailStr], email_data:  dict):

    logger.info(f"Sending email of type {email_type} to {email_to}")

    dispatch_email(email_to, email_type, email_data)


# Task to initiate kyc verification

@exp_backoff_task(retries=3, retry_backoff=1.15, retry_delay=45)
def task_initiate_kyc_verification(user_id:  str):

    quore_id_api_token = load_quore_id_api_token()

    if quore_id_api_token is None:
        logger.critical(f"QUORE ID TOKEN is not ready!!!")
        raise CancelExecution(retry=False)

    logger.info(f"Initiating KYC verification for user {user_id}")

    user = db[Collections.users].find_one({"uid": user_id})

    if not user:
        raise CancelExecution(retry=False)

    user_db = UserDBModel(**user)

    dob = datetime.fromtimestamp(
        user_db.date_of_birth).strftime("%Y-%m-%d")

    if user["kyc_status"] == KYCStatus.APPROVED.value:
        logger.info(f"User {user_id} has already been verified")
        raise CancelExecution(retry=False)

    if user["kyc_status"] != KYCStatus.PENDING.value:
        logger.info(f"User {user_id} has not been marked for KYC verification")
        raise CancelExecution(retry=False)

    approved = False
    failure_reason = ""

    decrypted_bvn = decrypt(bytes.fromhex(user_db.kyc_info.BVN)).decode()

    body = {
        "firstname": user_db.first_name,
        "lastname": user_db.last_name,
        "dob": dob,
        "gender":  user_db.gender,
        "phone": user_db.phone,
    }

    url = make_url(Endpoints.bvn_verification.value,
                   surfix=f"/{decrypted_bvn}")

    # Make the request to the KYC API
    ok, status, data = make_req(
        method="POST", url=url, body=body, headers={
            "Authorization": f"Bearer {quore_id_api_token}"
        })

    success = handle_response2(ok, status, data)

    if not success:

        reason = str(data) if type(data) != "str" else data

        try:
            t = json.loads(reason)
            reason = t["message"]

        except:
            pass

        # Update the user's kyc status
        db[Collections.users].update_one(
            {"uid": user_id}, {"$set": {"kyc_status": KYCStatus.REJECTED}})

        # Send an email to the user
        task_send_mail("kyc_rejected", user["email"], {
            "first_name": user["first_name"], "reason":  reason})

        logger.info(
            f"KYC verification request for user {user_id} failed - {ok} {status} {data}")

        raise CancelExecution(retry=True)

    bvn_summary = data["summary"]
    # bvn_status = bvn_summary["status"]

    field_matches = bvn_summary["bvn_match_check"]["fieldMatches"]

    unmatched_fields = []

    if not field_matches.get("firstname", None):
        unmatched_fields.append("First Name")

    if not field_matches.get("lastname", None):
        unmatched_fields.append("Last Name")

    if len(unmatched_fields) > 0:

        reason = "The details you provided do not match the details on your BVN. The following fields do not match: " + \
            ", ".join(unmatched_fields)

        failure_reason = reason

        # # Update the user's kyc status
        # db[Collections.users].update_one(
        #     {"uid": user_id}, {"$set": {"kyc_status": KYCStatus.REJECTED}})

        # # Send an email to the user
        # task_send_mail("kyc_rejected", user["email"], {
        #     "first_name": user["first_name"], "reason":  reason})

    else:

        approved = True

        # # Update the user's kyc status
        # db[Collections.users].update_one(
        #     {"uid": user_id}, {"$set": {"kyc_status": KYCStatus.APPROVED}})

        # # Send an email to the user
        # task_send_mail("kyc_approved", user["email"], {
        #     "first_name": user["first_name"], })

    decrypted_nin = decrypt(bytes.fromhex(
        user_db.kyc_info.IDNumber)).decode()

    body = {
        "firstname": user_db.first_name,
        "lastname": user_db.last_name,
        "dob": dob,
        "gender":  user_db.gender

    }

    url = make_url(Endpoints.nin_verification.value,
                   surfix=f"/{decrypted_nin}")

    # Make the request to the KYC API
    ok, status, data = make_req(
        url, "POST",  body=body, headers={
            "Authorization": f"Bearer {quore_id_api_token}"
        })

    success = handle_response2(ok, status, data)

    if not success:

        reason = str(data) if type(data) != "str" else data

        try:
            t = json.loads(reason)
            reason = t["message"]

        except:
            pass

        # Update the user's kyc status
        db[Collections.users].update_one(
            {"uid": user_id}, {"$set": {"kyc_status": KYCStatus.REJECTED}})

        # Send an email to the user
        task_send_mail("kyc_rejected", user["email"], {
            "first_name": user["first_name"], "reason":  reason})

        logger.info(
            f"KYC verification request for user {user_id} failed - {ok} {status} {data}")

        raise CancelExecution(retry=False)

    nin_summary = data["summary"]
    # nin_status = nin_summary["status"]

    field_matches = nin_summary["nin_check"]["fieldMatches"]

    unmatched_fields = []

    if not field_matches.get("firstname", None):
        unmatched_fields.append("First Name")

    if not field_matches.get("lastname", None):
        unmatched_fields.append("Last Name")

    if not field_matches.get("gender", None):
        unmatched_fields.append("Gender")

    if "dob" in field_matches:
        if not field_matches["dob"]:
            unmatched_fields.append("Date of Birth")

    if len(unmatched_fields) > 0:

        reason = "1. The details you provided do not match the details on your NIN. The following fields do not match: " + \
            ", ".join(unmatched_fields)

        if failure_reason:

            reason += f"   2. {failure_reason}"

        # Update the user's kyc status
        db[Collections.users].update_one(
            {"uid": user_id}, {"$set": {"kyc_status": KYCStatus.REJECTED}})

        # Send an email to the user
        task_send_mail("kyc_rejected", user["email"], {
            "first_name": user["first_name"], "reason":  reason})

    else:

        if not approved:

            # Update the user's kyc status
            db[Collections.users].update_one(
                {"uid": user_id}, {"$set": {"kyc_status": KYCStatus.REJECTED}})

            # Send an email to the user
            task_send_mail("kyc_rejected", user["email"], {
                "first_name": user["first_name"], "reason":  failure_reason})

        else:

            # Update the user's kyc status
            db[Collections.users].update_one(
                {"uid": user_id}, {"$set": {"kyc_status": KYCStatus.APPROVED}})

            # Send an email to the user
            task_send_mail("kyc_approved", user["email"], {
                "first_name": user["first_name"], })
