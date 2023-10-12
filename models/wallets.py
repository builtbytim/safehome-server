from pydantic import BaseModel, Field, EmailStr, validator, constr
from pydantic_settings import SettingsConfigDict
from enum import Enum
from libs.utils.pure_functions import *
from time import time
from libs.config.settings import get_settings
from pydantic_settings import SettingsConfigDict
import phonenumbers


settings = get_settings()


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
