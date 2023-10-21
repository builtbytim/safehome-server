from fastapi import APIRouter, HTTPException, Depends, Query
from libs.config.settings import get_settings
from models.users import AuthenticationContext
from libs.db import _db, Collections
from libs.utils.api_helpers import find_record, update_record
from models.payments import Transaction
from libs.utils.flutterwave import _initiate_payment
from models.payments import *
from models.savings import *
from models.wallets import Wallet
from libs.utils.pure_functions import *
from libs.utils.pagination import Paginator, PaginatedResult
from libs.huey_tasks.tasks import task_send_mail, task_create_notification
from models.notifications import NotificationTypes
from libs.deps.users import get_auth_context, get_user_wallet, only_paid_users, only_kyc_verified_users
from libs.logging import Logger

logger = Logger(f"{__package__}.{__name__}")


settings = get_settings()


router = APIRouter(responses={
    404: {"description": "The resource you requested does not exist!"}
}, tags=["Savings"], dependencies=[Depends(only_paid_users)])


def calculate_savings_plan_cycles(start_date: float, end_date: float, interval: Intervals):
    threshold = float(IntervalsToSeconds[interval.name].value)

    return (end_date - start_date) / threshold


# create goal savings plan
@router.post("/goals", status_code=200, response_model=GoalSavingsPlan)
async def create_goal_savings_plan(body:  GoalSavingsPlanInput, auth_context:  AuthenticationContext = Depends(get_auth_context), user_wallet:  Wallet = Depends(get_user_wallet), paid_user:  bool = Depends(only_paid_users), kyc_verified_user:  bool = Depends(only_kyc_verified_users)):

    if not user_wallet:
        raise HTTPException(status_code=400,
                            detail="You cannot create a savings plan as you do not have a wallet.")

    # ensure sure that there are at least two cycles of interval between the start and end date

    if not is_valid_savings_plan_date_range(body.start_date, body.end_date, body.interval):
        raise HTTPException(status_code=400,
                            detail="The start date and end date must be at least two cycles of interval.")

    # create the savings plan
    savings_plan = GoalSavingsPlan(
        **body.model_dump(), user_id=auth_context.user.uid, cycles=calculate_savings_plan_cycles(body.start_date, body.end_date, body.interval), wallet_id=user_wallet.uid)

    await _db[Collections.goal_savings_plans].insert_one(savings_plan.model_dump())

    return savings_plan


# fetch my goal savings
@router.get("/goals", status_code=200, response_model=PaginatedResult)
async def get_my_goal_savings_plans(auth_context:  AuthenticationContext = Depends(get_auth_context), user_wallet:  Wallet = Depends(get_user_wallet), paid_user:  bool = Depends(only_paid_users),  page: int = Query(1, gt=0), limit: int = Query(10, gt=0), completed:  bool = Query(False)):

    root_filter = {
        "user_id":  auth_context.user.uid
    }

    if completed:
        root_filter["completed"] = True

    filters = {}

    paginator = Paginator(Collections.goal_savings_plans, "created_at",
                          top_down_sort=True, per_page=limit, filters=filters, root_filter=root_filter)

    return await paginator.get_paginated_result(page, GoalSavingsPlan)


