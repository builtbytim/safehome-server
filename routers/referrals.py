from fastapi import APIRouter, HTTPException, Depends, Query
from libs.config.settings import get_settings
from models.referrals import *
from models.users import AuthenticationContext
from libs.db import _db, Collections
from libs.utils.api_helpers import find_record
from libs.utils.pure_functions import *
from models.payments import Transaction, TransactionDirection, FundSource, TransactionStatus, TransactionType
from models.notifications import NotificationTypes
from models.wallets import Wallet
from libs.huey_tasks.tasks import task_send_mail, task_create_notification
from libs.deps.users import get_auth_context,  only_paid_users, get_user_wallet, only_kyc_verified_users
from libs.utils.pagination import Paginator, PaginatedResult
from libs.logging import Logger


settings = get_settings()

logger = Logger(f"{__package__}.{__name__}")


router = APIRouter(responses={
    404: {"description": "The resource you requested does not exist!"}
}, tags=["Referrals"], dependencies=[Depends(get_auth_context), Depends(only_paid_users)])


@router.get("/profile", status_code=200, response_model=UserReferralProfileOutput)
async def get_referral_profile(auth_context: AuthenticationContext = Depends(get_auth_context)):

    referral_profile = await find_record(UserReferralProfile, Collections.referral_profiles, "user_id", auth_context.user.uid, raise_404=False)

    if not referral_profile:
        # create a new referral profile for the user

        referral_code = generate_referral_code()

        # check if referral code already exists

        while await find_record(UserReferralProfile, Collections.referral_profiles, "referral_code", referral_code, raise_404=False):
            referral_code = generate_referral_code()

        referral_profile = UserReferralProfile(
            user_id=auth_context.user.uid, referral_code=referral_code)

        await _db[Collections.referral_profiles].insert_one(referral_profile.model_dump())

    return referral_profile.model_dump(by_alias=True)


@router.get("/referrals", status_code=200, response_model=PaginatedResult)
async def get_referrals(auth_context: AuthenticationContext = Depends(get_auth_context), page: int = Query(default=1), limit: int = Query(default=20), search: str = Query(default="")):

    root_filter = {"referred_by": auth_context.user.uid}

    filters = {}

    if search:

        filters.update({"$or": [
            {"referred_user_name": {"$regex": search, "$options": "i"}},
            {"referred_user_email": {"$regex": search, "$options": "i"}},
            {"referred_user_id": {"$regex": search, "$options": "i"}},
        ]})

    paginator = Paginator(Collections.referrals, "created_at",
                          True, limit, filters, root_filter=root_filter)

    return await paginator.get_paginated_result(page, Referral)


@router.post("/withdraw", status_code=200, response_model=Transaction)
async def withdraw_referral_bonus(auth_context: AuthenticationContext = Depends(get_auth_context), user_wallet: Wallet = Depends(get_user_wallet), kyced: bool = Depends(only_kyc_verified_users)):

    referral_profile:  UserReferralProfile = await find_record(UserReferralProfile, Collections.referral_profiles, "user_id", auth_context.user.uid)

    if referral_profile.referral_bonus < settings.referral_withdrawal_threshold:
        raise HTTPException(
            status_code=400, detail="You have not reached the minimum withdrawal threshold!")

    amount = referral_profile.referral_bonus

    referral_profile.referral_bonus = 0.0

    await _db[Collections.referral_profiles].update_one({"user_id": auth_context.user.uid}, {"$set": referral_profile.model_dump()})

    # Send email to applicant

    task_send_mail("referral_withdrawal", auth_context.user.email,
                   {"first_name":  auth_context.user.first_name, "amount": amount})

    transaction = Transaction(
        initiator=auth_context.user.uid,
        wallet=user_wallet.uid,
        fund_source=FundSource.na,
        type=TransactionType.referral_bonus_deposit,
        description=f"Referral bonus deposit of ₦{amount}",
        balance_after=user_wallet.balance + amount,
        amount=amount, direction=TransactionDirection.incoming, status=TransactionStatus.successful,)

    user_wallet.balance += amount

    await _db[Collections.transactions].insert_one(transaction.model_dump())

    await _db[Collections.wallets].update_one({"user_id": auth_context.user.uid}, {"$set": user_wallet.model_dump()})

    task_create_notification(
        auth_context.user.uid, NotificationTypes.referral, "Referral Bonus Deposited", f"We have transferred your referral bonus of {amount}  into your wallet.")

    return transaction
