from models.payments import Transaction
from models.users import AuthenticationContext
from libs.config.settings import get_settings
from libs.utils.req_helpers import make_req, make_url, Endpoints, handle_response
from libs.logging import Logger
from fastapi import HTTPException

logger = Logger(f"{__package__}.{__name__}")

settings = get_settings()


def _verify_transaction(tx_id: str, user_id: str):

    url = make_url(
        f"{Endpoints.flutterwave_tx_verification.value}/{tx_id}/verify")

    ok, status, data = make_req(
        url, "GET", headers={"Authorization": f"Bearer {settings.flutterwave_secret_key}"})

    success = handle_response(ok, status, data)

    if not success:
        logger.error(
            f"Unable to verify transaction {tx_id} for user {user_id} due to {ok} {status} {data} ")
        raise HTTPException(
            status_code=500, detail="Unable to verify transaction")

    result = data["data"]

    return result


def _initiate_topup_payment(transaction: Transaction, auth_context: AuthenticationContext):
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

    return result