# fund a goal savings
@router.post("/goals/fund", status_code=200, response_model=TopupOutput | None)
async def fund_goal_savings_plan(body:  FundGoalSavingsInput, auth_context:  AuthenticationContext = Depends(get_auth_context), user_wallet:  Wallet = Depends(get_user_wallet), paid_user:  bool = Depends(only_paid_users), kyc_verified_user:  bool = Depends(only_kyc_verified_users)):

    savings_plan: GoalSavingsPlan = await find_record(GoalSavingsPlan, Collections.goal_savings_plans, "uid", body.goal_savings_id)

    if savings_plan.payment_mode == PaymentModes.auto.value:
        raise HTTPException(status_code=400,
                            detail="You cannot fund an auto savings plan.")

    if not savings_plan:
        raise HTTPException(status_code=404,
                            detail="The savings plan you are trying to fund does not exist.")

    if savings_plan.user_id != auth_context.user.uid:
        raise HTTPException(status_code=403,
                            detail="You are not authorized to fund this savings plan.")

    if savings_plan.completed:
        raise HTTPException(status_code=400,
                            detail="You cannot fund a completed savings plan.")

    if savings_plan.withdrawn:
        raise HTTPException(status_code=400,
                            detail="You cannot fund a withdrawn savings plan.")

    if savings_plan.amount_saved >= savings_plan.goal_amount:
        raise HTTPException(status_code=400,
                            detail="You have already saved the required amount for this savings plan.")

    if savings_plan.amount_saved + body.amount_to_add > savings_plan.goal_amount:
        raise HTTPException(status_code=400,
                            detail="You cannot add more than the required amount to this savings plan.")

    # create a transaction
    transaction = Transaction(
        initiator=auth_context.user.uid,
        wallet=user_wallet.uid,
        amount=body.amount_to_add,
        direction=TransactionDirection.outgoing,
        type=TransactionType.savings_add_funds,
        description=f"Fund Savings Plan - {savings_plan.goal_name}",
        balance_before=user_wallet.balance,
    )

    if body.fund_source == FundSource.wallet:

        if user_wallet.balance < body.amount_to_add:
            raise HTTPException(status_code=400,
                                detail="You do not have enough balance to fund this savings plan.")

        transaction.balance_after = user_wallet.balance - body.amount_to_add

        # update the wallet
        user_wallet.balance = user_wallet.balance - body.amount_to_add

        transaction.fund_source = FundSource.wallet

        transaction.status = TransactionStatus.successful

        savings_plan.payment_references.append(transaction.reference)

        savings_plan.amount_saved += body.amount_to_add

        if savings_plan.amount_saved >= savings_plan.goal_amount:
            savings_plan.completed = True

        # update the wallet

        await update_record(Wallet, user_wallet.model_dump(), Collections.wallets, "uid")

        # update the savings plan

        await update_record(GoalSavingsPlan, savings_plan.model_dump(), Collections.goal_savings_plans, "uid")

        # save the transaction

        await _db[Collections.transactions].insert_one(transaction.model_dump())

    elif body.fund_source == FundSource.bank_account:

        transaction.fund_source = FundSource.bank_account

        transaction.status = TransactionStatus.pending

        # initiate payment
        result = _initiate_payment(transaction, auth_context, customizations={
            "title": f"Fund Savings Plan - {savings_plan.goal_name}",
            "description": f"Fund Savings Plan - {savings_plan.goal_name}"

        })

        api_response = {
            "redirect_url": result["link"],
        }

        # save the transaction
        await _db[Collections.transactions].insert_one(transaction.model_dump())

        # update the savings plan

        savings_plan.payment_references.append(transaction.reference)

        await update_record(GoalSavingsPlan, savings_plan.model_dump(), Collections.goal_savings_plans, "uid")

        return api_response


@router.get("/stats", status_code=200, response_model=UserSavingsStats)
async def get_user_savings_stats(auth_context: AuthenticationContext = Depends(get_auth_context), user_wallet: Wallet = Depends(get_user_wallet)):

    filters = {
        "user_id": auth_context.user.uid,
        "completed": False,
        "is_active":  True
    }

    savings_plans = await _db[Collections.goal_savings_plans].find(filters).to_list(None)

    savings_count = len(savings_plans)

    total_savings = 0

    for savings_plan in savings_plans:
        total_savings += savings_plan["amount_saved"]

    return UserSavingsStats(balance=total_savings, savings_count=savings_count,
                            goal_savings_balance=total_savings,
                            locked_savings_balance=0,
                            total_saved=user_wallet.total_amount_saved, total_withdrawn=user_wallet.total_amount_saved_withdrawn
                            )
