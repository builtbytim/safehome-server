from pymongo import MongoClient
from pydantic import EmailStr
from libs.utils.pure_functions import get_utc_timestamp
from libs.config.settings import get_settings
from libs.logging import Logger
from libs.db import Collections
from models.wallets import Wallet
from models.referrals import Referral, UserReferralProfile
from models.affiliates import AffiliateLevel, AffiliateReferralCodeOutput, AffiliateProfile, AffiliateProfileOutput, AffiliateReferral, AffiliateReferralCode
from huey.exceptions import CancelExecution
from huey import crontab
from models.notifications import Notification, NotificationTypes
from .utils import exp_backoff_task
from .config import huey
from libs.emails.send_email import dispatch_email
from libs.utils.req_helpers import handle_response, make_req, make_url, Endpoints
from models.users import UserDBModel, KYCDocumentType, KYCStatus
from libs.utils.security import decrypt


logger = Logger(f"{__package__}.{__name__}")

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


# Task to process affiliate code
@exp_backoff_task(retries=10, retry_backoff=1.15, retry_delay=5)
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

    # create a referral

    affiliate_referral = AffiliateReferral(
        referred_by=affiliate_profile.user_id,
        referred_user_id=user_id,
        referred_user_email=user.email,
        referred_user_name=user.get_full_name(),
        referral_code=affiliate_code,
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

    db[Collections.affiliate_profiles].update_one(
        {"user_id": affiliate_profile.user_id}, {"$set": affiliate_profile.model_dump()})


# Task to process referral code
@exp_backoff_task(retries=10, retry_backoff=1.15, retry_delay=5)
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
@exp_backoff_task(retries=10, retry_backoff=1.15, retry_delay=5)
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

@exp_backoff_task(retries=10, retry_backoff=1.15, retry_delay=5)
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

@exp_backoff_task(retries=10, retry_backoff=1.15, retry_delay=5)
def task_send_mail(email_type:  str, email_to:  EmailStr | list[EmailStr], email_data:  dict):

    logger.info(f"Sending email of type {email_type} to {email_to}")

    dispatch_email(email_to, email_type, email_data)


# Task to initiate kyc verification

@exp_backoff_task(retries=10, retry_backoff=1.15, retry_delay=15)
def task_initiate_kyc_verification(user_id:  str):

    logger.info(f"Initiating KYC verification for user {user_id}")

    user = db[Collections.users].find_one({"uid": user_id})

    if not user:
        raise CancelExecution(retry=False)

    user_db = UserDBModel(**user)

    # Update the user's kyc status
    db[Collections.users].update_one(
        {"uid": user_id}, {"$set": {"kyc_status": KYCStatus.APPROVED.value}})

    # Send an email to the user
    task_send_mail("kyc_approved", user["email"], {
        "first_name": user["first_name"]})

    return

    if user["kyc_status"] == KYCStatus.APPROVED.value:
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

        url = make_url(Endpoints.bvn_verification.value,
                       surfix=f"/{decrypted_bvn}")

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
                {"uid": user_id}, {"$set": {"kyc_status": KYCStatus.APPROVED.value}})

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

        url = make_url(Endpoints.nin_verification.value,
                       surfix=f"/{decrypted_nin}")

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
                {"uid": user_id}, {"$set": {"kyc_status": KYCStatus.APPROVED.value}})

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
