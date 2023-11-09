from fastapi import APIRouter, HTTPException, Depends,  Request, Query
from fastapi.responses import RedirectResponse
from libs.config.settings import get_settings
from models.users import AuthenticationContext
from libs.db import _db, Collections
from libs.utils.api_helpers import find_record, update_record
from libs.utils.pagination import Paginator, PaginatedResult
from models.payments import *
from models.wallets import *
from libs.utils.pure_functions import *
from libs.huey_tasks.tasks import task_send_mail, task_create_notification
from models.notifications import NotificationTypes
from libs.deps.users import get_auth_context, get_user_wallet, only_paid_users, only_kyc_verified_users
from libs.logging import Logger
from libs.utils.flutterwave import _initiate_topup_payment, _verify_transaction, _get_supported_banks, _resolve_bank_account, _initiate_withdrawal
from libs.utils.security import encrypt_string
from libs.utils.pagination import Paginator, PaginatedResult


logger = Logger(f"{__package__}.{__name__}")

settings = get_settings()


router = APIRouter(responses={
    404: {"description": "The resource you requested does not exist!"}
}, tags=["Wallets"])


@router.post("/debit-cards", status_code=201, )
async def add_card(body:  DebitCardInput,  paid_membership_fee: bool = Depends(only_paid_users), auth_context: AuthenticationContext = Depends(get_auth_context), wallet:  Wallet = Depends(get_user_wallet)):

    card = DebitCard(
        user_id=auth_context.user.uid,
        wallet=wallet.uid,
        card_number=encrypt_string(body.card_number),
        expiry_month=encrypt_string(body.expiry_month),
        expiry_year=encrypt_string(body.expiry_year),
        cvv=encrypt_string(body.cvv),
        card_type=encrypt_string(body.card_type),
        surfix=body.card_number[-4:],
    )

    await _db[Collections.debitcards].insert_one(card.model_dump())

    return


@router.get("/debit-cards", status_code=200, response_model=PaginatedResult)
async def get_cards(auth_context: AuthenticationContext = Depends(get_auth_context),  paid_membership_fee: bool = Depends(only_paid_users), wallet:  Wallet = Depends(get_user_wallet)):

    page = 1
    limit = 100

    root_filter = {
        "wallet": wallet.uid,
    }

    filters = {
    }

    paginator = Paginator(
        col_name=Collections.debitcards,
        filters=filters,
        sort_field="created_at",
        top_down_sort=True,
        include_crumbs=True,
        per_page=limit,
        root_filter=root_filter,
    )

    return await paginator.get_paginated_result(page, DecryptedDebitCard)


@router.delete("/debit-cards/{card_id}", status_code=200)
async def delete_card(card_id: str, auth_context: AuthenticationContext = Depends(get_auth_context), wallet:  Wallet = Depends(get_user_wallet),  paid_membership_fee: bool = Depends(only_paid_users)):

    card: DebitCard = await find_record(DebitCard, Collections.debitcards, "uid", card_id, raise_404=False)

    if not card:
        logger.error(f"Card {card_id} not found")
        raise HTTPException(
            status_code=400, detail="Card specified does not exist.")

    if card.user_id != auth_context.user.uid:
        logger.error(
            f"Card {card_id} does not belong to user {auth_context.user.uid}")
        raise HTTPException(
            status_code=400, detail="Card specified does not belong to you.")

    if card.wallet != wallet.uid:
        logger.error(
            f"Card {card_id} does not belong to wallet {wallet.uid}")
        raise HTTPException(
            status_code=400, detail="Card specified does not belong to your wallet.")

    await _db[Collections.debitcards].delete_one({"uid": card_id})

    return


@router.post("/banks", status_code=201)
async def add_bank_account(body:  BankAccountInput,  paid_membership_fee: bool = Depends(only_paid_users), auth_context: AuthenticationContext = Depends(get_auth_context), wallet:  Wallet = Depends(get_user_wallet)):

    account_result = _resolve_bank_account(body.bank_code, body.account_number)
    banks_result = _get_supported_banks()

    bank_from_results = next(
        (bank for bank in banks_result if bank["code"] == body.bank_code), None)

    if not bank_from_results:
        logger.error(f"Invalid bank code - {body.bank_code}")
        raise HTTPException(
            status_code=400, detail="Invalid bank code")

    bank_account = BankAccount(
        user_id=auth_context.user.uid,
        wallet=wallet.uid,
        bank_name=bank_from_results["name"],
        account_name=account_result["account_name"],
        account_number=account_result["account_number"],
        bank_code=body.bank_code,
    )

    await _db[Collections.bank_accounts].insert_one(bank_account.model_dump())

    return


@router.get("/banks", status_code=201, response_model=list[BankAccount])
async def get_bank_accounts(auth_context: AuthenticationContext = Depends(get_auth_context),  paid_membership_fee: bool = Depends(only_paid_users), wallet:  Wallet = Depends(get_user_wallet)):

    bank_accounts = await _db[Collections.bank_accounts].find({"wallet": wallet.uid}).to_list(100)

    return bank_accounts


