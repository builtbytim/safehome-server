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


def calculate_savings_plan_cycles(start_date: float, end_date: float, interval: IntervalsToSeconds):
    return (end_date - start_date) / interval.value


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
