from fastapi import APIRouter, HTTPException, Depends, Query
from libs.config.settings import get_settings
from models.referrals import *
from models.users import AuthenticationContext
from libs.db import _db, Collections
from libs.utils.api_helpers import find_record
from libs.utils.pure_functions import *
from models.payments import Transaction, TransactionDirection, FundSource, TransactionStatus, TransactionType
from models.wallets import Wallet
from libs.huey_tasks.tasks import task_send_mail
from libs.deps.users import get_auth_context, only_kyc_verified_users, only_paid_users, get_user_wallet
from libs.utils.pagination import Paginator, PaginatedResult
from libs.logging import Logger


settings = get_settings()

logger = Logger(f"{__package__}.{__name__}")


router = APIRouter(responses={
    404: {"description": "The resource you requested does not exist!"}
}, tags=["Referrals"], dependencies=[Depends(get_auth_context), Depends(only_kyc_verified_users), Depends(only_paid_users)])


@router.get("/profile", status_code=200, response_model=UserReferralProfile)
async def get_referral_profile(auth_context: AuthenticationContext = Depends(get_auth_context)):

    referral_profile = await find_record(UserReferralProfile, Collections.referral_profiles, "user_id", auth_context.user.uid, raise_404=False)

    if not referral_profile:
        # create a new referral profile for the user

        referral_code = generate_referral_code()

        # check if referral code already exists

        while await find_record(UserReferralProfile, Collections.referral_profiles, "referral_code", referral_code, raise_404=False):
            referral_code = generate_referral_code()

        referral_link = f"{settings.app_url}/r/{referral_code}"

        referral_profile = UserReferralProfile(
            user_id=auth_context.user.uid, referral_code=referral_code, referral_link=referral_link)

        await _db[Collections.referral_profiles].insert_one(referral_profile.model_dump())

    return referral_profile


@router.get("/referrals", status_code=200, response_model=PaginatedResult)
async def get_referrals(auth_context: AuthenticationContext = Depends(get_auth_context), page: int = Query(default=1), limit: int = Query(default=20)):

    root_filter = {"referred_by": auth_context.user.uid}

    filters = {}

    paginator = Paginator(Collections.referrals, "created_at",
                          True, limit, filters, root_filter=root_filter)

    return await paginator.get_paginated_result(page, Referral)


@router.post("/withdraw", status_code=200)
async def withdraw_referral_bonus(auth_context: AuthenticationContext = Depends(get_auth_context), user_wallet: Wallet = Depends(get_user_wallet)):

    referral_profile:  UserReferralProfile = await find_record(UserReferralProfile, Collections.referral_profiles, "user_id", auth_context.user.uid)

    if referral_profile.referral_bonus < settings.referral_withdrawal_threshold:
        raise HTTPException(
            status_code=400, detail="You have not reached the minimum withdrawal threshold!")

    amount = referral_profile.referral_bonus

    referral_profile.referral_bonus = 0.0

    referral_profile.total_referral_bonus += amount

    await _db[Collections.referral_profiles].update_one({"user_id": auth_context.user.uid}, {"$set": referral_profile.model_dump()})

    # Send email to applicant

    task_send_mail("referral_withdrawal", auth_context.user.email,
                   {"first_name":  auth_context.user.first_name, "amount": amount})

    transaction = Transaction(
        initiator=auth_context.user.uid,
        wallet=user_wallet.uid,
        fund_source=FundSource.na,
        amount=amount, direction=TransactionDirection.incoming, status=TransactionStatus.successful, type=TransactionType.referral_bonus_deposit)

    user_wallet.balance += amount

    await _db[Collections.transactions].insert_one(transaction.model_dump())

    await _db[Collections.wallets].update_one({"user_id": auth_context.user.uid}, {"$set": user_wallet.model_dump()})

    return {"message": "Withdrawal request successful!"}
