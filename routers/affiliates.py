from fastapi import APIRouter, HTTPException, Depends, Query
from libs.config.settings import get_settings
from models.affiliates import *
from models.users import AuthenticationContext, UserDBModel
from libs.db import _db, Collections
from libs.utils.api_helpers import find_record, update_record
from libs.utils.pure_functions import *
from models.payments import Transaction, TransactionDirection, FundSource, TransactionStatus, TransactionType
from models.users import UserRoles
from models.wallets import Wallet
from models.notifications import NotificationTypes
from libs.huey_tasks.tasks import task_send_mail, task_create_notification
from libs.deps.users import get_auth_context, only_kyc_verified_users, only_paid_users, get_user_wallet, only_affiliates
from libs.utils.pagination import Paginator, PaginatedResult
from libs.logging import Logger


settings = get_settings()

logger = Logger(f"{__package__}.{__name__}")


router = APIRouter(responses={
    404: {"description": "The resource you requested does not exist!"}
}, tags=["Affiliates"], dependencies=[Depends(get_auth_context), Depends(only_kyc_verified_users), Depends(only_paid_users)])


@router.post("/become", status_code=200)
async def enable_affiliate_on_account(auth_context: AuthenticationContext = Depends(get_auth_context)):

    if auth_context.user.role == UserRoles.AFFILIATE:
        return

    else:
        auth_context.user.role = UserRoles.AFFILIATE

        await update_record(UserDBModel, auth_context.user.model_dump(), Collections.users, "uid", auth_context.user.uid)

        task_send_mail("welcome_to_affiliates", auth_context.user.email, {
            "first_name": auth_context.user.first_name})

        task_create_notification(
            auth_context.user.uid, NotificationTypes.account, "Your account has been enabled for affiliates.", "Your account has been enabled for affiliates. You can now start referring people to the platform and earn commissions.")

        return


@router.get("/profile", status_code=200, response_model=AffiliateProfileOutput)
async def get_affiliate_profile(auth_context: AuthenticationContext = Depends(get_auth_context), is_affiliate:  bool = Depends(only_affiliates)):

    affiliate_profile:  AffiliateProfile | None = await find_record(AffiliateProfile, Collections.affiliate_profiles, "user_id", auth_context.user.uid, raise_404=False)

    if not affiliate_profile:

        # create a new affiliate profile for the user

        new_affiliate_profile = AffiliateProfile(
            user_id=auth_context.user.uid,

        )

        # create one referral link

        new_code = generate_referral_code()

        # check if referral code already exists

        while await _db[Collections.affiliate_profiles].find_one({
            "referral_codes": {

                "$elemMatch": {
                    "code": new_code
                }

            }
        }):
            new_code = generate_referral_code()

        new_affiliate_link = AffiliateReferralCode(

            affiliate=auth_context.user.uid,
            affiliate_profile_id=new_affiliate_profile.uid,
            code=new_code,

        )

        new_affiliate_profile.referral_codes.append(new_affiliate_link)

        await _db[Collections.affiliate_profiles].insert_one(new_affiliate_profile.model_dump())

        res = new_affiliate_profile.model_dump(by_alias=True)

        res["referralCodes"] = [x.model_dump(
            by_alias=True) for x in new_affiliate_profile.referral_codes]

        return res

    res = affiliate_profile.model_dump(by_alias=True)

    res["referralCodes"] = [x.model_dump(
        by_alias=True) for x in affiliate_profile.referral_codes]

    return res


@router.get("/referrals", status_code=200, response_model=PaginatedResult)
async def get_referrals(auth_context: AuthenticationContext = Depends(get_auth_context), page: int = Query(default=1), limit: int = Query(default=20), search: str = Query(default=""), is_affiliate:  bool = Depends(only_affiliates), code_id:  str = Query(default="", alias="codeId")):

    root_filter = {"affiliate": auth_context.user.uid}

    filters = {}

    if code_id:
        filters.update({
            "referral_code_id":  code_id
        })

    if search:

        filters.update({"$or": [
            {"referred_user_name": {"$regex": search, "$options": "i"}},
            {"referred_user_email": {"$regex": search, "$options": "i"}},
            {"referred_user_id": {"$regex": search, "$options": "i"}},
        ]})

    paginator = Paginator(Collections.affiliate_referrals, "created_at",
                          True, limit, filters, root_filter=root_filter)

    return await paginator.get_paginated_result(page, AffiliateReferral)


@router.post("/withdraw", status_code=200, response_model=Transaction)
async def withdraw_affiliate_bonus(auth_context: AuthenticationContext = Depends(get_auth_context), is_affiliate:  bool = Depends(only_affiliates), user_wallet: Wallet = Depends(get_user_wallet)):

    affiliate_profile:  AffiliateProfile = await find_record(AffiliateProfile, Collections.affiliate_profiles, "user_id", auth_context.user.uid)

    if affiliate_profile.referral_bonus < settings.affiliate_withdrawal_threshold:
        raise HTTPException(
            status_code=400, detail="You have not reached the minimum withdrawal threshold!")

    amount = affiliate_profile.referral_bonus

    for referral in affiliate_profile.referral_codes:

        referral.referral_bonus = 0.0

    await _db[Collections.affiliate_profiles].update_one({"user_id": auth_context.user.uid}, {"$set": affiliate_profile.model_dump()})

    # Send email to applicant

    task_send_mail("affiliate_withdrawal", auth_context.user.email,
                   {"first_name":  auth_context.user.first_name, "amount": amount})

    transaction = Transaction(
        initiator=auth_context.user.uid,
        type=TransactionType.affiliate_bonus_deposit,
        wallet=user_wallet.uid,
        fund_source=FundSource.na,
        description=f"Affiliate bonus deposit of ₦{amount}",
        balance_after=user_wallet.balance + amount,
        amount=amount, direction=TransactionDirection.incoming, status=TransactionStatus.successful)

    user_wallet.balance += amount

    await _db[Collections.transactions].insert_one(transaction.model_dump())

    await _db[Collections.wallets].update_one({"user_id": auth_context.user.uid}, {"$set": user_wallet.model_dump()})

    return transaction
