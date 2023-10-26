from pydantic import BaseModel, Field, validator
from pydantic_settings import SettingsConfigDict
from enum import Enum
from libs.utils.pure_functions import *
from libs.utils.security import decrypt_string
from libs.config.settings import get_settings
from pydantic_settings import SettingsConfigDict


settings = get_settings()


class FromLastNTime(str, Enum):
    last_7_days = "7_days"
    last_14_days = "14_days"
    last_1_day = "1_day"
    last_12_hours = "12_hours"
    last_1_hour = "1_hour"
    last_15_mins = "15_minutes"
    all_time = "all_time"


class CardTypes(str, Enum):
    VISA = "VISA"
    MASTERCARD = "MASTERCARD"
    VERVE = "VERVE"


# Wallet for each user's  on-platform wallet
class Wallet(BaseModel):
    uid:  str = Field(default_factory=get_uuid4)
    user_id:  str = Field(alias="userId")
    balance:  float = Field(default=0.0, ge=0.0)
    currency: str = Field(default=settings.default_currency)
    last_transaction_at: float = Field(
        default_factory=get_utc_timestamp, alias="lastTransactionAt")
    is_active: bool = Field(default=False, alias="isActive")
    created_at:  float = Field(
        default_factory=get_utc_timestamp, alias="createdAt")
    updated_at:  float = Field(
        default_factory=get_utc_timestamp, alias="updatedAt")
    total_amount_deposited: float = Field(
        default=0.0, alias="totalAmountDeposited")
    total_amount_withdrawn: float = Field(
        default=0.0, alias="totalAmountWithdrawn")
    total_amount_invested: float = Field(
        default=0.0, alias="totalAmountInvested")
    total_amount_invested_withdrawn: float = Field(
        default=0.0, alias="totalAmountInvestedWithdrawn")
    total_amount_saved: float = Field(default=0.0, alias="totalAmountSaved")
    total_amount_saved_withdrawn: float = Field(
        default=0.0, alias="totalAmountSavedWithdrawn")

    model_config = SettingsConfigDict(populate_by_name=True)

    # make balance always 2 decimal places when serializing
    @validator('balance')
    def balance_must_be_2dp(cls, v):
        return round(v, 2)


class DebitCardInput(BaseModel):
    card_number: str = Field(alias="cardNumber", min_length=16, max_length=16)
    expiry_month: str = Field(alias="expiryMonth", min_length=2, max_length=2)
    expiry_year: str = Field(alias="expiryYear", min_length=2, max_length=2)
    cvv: str = Field(alias="cvv", min_length=3, max_length=3)
    card_type: CardTypes = Field(alias="cardType", )

    model_config = SettingsConfigDict(populate_by_name=True)

    @validator("card_number")
    def validate_card_number(cls, v):
        if not v.isdigit():
            raise ValueError("Card number must be numeric")
        return v

    @validator("expiry_month")
    def validate_expiry_month(cls, v):
        if not v.isdigit():
            raise ValueError("Expiry month must be numeric")
        return v

    @validator("expiry_year")
    def validate_expiry_year(cls, v):
        if not v.isdigit():
            raise ValueError("Expiry year must be numeric")
        return v

    @validator("cvv")
    def validate_cvv(cls, v):
        if not v.isdigit():
            raise ValueError("CVV must be numeric")
        return v


class DebitCard(BaseModel):
    card_number: str = Field(alias="cardNumber", )
    card_name: str = Field(alias="cardName", default="")
    expiry_month: str = Field(alias="expiryMonth", )
    expiry_year: str = Field(alias="expiryYear", )
    cvv: str = Field(alias="cvv",)
    card_type: str = Field(alias="cardType", )
    uid: str = Field(default_factory=get_uuid4)
    user_id: str = Field(alias="userId")
    wallet: str = Field(alias="wallet")
    surfix: str = Field(alias="surfix")
    is_active: bool = Field(default=True, alias="isActive")
    created_at: float = Field(
        default_factory=get_utc_timestamp, alias="createdAt")
    updated_at: float = Field(
        default_factory=get_utc_timestamp, alias="updatedAt")

    model_config = SettingsConfigDict(populate_by_name=True)


class DecryptedDebitCard(DebitCard):

    model_config = SettingsConfigDict(populate_by_name=True)

    # overload model dump to decrypt values when json conversion is needed

    def model_dump(self, *args, **kwargs):
        temp = super().model_dump(*args, **kwargs)

        if False:
            temp.update({
                "card_number": decrypt_string(self.card_number),
                "expiry_month": decrypt_string(self.expiry_month),
                "expiry_year": decrypt_string(self.expiry_year),
                "cvv": decrypt_string(self.cvv)
            })

        else:
            temp.update({
                "cardNumber": decrypt_string(self.card_number),
                "expiryMonth": decrypt_string(self.expiry_month),
                "expiryYear": decrypt_string(self.expiry_year),
                "cvv": decrypt_string(self.cvv),
                "cardType": decrypt_string(self.card_type),

            })

        return temp


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
