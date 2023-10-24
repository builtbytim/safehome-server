from fastapi import APIRouter, HTTPException, Depends, Response, Request
from fastapi.responses import RedirectResponse
from libs.config.settings import get_settings
from models.users import AuthenticationContext, UserDBModel
from libs.db import _db, Collections
from libs.utils.api_helpers import find_record, update_record
from models.payments import *
from models.investments import Investment
from models.notifications import NotificationTypes
from models.wallets import Wallet
from models.savings import GoalSavingsPlan, FundSource, LockedSavingsPlan
from libs.utils.pure_functions import *
from libs.huey_tasks.tasks import task_send_mail, task_create_notification
from libs.deps.users import get_auth_context, get_user_wallet
from libs.logging import Logger
from libs.utils.req_helpers import make_req, make_url, Endpoints, handle_response
from libs.utils.flutterwave import _initiate_payment, _verify_transaction
from libs.deps.users import get_auth_context, get_user_wallet


logger = Logger(f"{__package__}.{__name__}")


settings = get_settings()


router = APIRouter(responses={
    404: {"description": "The resource you requested does not exist!"}
}, tags=["Payments"])


# one time membership payment for new users
@router.post("/membership", status_code=201)
async def initiate_membership_payment(auth_context: AuthenticationContext = Depends(get_auth_context), wallet: Wallet = Depends(get_user_wallet)):

    if auth_context.user.has_paid_membership_fee:
        raise HTTPException(
            status_code=400, detail="You have already paid your membership fee. Reload the page manually if you think this is an error.")

    MEMBERSHIP_FEE = settings.membership_fee

    transaction = Transaction(
        initiator=auth_context.user.uid,
        wallet=wallet.uid,
        amount=MEMBERSHIP_FEE,
        direction=TransactionDirection.outgoing,
        type=TransactionType.membership_fee,
        description="Membership Fee",
        balance_before=wallet.balance,
        balance_after=wallet.balance,

    )

    result = _initiate_payment(transaction, auth_context, customizations={

        "title": "SafeHome",
        "description": "Membership Fee",

    })

    api_response = {
        "redirect_url": result["link"],
    }

    # save tx to db

    await _db[Collections.transactions].insert_one(transaction.model_dump())

    return api_response


