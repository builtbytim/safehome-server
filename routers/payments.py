from fastapi import APIRouter, HTTPException, Depends, Response, Request
from fastapi.responses import RedirectResponse
from libs.config.settings import get_settings
from models.users import AuthenticationContext, UserDBModel
from libs.db import _db, Collections
from libs.utils.api_helpers import find_record, update_record
from models.payments import *
from models.investments import Investment
from models.wallets import Wallet
from libs.utils.pure_functions import *
from libs.huey_tasks.tasks import task_send_mail
from libs.deps.users import get_auth_context, get_user_wallet
from libs.logging import Logger
from libs.utils.req_helpers import make_req, make_url, Endpoints, handle_response
from libs.utils.flutterwave import _initiate_topup_payment, _verify_transaction

logger = Logger(f"{__package__}.{__name__}")


settings = get_settings()


router = APIRouter(responses={
    404: {"description": "The resource you requested does not exist!"}
}, tags=["Payments"])


@router.get("/complete", status_code=200)
async def complete_payment(req:  Request, ):

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

        if transaction.type == TransactionType.investment:

            the_investment: Investment = await find_record(Investment, Collections.investments, "payment_reference", transaction.reference, raise_404=False)

            if not the_investment:
                logger.error(
                    f"Unable to find investment with payment reference {transaction.reference}")
                return failed_redirect

            the_investment.is_active = True

            await update_record(Investment, the_investment.model_dump(), Collections.investments, "uid", refresh_from_db=True)

        else:

            the_wallet: Wallet = await find_record(Wallet, Collections.wallets, "uid", transaction.initiator, raise_404=False)

            if not the_wallet:
                logger.error(
                    f"Unable to find wallet with uid {transaction.initiator}")
                return failed_redirect

            the_wallet.balance += transaction.amount
            the_wallet.last_transaction_at = get_utc_timestamp()

            await update_record(Wallet, the_wallet.model_dump(), Collections.wallets, "uid", refresh_from_db=True)

            user: UserDBModel = await find_record(UserDBModel, Collections.users, "uid", transaction.initiator, raise_404=False)

            if not user:
                logger.error(
                    f"Unable to find user with uid {transaction.initiator}")
                return failed_redirect

            # send mail

        await update_record(Transaction, transaction.model_dump(), Collections.transactions, "reference", refresh_from_db=True)

        return success_redirect

    else:

        # update the transaction status to failed

        transaction.status = TransactionStatus.failed

        await update_record(Transaction, transaction.model_dump(), Collections.transactions, "reference", refresh_from_db=True)

        return failed_redirect
