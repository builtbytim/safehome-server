from fastapi import APIRouter, HTTPException, Depends, Response, Request
from fastapi.responses import RedirectResponse
from libs.config.settings import get_settings
from models.users import AuthenticationContext
from libs.db import _db, Collections
from libs.utils.api_helpers import find_record, update_record
from models.payments import *
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


@router.post("/top-up", status_code=200, response_model=TopupOutput)
async def topup_wallet(body:  TopupInput, auth_context: AuthenticationContext = Depends(get_auth_context), wallet:  Wallet = Depends(get_user_wallet)):

    if not wallet:
        logger.error(f"User {auth_context.user.uid} does not have a wallet")

        raise HTTPException(
            status_code=400, detail="You do not have a wallet yet! Please contact support.")

    transaction = Transaction(
        initiator=auth_context.user.uid,
        wallet=wallet.uid,
        amount=body.amount,
        direction=TransactionDirection.incoming,
        type=TransactionType.topup,
    )

    # initiate the transaction on flutterwave

    result = _initiate_topup_payment(transaction, auth_context)

    api_response = {
        "redirect_url": result["link"],
    }

    # save tx to db

    await _db[Collections.transactions].insert_one(transaction.model_dump())

    return api_response


@router.get("/top-up/complete", status_code=200)
async def complete_topup_wallet(req:  Request, ):

    query = req.query_params

    tx_status = query.get("status", None)
    tx_ref = query.get("tx_ref", None)

    if not tx_status or not tx_ref:
        logger.error(
            f"Invalid payment request parameters - {tx_status} {tx_ref}")
        raise HTTPException(
            status_code=400, detail="Invalid payment request parameters")

    # find the transaction

    transaction:  Transaction = await find_record(Transaction, Collections.transactions, "reference", tx_ref, raise_404=False)

    payment_rejection_url = f"{settings.app_url}/payments/failed"
    payment_success_url = f"{settings.app_url}/payments/success"

    failed_redirect = RedirectResponse(payment_rejection_url)
    success_redirect = RedirectResponse(payment_success_url)

    if not transaction:
        logger.error(
            f"Transaction with reference {tx_ref} not found")
        return failed_redirect

    if tx_status == "successful" or tx_status == "completed":

        # verify the transaction on flutterwave
        result = _verify_transaction(tx_ref, transaction.initiator)

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

        # update  corresponding wallet

        wallet: Wallet = await find_record(Wallet, Collections.wallets, "uid", transaction.wallet)

        wallet.balance += transaction.amount

        await update_record(Wallet, wallet.model_dump(), Collections.wallets, "uid", refresh_from_db=True)

        await update_record(Transaction, transaction.model_dump(), Collections.transactions, "reference", refresh_from_db=True)

        return success_redirect

    else:

        # update the transaction status to failed

        transaction.status = TransactionStatus.failed

        await update_record(Transaction, transaction.model_dump(), Collections.transactions, "reference", refresh_from_db=True)

        return failed_redirect