@router.get("/complete", status_code=200)
async def complete_payment(req:  Request, ):

    allowed_tx_types = [TransactionType.membership_fee, TransactionType.investment,
                        TransactionType.savings_add_funds, TransactionType.locked_savings_add_funds]

    query = req.query_params

    tx_status = query.get("status", None)
    tx_ref = query.get("tx_ref", None)
    tx_id = query.get("transaction_id", None)

    if not tx_status or not tx_ref:
        logger.error(
            f"Invalid payment request parameters - {tx_status} {tx_ref} {tx_id}")
        raise HTTPException(
            status_code=400, detail="Invalid payment request parameters")

    # find the transaction

    transaction:  Transaction = await find_record(Transaction, Collections.transactions, "reference", tx_ref, raise_404=False)

    payment_rejection_url = f"{settings.app_url}?showTx=true&txStatus=failed&txRef={tx_ref}"
    payment_success_url = f"{settings.app_url}?showTx=true&txStatus=successful&txRef={tx_ref}"

    failed_redirect = RedirectResponse(payment_rejection_url)
    success_redirect = RedirectResponse(payment_success_url)

    if not transaction:
        logger.error(
            f"Transaction with reference {tx_ref} not found")
        return failed_redirect

    if transaction.status == TransactionStatus.successful:
        return success_redirect

    if transaction.status == TransactionStatus.failed:
        return failed_redirect

    if transaction.type not in allowed_tx_types:
        logger.error(
            f"Transaction type not allowed - {transaction.type}")
        return failed_redirect

    if tx_status == "successful" or tx_status == "completed":

        # verify the transaction on flutterwave
        result = _verify_transaction(tx_id, transaction.initiator)

        if result["tx_ref"] != transaction.reference:
            logger.error(
                f"Transaction reference mismatch - {tx_ref} {transaction.reference}")
            return failed_redirect

        if result["status"] != "successful":
            logger.error(
                f"Transaction status mismatch - {tx_ref} {result['status']}")
            return failed_redirect

        if transaction.amount > result["amount"]:
            logger.error(
                f"Transaction amount mismatch - {tx_ref} {result['amount']}")
            return failed_redirect

        # update the transaction status to completed

        transaction.status = TransactionStatus.successful

        transaction.tx_id = tx_id

        # give wallet

        the_wallet: Wallet = await find_record(Wallet, Collections.wallets, "uid", transaction.wallet, raise_404=False)

        if not the_wallet:
            logger.error(
                f"Unable to find wallet with uid {transaction.initiator}")
            return failed_redirect

        if transaction.type == TransactionType.investment:

            the_investment: Investment = await find_record(Investment, Collections.investments, "payment_reference", transaction.reference, raise_404=False)

            if not the_investment:
                logger.error(
                    f"Unable to find investment with payment reference {transaction.reference}")
                return failed_redirect

            the_investment.is_active = True

            the_wallet.total_amount_invested += transaction.amount

            transaction.balance_after = the_wallet.balance

            await update_record(Investment, the_investment.model_dump(), Collections.investments, "uid", refresh_from_db=True)

            # fetch the asset for the investment

            asset = await _db[Collections.investible_assets].find_one(
                {"uid": the_investment.asset_uid})

            if not asset:
                logger.error(
                    f"Unable to find asset with uid {the_investment.asset_uid}")
                return failed_redirect

            task_create_notification(
                the_investment.investor_uid, "Investment Successful", f"Your investment in {asset['asset_name']} was successful", NotificationTypes.investment)

        elif transaction.type == TransactionType.savings_add_funds:

            the_savings_plan = await _db[Collections.goal_savings_plans].find_one({
                "payment_references": {
                    "$elemMatch": {

                        "$eq": transaction.reference

                    }
                }
            })

            if not the_savings_plan:
                logger.error(
                    f"Unable to find savings plan with payment reference {transaction.reference}")
                return failed_redirect

            the_savings_plan = GoalSavingsPlan(**the_savings_plan)

            the_savings_plan.amount_saved += transaction.amount

            transaction.balance_after = the_wallet.balance

            await update_record(GoalSavingsPlan, the_savings_plan.model_dump(), Collections.goal_savings_plans, "uid")

            task_create_notification(
                transaction.initiator, "Add Fund to Savings Plan Successful", f"You added funds to savings plan {the_savings_plan.goal_name} ", NotificationTypes.savings)

        elif transaction.type == TransactionType.locked_savings_add_funds:

            the_savings_plan = await _db[Collections.locked_savings_plans].find_one({
                "payment_references": {
                    "$elemMatch": {

                        "$eq": transaction.reference

                    }
                }
            })

            if not the_savings_plan:
                logger.error(
                    f"Unable to find locked savings plan with payment reference {transaction.reference}")
                return failed_redirect

            the_savings_plan = LockedSavingsPlan(**the_savings_plan)

            the_savings_plan.amount_saved += transaction.amount

            transaction.balance_after = the_wallet.balance

            await update_record(LockedSavingsPlan, the_savings_plan.model_dump(), Collections.locked_savings_plans, "uid")

            task_create_notification(
                transaction.initiator, "Add Fund to Locked Savings Plan Successful", f"You added funds to locked savings plan {the_savings_plan.lock_name} ", NotificationTypes.savings)

        elif transaction.type == TransactionType.membership_fee:

            the_wallet.is_active = True

            # set has paid on user to true

            user: UserDBModel = await find_record(UserDBModel, Collections.users, "uid", transaction.initiator, raise_404=False)

            if not user:
                logger.error(
                    f"Unable to find user with uid {transaction.initiator}")
                return failed_redirect

            user.has_paid_membership_fee = True

            transaction.balance_after = the_wallet.balance

            await update_record(UserDBModel, user.model_dump(), Collections.users, "uid", refresh_from_db=True)

            task_create_notification(
                transaction.initiator, "Membership Fee Paid", f"Your membership fee payment was successful", NotificationTypes.account)

        else:

            the_wallet: Wallet = await find_record(Wallet, Collections.wallets, "uid", transaction.initiator, raise_404=False)

            if not the_wallet:
                logger.error(
                    f"Unable to find wallet with uid {transaction.initiator}")
                return failed_redirect

            the_wallet.balance += transaction.amount
            transaction.balance_after = the_wallet.balance
            the_wallet.total_amount_deposited += transaction.amount
            the_wallet.last_transaction_at = get_utc_timestamp()

            task_create_notification(
                transaction.initiator, "Added funds successfully", f"Your funding of {transaction.amount} was successful", NotificationTypes.wallet)

            user: UserDBModel = await find_record(UserDBModel, Collections.users, "uid", transaction.initiator, raise_404=False)

            if not user:
                logger.error(
                    f"Unable to find user with uid {transaction.initiator}")
                return failed_redirect

            # send mail

        await update_record(Transaction, transaction.model_dump(), Collections.transactions, "reference", refresh_from_db=True)

        await update_record(Wallet, the_wallet.model_dump(), Collections.wallets, "uid", refresh_from_db=True)

        return success_redirect

    else:

        # update the transaction status to failed

        transaction.status = TransactionStatus.failed

        await update_record(Transaction, transaction.model_dump(), Collections.transactions, "reference", refresh_from_db=True)

        return failed_redirect
