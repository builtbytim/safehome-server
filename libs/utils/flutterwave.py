from models.payments import Transaction
from fastapi import HTTPException
from models.users import AuthenticationContext
from libs.config.settings import get_settings
from libs.utils.req_helpers import make_req, make_url, Endpoints, handle_response
from models.wallets import BankAccount
from libs.logging import Logger
from fastapi import HTTPException

logger = Logger(f"{__package__}.{__name__}")

settings = get_settings()


def _resolve_bank_account(bank_code: str, account_number: str):

    try:

        url = make_url(
            f"{Endpoints.flutterwave_resolve_bank_account.value}")

        body = {
            "account_number": account_number,
            "account_bank": bank_code,
        }

        # temp fix
        return {
            "account_number": "0690000032",
            "account_name": "Pastor Bright"
        }

        ok, status, data = make_req(
            url, "POST", headers={"Authorization": f"Bearer {settings.flutterwave_secret_key}"}, body=body)

        if str(status) == "400":
            raise HTTPException(
                status_code=400, detail="Invalid bank account")

        success = handle_response(ok, status, data)

        if not success:
            logger.error(
                f"Unable to resolve bank account {account_number} due to {ok} {status} {data} ")
            raise HTTPException(
                status_code=500, detail="Unable to resolve bank account")

        result = data["data"]

        return result

    except Exception as e:
        logger.error(
            f"Unable to resolve bank account {account_number} due to {e} ")
        raise HTTPException(
            status_code=500, detail="Unable to resolve bank account")


def _get_supported_banks(country: str = "NG"):

    try:

        url = make_url(
            f"{Endpoints.flutterwave_get_banks.value}/{country}")

        ok, status, data = make_req(
            url, "GET", headers={"Authorization": f"Bearer {settings.flutterwave_secret_key}"})

        success = handle_response(ok, status, data)

        if not success:
            logger.error(
                f"Unable to get supported banks for country {country} due to {ok} {status}  ")
            raise HTTPException(
                status_code=500, detail="Unable to get supported banks")

        result = data["data"]

        return result

    except Exception as e:
        logger.error(
            f"Unable to get supported banks for country {country} due to {e}  ")
        raise HTTPException(
            status_code=500, detail="Unable to get supported banks")


def _verify_transaction(tx_id: str, user_id: str):

    try:

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

    except Exception as e:
        logger.error(
            f"Unable to verify transaction {tx_id} for user {user_id} due to {e} ")
        raise HTTPException(
            status_code=500, detail="Unable to verify transaction")


def _initiate_payment(transaction: Transaction, auth_context: AuthenticationContext, customizations: dict = {}):

    try:

        # initiate the transaction on flutterwave

        payment_payload = {

            "tx_ref": transaction.reference,
            "amount": transaction.amount,
            "currency": transaction.currency,
            "redirect_url": f"{settings.server_url}/payments/complete",
            "customer": {
                "email": auth_context.user.email,
            },

            "customizations": customizations,

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
                f"Unable to initiate payment for user {auth_context.user.uid} due to {ok} {status} {data} ")
            raise HTTPException(
                status_code=500, detail="Unable to initiate payment")

        result = data["data"]

        return result

    except Exception as e:
        logger.error(
            f"Unable to initiate payment for user {auth_context.user.uid} due to {e} ")
        raise HTTPException(
            status_code=500, detail="Unable to initiate payment")


def _initiate_topup_payment(transaction: Transaction, auth_context: AuthenticationContext):

    try:

        # initiate the transaction on flutterwave

        payment_payload = {

            "tx_ref": transaction.reference,
            "amount": transaction.amount,
            "currency": transaction.currency,
            "redirect_url": f"{settings.server_url}/wallet/top-up/complete",
            "customer": {
                "email": auth_context.user.email,
            },

            "customizations": {
                "title": "SafeHome",
                "description": "Top Up your SafeHome",
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

    except Exception as e:
        logger.error(
            f"Unable to initiate top-up payment for user {auth_context.user.uid} due to {e} ")
        raise HTTPException(
            status_code=500, detail="Unable to initiate payment")


def _initiate_withdrawal(transaction: Transaction, auth_context: AuthenticationContext, bank_account: BankAccount):

    try:

        # initiate the transaction on flutterwave

        payment_payload = {

            "reference": transaction.reference,
            "amount": transaction.amount,
            "debit_currency": transaction.currency,
            "account_bank": bank_account.bank_code,
            "account_number": bank_account.account_number,
            "narration": f"{transaction.description}",
            "callback_url": f"{settings.server_url}/wallet/withdrawal/complete",
            "customer": {
                "email": auth_context.user.email,
            },

            "customizations": {
                "title": "SafeHome",
                "description": "Complete your Withdrawal from SafeHome",
            },

        }

        url = make_url(Endpoints.flutterwave_transfers.value)

        headers = {
            "Authorization": f"Bearer {settings.flutterwave_secret_key}",
        }

        ok, status, data = make_req(
            url, "POST", headers=headers, body=payment_payload)

        success = handle_response(ok, status, data)

        if not success:
            logger.error(
                f"Unable to initiate withdrawal payment for user {auth_context.user.uid} due to {ok} {status} {data} ")
            raise HTTPException(
                status_code=500, detail="Unable to initiate payment")

        result = data["data"]

        return result

    except Exception as e:
        logger.error(
            f"Unable to initiate withdrawal payment for user {auth_context.user.uid} due to {e} ")
        raise HTTPException(
            status_code=500, detail="Unable to initiate payment")
