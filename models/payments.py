from pydantic import BaseModel, Field, EmailStr, validator, constr
from pydantic_settings import SettingsConfigDict
from enum import Enum
from libs.utils.pure_functions import *
from time import time
from libs.config.settings import get_settings
from pydantic_settings import SettingsConfigDict
import phonenumbers


settings = get_settings()


class TransactionStatus(str, Enum):
    pending = "pending"
    failed = "failed"
    successful = "successful"


class TransactionType(str, Enum):
    credit = "credit"
    debit = "debit"
    topup = "topup"
    withdrawal = "withdrawal"


class TransactionDirection(str, Enum):
    incoming = "incoming"
    outgoing = "outgoing"


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
    amount:  float = Field(ge=0.0)
    currency: str = Field(default=settings.default_currency)
    status: TransactionStatus = Field(default=TransactionStatus.pending)
    direction: TransactionDirection
    type: TransactionType
    description: str = Field(default="")
    created_at:  float = Field(
        default_factory=get_utc_timestamp, alias="createdAt")
    updated_at:  float = Field(
        default_factory=get_utc_timestamp, alias="updatedAt")

    model_config = SettingsConfigDict(populate_by_name=True)


# Transaction Model
class Transaction(BaseTransactionModel):
    pass

    model_config = SettingsConfigDict(populate_by_name=True)