@router.get("/banks/supported", status_code=200, response_model=list[SupportedBank])
async def get_supported_banks(auth_context: AuthenticationContext = Depends(get_auth_context),  paid_membership_fee: bool = Depends(only_paid_users),):
    return _get_supported_banks()


@router.post("/banks/resolve", status_code=200, response_model=ResolveBankAccountOutput)
async def resolve_bank_account(body: BankAccountInput,  auth_context: AuthenticationContext = Depends(get_auth_context),  paid_membership_fee: bool = Depends(only_paid_users)):

    result = _resolve_bank_account(body.bank_code, body.account_number)

    resolved_bank = ResolveBankAccountOutput(
        **result
    )

    return resolved_bank


@router.delete("/banks/{bank_id}", status_code=200)
async def delete_bank_account(bank_id: str, auth_context: AuthenticationContext = Depends(get_auth_context), wallet:  Wallet = Depends(get_user_wallet),  paid_membership_fee: bool = Depends(only_paid_users)):

    bank_account: BankAccount = await find_record(BankAccount, Collections.bank_accounts, "uid", bank_id, raise_404=False)

    if not bank_account:
        logger.error(f"Bank account {bank_id} not found")
        raise HTTPException(
            status_code=400, detail="Bank account specified does not exist.")

    if bank_account.user_id != auth_context.user.uid:
        logger.error(
            f"Bank account {bank_id} does not belong to user {auth_context.user.uid}")
        raise HTTPException(
            status_code=400, detail="Bank account specified does not belong to you.")

    if bank_account.wallet != wallet.uid:
        logger.error(
            f"Bank account {bank_id} does not belong to wallet {wallet.uid}")
        raise HTTPException(
            status_code=400, detail="Bank account specified does not belong to your wallet.")

    if bank_account.is_active == False:
        logger.error(f"Bank account {bank_id} is inactive")
        raise HTTPException(
            status_code=400, detail="Bank account specified is inactive.")

    await _db[Collections.bank_accounts].delete_one({"uid": bank_id})

    return


@router.get("", status_code=200, response_model=Wallet)
async def get_wallet(auth_context: AuthenticationContext = Depends(get_auth_context), wallet:  Wallet = Depends(get_user_wallet),  paid_membership_fee: bool = Depends(only_paid_users)):

    if not wallet:
        logger.error(f"User {auth_context.user.uid} does not have a wallet")

        raise HTTPException(
            status_code=400, detail="You do not have a wallet yet! Please contact support.")

    return wallet


@router.get("/transactions", status_code=200, response_model=PaginatedResult)
async def get_wallet_transactions(page: int = Query(ge=1, default=1), limit: int = Query(ge=1, default=1), start_date: float | None = Query(alias="startDate", default=None), end_date: float | None = Query(alias="endDate", default=None), tx_type: str = Query(alias="type", default="all"), from_last: FromLastNTime | None = Query(alias="fromLast", default=None),  paid_membership_fee: bool = Depends(only_paid_users), match: str = Query(default=""), auth_context: AuthenticationContext = Depends(get_auth_context), wallet:  Wallet = Depends(get_user_wallet)):

    if not wallet:
        logger.error(f"User {auth_context.user.uid} does not have a wallet")

        raise HTTPException(
            status_code=400, detail="You do not have a wallet yet! Please contact support.")

    root_filter = {
        "wallet": wallet.uid,
    }

    if match:
        root_filter.update({"$or": [
            {"description": {"$regex": match, "$options": "i"}},
            {"type": {"$regex": match, "$options": "i"}},
        ]})

    filters = {
    }

    if tx_type != "all":
        filters["type"] = tx_type

    def get_time_delta(from_last: FromLastNTime):
        if from_last == FromLastNTime.last_7_days:
            return 7 * 24 * 60 * 60
        elif from_last == FromLastNTime.last_14_days:
            return 14 * 24 * 60 * 60
        elif from_last == FromLastNTime.last_1_day:
            return 24 * 60 * 60
        elif from_last == FromLastNTime.last_12_hours:
            return 12 * 60 * 60
        elif from_last == FromLastNTime.last_1_hour:
            return 60 * 60
        elif from_last == FromLastNTime.last_15_mins:
            return 15 * 60

    if from_last and from_last != FromLastNTime.all_time:
        filters["created_at"] = {
            "$gte": get_utc_timestamp() - get_time_delta(from_last),
            "$lte": get_utc_timestamp(),
        }

    if start_date and end_date:
        filters["created_at"] = {
            "$gte": float(start_date),
            "$lte": float(end_date),
        }

    paginator = Paginator(
        col_name=Collections.transactions,
        filters=filters,
        sort_field="created_at",
        top_down_sort=True,
        include_crumbs=True,
        per_page=limit,
        root_filter=root_filter,
    )

    return await paginator.get_paginated_result(page, Transaction, exclude_fields=["wallet"])


