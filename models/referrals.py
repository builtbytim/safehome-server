from pydantic import BaseModel, Field, EmailStr, validator, constr
from enum import Enum
from typing import Union
from libs.utils.pure_functions import *
from libs.config.settings import get_settings
from pydantic_settings import SettingsConfigDict
import random
import string


settings = get_settings()


def generate_referral_code(length=6):
    characters = string.ascii_letters + string.digits
    referral_code = ''.join(random.choice(characters) for _ in range(length))
    return referral_code


class UserReferralProfile(BaseModel):
    user_id:  str = Field(min_length=8, alias="userId")
    referral_code:  str = Field(
        min_length=6, alias="referralCode")
    referral_link:  str = Field(min_length=8, alias="referralLink")
    referral_count:  int = Field(default=0, alias="referralCount")
    referral_bonus:  float = Field(default=0.0, alias="referralBonus")
    is_active:  bool = Field(default=True, alias="isActive")
    total_referral_bonus:  float = Field(
        default=0.0, alias="totalReferralBonus")
    created_at:  float = Field(
        default_factory=get_utc_timestamp, alias="createdAt")
    updated_at:  float = Field(
        default_factory=get_utc_timestamp, alias="updatedAt")

    model_config = SettingsConfigDict(populate_by_name=True)


class Referral(BaseModel):
    referred_by:  str = Field(min_length=8, alias="referredBy")
    referred_user_id:  str = Field(min_length=8, alias="referredUserId")
    referred_user_email:  EmailStr = Field(
        alias="referredUserEmail")
    referred_user_name:  str = Field(
        min_length=3, alias="referredUserName")
    referral_code:  str = Field(min_length=4, alias="referralCode")
    referral_link:  str = Field(min_length=8, alias="referralLink")
    confirmed:  bool = Field(default=False)
    referral_bonus:  float = Field(default=0.0, alias="referralBonus")
    created_at:  float = Field(
        default_factory=get_utc_timestamp, alias="createdAt")
    updated_at:  float = Field(
        default_factory=get_utc_timestamp, alias="updatedAt")

    model_config = SettingsConfigDict(populate_by_name=True)
