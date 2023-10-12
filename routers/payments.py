from fastapi import APIRouter, HTTPException, Depends, Response, Request
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

    payment_payload = {

        "tx_ref": transaction.reference,
        "amount": transaction.amount,
        "currency": transaction.currency,
        "redirect_url": f"{settings.server_url}/payments/top-up/complete",
        "customer": {
            "email": auth_context.user.email,
        },

        "customizations": {
            "title": "Top Up SafeHome",
            "description": "Top Up SafeHome wallet",
        },

    }

    url = make_url(Endpoints.flutterwave_payments.value)

    headers = {
        "Authorization": f"Bearer {settings.flutterwave_secret_key}",
    }

    ok, status, data = make_req(
        url, "POST", headers=headers, body=payment_payload)

    success = handle_response(ok, status, data)

    if not success:
        logger.error(
            f"Unable to initiate top-up payment for user {auth_context.user.uid} due to {ok} {status} {data} ")
        raise HTTPException(
            status_code=500, detail="Unable to initiate payment")

    result = data["data"]

    api_response = {
        "redirect_url": result["link"],
    }

    # save tx to db

    await _db[Collections.transactions].insert_one(transaction.model_dump())

    return api_response


@router.get("/top-up/complete", status_code=200)
async def complete_topup_wallet(req:  Request, res:  Response):

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

    if not transaction:
        logger.error(
            f"Transaction with reference {tx_ref} not found")
        raise HTTPException(
            status_code=404, detail="Transaction not found")

    if tx_status == "successful" or tx_status == "completed":

        # verify the transaction on flutterwave
        pass

    else:

        # update the transaction status to failed

        transaction.status = TransactionStatus.failed

        await update_record(Transaction, transaction.model_dump(), Collections.transactions, "reference", refresh_from_db=True)
