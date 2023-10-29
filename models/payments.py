from pydantic import BaseModel, Field, EmailStr, validator, constr
from pydantic_settings import SettingsConfigDict
from enum import Enum
from libs.utils.pure_functions import *
from time import time
from libs.config.settings import get_settings
from pydantic_settings import SettingsConfigDict
import phonenumbers


settings = get_settings()


class FundSource(str, Enum):
    wallet = "wallet"
    bank_account = "bank"
    card = "card"
    bank = "bank"
    na = "na"


class TransactionStatus(str, Enum):
    pending = "pending"
    failed = "failed"
    successful = "successful"


class TransactionType(str, Enum):
    membership_fee = "membership_fee"
    credit = "credit"
    debit = "debit"
    topup = "topup"
    withdrawal = "withdrawal"
    investment = "investment"
    savings = "savings"
    savings_add_funds = "savings_add_funds"
    locked_savings_add_funds = "locked_savings_add_funds"
    referral_bonus_deposit = "referral_bonus_deposit"
    affiliate_bonus_deposit = "affiliate_bonus_deposit"


class TransactionDirection(str, Enum):
    incoming = "incoming"
    outgoing = "outgoing"


class WithdrawalInput(BaseModel):
    amount: float = Field(gt=0.0)
    bank_id: str = Field(alias="bankId")

    model_config = SettingsConfigDict(populate_by_name=True)


class WithdrawalOutput(BaseModel):
    redirect_url: str = Field(alias="redirectUrl")

    model_config = SettingsConfigDict(populate_by_name=True)


class TopupInput(BaseModel):
    amount: float = Field(gt=0.0)

    model_config = SettingsConfigDict(populate_by_name=True)


class TopupOutput(BaseModel):
    redirect_url: str = Field(alias="redirectUrl")

    model_config = SettingsConfigDict(populate_by_name=True)


# Base Transaction Model
class BaseTransactionModel(BaseModel):
    uid:  str = Field(default_factory=get_uuid4)
    initiator:  str = Field(alias="initiator")
    wallet:  str | None = Field(alias="wallet", default=None)
    reference:  str = Field(
        default_factory=get_tx_reference, alias="reference")
    tx_id: str | None = Field(alias="txId", default=None)
    fund_source: FundSource = Field(
        default=FundSource.bank_account, alias="fundSource")
    amount:  float = Field(ge=0.0)
    fee: float = Field(default=0.0)
    currency: str = Field(default=settings.default_currency)
    status: TransactionStatus = Field(default=TransactionStatus.pending)
    direction: TransactionDirection
    type: TransactionType
    description: str = Field(default="")
    balance_before: float = Field(default=0.0, alias="balanceBefore")
    balance_after: float = Field(default=0.0, alias="balanceAfter")
    created_at:  float = Field(
        default_factory=get_utc_timestamp, alias="createdAt")
    updated_at:  float = Field(
        default_factory=get_utc_timestamp, alias="updatedAt")

    model_config = SettingsConfigDict(populate_by_name=True)


# Transaction Model
class Transaction(BaseTransactionModel):
    pass

    model_config = SettingsConfigDict(populate_by_name=True)
