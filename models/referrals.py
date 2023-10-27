from pydantic import BaseModel, Field, EmailStr
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

    @property
    def referral_link(self):
        return f"{settings.app_url}/r/{self.referral_code}"

    def model_dump(self, by_alias=False, *args, **kwargs):

        temp = super().model_dump(by_alias=by_alias, *args, **kwargs)

        if by_alias:
            temp.update({
                "referralLink":  self.referral_link
            })

        else:
            temp.update({
                "referral_link":  self.referral_link
            })

        return temp


class UserReferralProfileOutput(BaseModel):
    user_id:  str = Field(min_length=8, alias="userId")
    referral_code:  str = Field(
        min_length=6, alias="referralCode")
    referral_count:  int = Field(default=0, alias="referralCount")
    referral_bonus:  float = Field(default=0.0, alias="referralBonus")
    is_active:  bool = Field(default=True, alias="isActive")
    total_referral_bonus:  float = Field(
        default=0.0, alias="totalReferralBonus")
    created_at:  float = Field(
        default_factory=get_utc_timestamp, alias="createdAt")
    updated_at:  float = Field(
        default_factory=get_utc_timestamp, alias="updatedAt")

    referral_link:  str = Field(alias="referralLink")

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