# get a single tx that belomgs to a user
@router.get("/transactions/{tx_ref}", status_code=200, response_model=Transaction)
async def get_wallet_transaction(tx_ref: str, paid_membership_fee: bool = Depends(only_paid_users), auth_context: AuthenticationContext = Depends(get_auth_context), wallet:  Wallet = Depends(get_user_wallet)):
    if not wallet:
        logger.error(f"User {auth_context.user.uid} does not have a wallet")

        raise HTTPException(
            status_code=400, detail="You do not have a wallet yet! Please contact support.")

    transaction: Transaction = await find_record(Transaction, Collections.transactions, "reference", tx_ref, raise_404=False)

    if not transaction:
        logger.error(f"Transaction {tx_ref} not found")
        raise HTTPException(
            status_code=400, detail="Transaction specified does not exist.")

    if transaction.wallet != wallet.uid:
        logger.error(
            f"Transaction {tx_ref} does not belong to wallet {wallet.uid}")
        raise HTTPException(
            status_code=400, detail="Transaction specified does not belong to your wallet.")

    return transaction


@router.post("/withdraw", status_code=200)
async def withdraw_from_wallet(body:  WithdrawalInput, kyced: bool = Depends(only_kyc_verified_users),  paid_membership_fee: bool = Depends(only_paid_users), auth_context: AuthenticationContext = Depends(get_auth_context), wallet:  Wallet = Depends(get_user_wallet)):

    if not wallet:
        logger.error(f"User {auth_context.user.uid} does not have a wallet")

        raise HTTPException(
            status_code=400, detail="You do not have a wallet yet! Please contact support.")

    # check if the destination bank exists and it belongs to the user

    bank_account: BankAccount = await find_record(BankAccount, Collections.bank_accounts, "uid", body.bank_id, raise_404=False)

    if not bank_account:
        logger.error(f"Bank account {body.bank_id} not found")
        raise HTTPException(
            status_code=400, detail="Bank account specified does not exist.")

    if bank_account.user_id != auth_context.user.uid:
        logger.error(
            f"Bank account {body.bank_id} does not belong to user {auth_context.user.uid}")
        raise HTTPException(
            status_code=400, detail="Bank account specified does not belong to you.")

    if bank_account.wallet != wallet.uid:
        logger.error(
            f"Bank account {body.bank_id} does not belong to wallet {wallet.uid}")
        raise HTTPException(
            status_code=400, detail="Bank account specified does not belong to your wallet.")

    if bank_account.is_active == False:
        logger.error(f"Bank account {body.bank_id} is inactive")
        raise HTTPException(
            status_code=400, detail="Bank account specified is inactive.")

    # confirm the user has the amount to withdraw

    if body.amount > wallet.balance:
        logger.error(f"Insufficient balance to withdraw {body.amount}")
        raise HTTPException(
            status_code=400, detail="You do not have enough balance to complete this withrawal.")

    transaction = Transaction(
        initiator=auth_context.user.uid,
        wallet=wallet.uid,
        amount=body.amount,
        direction=TransactionDirection.outgoing,
        type=TransactionType.withdrawal,
        description="Withdrawal",
        balance_before=wallet.balance,
        balance_after=wallet.balance - body.amount,
    )

    result = _initiate_withdrawal(transaction, auth_context, bank_account)

    tx_status = result["status"]

    if tx_status != "NEW":
        logger.error(
            f"Unable to initiate withdrawal for user {auth_context.user.uid} due to tx status {tx_status} ")
        raise HTTPException(
            status_code=500, detail="Unable to initiate withdrawal.")


@router.post("/top-up", status_code=200, response_model=TopupOutput)
async def topup_wallet(body:  TopupInput,  paid_membership_fee: bool = Depends(only_paid_users), auth_context: AuthenticationContext = Depends(get_auth_context), wallet:  Wallet = Depends(get_user_wallet)):

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
        description="Add Funds",
        balance_before=wallet.balance,
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

    if transaction.type != TransactionType.topup:
        logger.error(
            f"Transaction with reference {tx_ref} is not a topup transaction")
        return failed_redirect

    if transaction.direction != TransactionDirection.incoming:
        logger.error(
            f"Transaction with reference {tx_ref} is not an incoming transaction")
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

        # update  corresponding wallet

        wallet: Wallet = await find_record(Wallet, Collections.wallets, "uid", transaction.wallet)

        wallet.balance += transaction.amount

        transaction.balance_after = wallet.balance

        wallet.total_amount_deposited += transaction.amount
        wallet.last_transaction_at = transaction.created_at

        await update_record(Wallet, wallet.model_dump(), Collections.wallets, "uid", refresh_from_db=True)

        await update_record(Transaction, transaction.model_dump(), Collections.transactions, "reference", refresh_from_db=True)

        # send a notification

        task_create_notification(
            transaction.initiator,  NotificationTypes.wallet, "Added funds successfully", f"Your funding of {transaction.amount} was successful")

        return success_redirect

    else:

        # update the transaction status to failed

        transaction.status = TransactionStatus.failed

        await update_record(Transaction, transaction.model_dump(), Collections.transactions, "reference", refresh_from_db=True)

        return failed_redirect
