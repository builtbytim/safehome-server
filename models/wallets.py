from pydantic import BaseModel, Field, EmailStr, validator, constr
from pydantic_settings import SettingsConfigDict
from enum import Enum
from libs.utils.pure_functions import *
from time import time
from libs.config.settings import get_settings
from pydantic_settings import SettingsConfigDict
import phonenumbers


settings = get_settings()


class FromLastNTime(str, Enum):
    last_7_days = "7_days"
    last_14_days = "14_days"
    last_1_day = "1_day"
    last_12_hours = "12_hours"
    last_1_hour = "1_hour"
    last_15_mins = "15_minutes"
    all_time = "all_time"


# Wallet for each user's  on-platform wallet
class Wallet(BaseModel):
    uid:  str = Field(default_factory=get_uuid4)
    user_id:  str = Field(alias="userId")
    balance:  float = Field(default=0.0, ge=0.0,)
    currency: str = Field(default=settings.default_currency)
    last_transaction_at: float = Field(
        default_factory=get_utc_timestamp, alias="lastTransactionAt")
    is_active: bool = Field(default=True, alias="isActive")
    created_at:  float = Field(
        default_factory=get_utc_timestamp, alias="createdAt")
    updated_at:  float = Field(
        default_factory=get_utc_timestamp, alias="updatedAt")

    model_config = SettingsConfigDict(populate_by_name=True)


class BankAccountInput(BaseModel):
    bank_code:  str = Field(alias="bankCode")
    account_number:  str = Field(alias="accountNumber")

    model_config = SettingsConfigDict(populate_by_name=True)


class SupportedBank(BaseModel):
    code: str
    name: str

    model_config = SettingsConfigDict(populate_by_name=True)


class ResolveBankAccountOutput(BaseModel):
    account_number:  str = Field(alias="accountNumber")
    account_name:  str = Field(alias="accountName")

    model_config = SettingsConfigDict(populate_by_name=True)


class BankAccount(BankAccountInput):
    uid: str = Field(default_factory=get_uuid4, min_length=8)
    user_id:  str = Field(alias="userId")
    wallet:  str = Field(alias="wallet")
    bank_name:  str = Field(alias="bankName")
    account_name:  str = Field(alias="accountName")
    is_active: bool = Field(default=True, alias="isActive")
    created_at:  float = Field(
        default_factory=get_utc_timestamp, alias="createdAt")
    updated_at:  float = Field(
        default_factory=get_utc_timestamp, alias="updatedAt")

    model_config = SettingsConfigDict(populate_by_name=True)
