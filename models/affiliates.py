from pydantic import BaseModel, Field, EmailStr
from libs.utils.pure_functions import *
from enum import Enum
from libs.config.settings import get_settings
from pydantic_settings import SettingsConfigDict
import random
import string


settings = get_settings()


def generate_referral_code(length=6):
    characters = string.ascii_letters + string.digits
    referral_code = ''.join(random.choice(characters) for _ in range(length))
    return referral_code


class AffiliateLevel(str, Enum):
    BRONZE = "BRONZE"
    SILVER = "SILVER"
    GOLD = "GOLD"


class AffiliateReferralCode(BaseModel):
    uid:  str = Field(min_length=8, default_factory=get_uuid4)
    code:  str = Field(min_length=4)
    count:  int = Field(default=0)
    is_active: bool = Field(default=True, alias="isActive")
    created_at:  float = Field(
        default_factory=get_utc_timestamp, alias="createdAt")
    updated_at:  float = Field(
        default_factory=get_utc_timestamp, alias="updatedAt")
    affiliate:  str = Field(min_length=8)
    affiliate_profile_id:  str = Field(
        min_length=8, alias="affiliateProfileId")
    bonus:  float = Field(default=0.0)
    total_bonus:  float = Field(default=0.0, alias="totalBonus")

    model_config = SettingsConfigDict(populate_by_name=True)

    @property
    def link(self):
        return f"{settings.landing_page_url}/a/{self.code}"

    def model_dump(self, by_alias=False, *args, **kwargs):

        temp = super().model_dump(by_alias=by_alias, *args, **kwargs)

        if by_alias:
            temp.update({
                "referralLink":  self.link
            })

        else:
            temp.update({
                "referral_link":  self.link
            })

        return temp


class AffiliateReferralCodeOutput(BaseModel):
    uid:  str = Field(min_length=8, default_factory=get_uuid4)
    code:  str = Field(min_length=4)
    count:  int = Field(default=0)
    is_active: bool = Field(default=True, alias="isActive")
    created_at:  float = Field(
        default_factory=get_utc_timestamp, alias="createdAt")
    updated_at:  float = Field(
        default_factory=get_utc_timestamp, alias="updatedAt")
    affiliate:  str = Field(min_length=8)
    affiliate_profile_id:  str = Field(
        min_length=8, alias="affiliateProfileId")
    bonus:  float = Field(default=0.0)
    total_bonus:  float = Field(default=0.0, alias="totalBonus")
    referral_link:  str = Field(min_length=8, alias="referralLink")

    model_config = SettingsConfigDict(populate_by_name=True)


class AffiliateProfile(BaseModel):
    uid:  str = Field(min_length=8, default_factory=get_uuid4)
    user_id:  str = Field(min_length=8, alias="userId")
    referral_codes:  list[AffiliateReferralCode] = Field(
        alias="referralCodes", default=[])
    level:  str | None = Field(default=None)
    created_at:  float = Field(
        default_factory=get_utc_timestamp, alias="createdAt")
    updated_at:  float = Field(
        default_factory=get_utc_timestamp, alias="updatedAt")

    @property
    def referral_count(self):
        return sum([x.count for x in self.referral_codes])

    @property
    def referral_bonus(self):
        return sum([x.bonus for x in self.referral_codes])

    @property
    def num_codes(self):
        return len(self.referral_codes)

    @property
    def total_referral_bonus(self):
        return sum([x.total_bonus for x in self.referral_codes])

    model_config = SettingsConfigDict(populate_by_name=True)

    def model_dump(self, by_alias=False, *args, **kwargs):

        temp = super().model_dump(by_alias=by_alias, *args, **kwargs)

        if by_alias:
            temp.update({
                "referralCount":  self.referral_count,
                "referralBonus":  self.referral_bonus,
                "numCodes":  self.num_codes,
                "totalReferralBonus":  self.total_referral_bonus,
            })

        else:
            temp.update({
                "referral_count":  self.referral_count,
                "referral_bonus":  self.referral_bonus,
                "num_codes":  self.num_codes,
                "total_referral_bonus":  self.total_referral_bonus,
            })

        return temp


class AffiliateProfileOutput(BaseModel):
    uid:  str = Field(min_length=8)
    user_id:  str = Field(min_length=8, alias="userId")
    referral_codes:  list[AffiliateReferralCode] = Field(
        alias="referralCodes")
    level:  AffiliateLevel | None = Field(default=None)
    created_at:  float = Field(
        default_factory=get_utc_timestamp, alias="createdAt")
    updated_at:  float = Field(
        default_factory=get_utc_timestamp, alias="updatedAt")
    referral_codes:  list[AffiliateReferralCodeOutput] = Field(
        min_length=1, alias="referralCodes")
    referral_count:  int = Field(alias="referralCount")
    referral_bonus:  float = Field(alias="referralBonus")
    num_codes:  int = Field(alias="numCodes")
    total_referral_bonus:  float = Field(alias="totalReferralBonus")

    model_config = SettingsConfigDict(populate_by_name=True)


class AffiliateReferral(BaseModel):
    uid:  str = Field(min_length=8, default_factory=get_uuid4)
    affiliate:  str = Field(min_length=8, alias="affiliate")
    referred_user_id:  str = Field(min_length=8, alias="referredUserId")
    referred_user_email:  EmailStr = Field(
        alias="referredUserEmail")
    referred_user_name:  str = Field(
        min_length=3, alias="referredUserName")
    referral_code_id:  str = Field(min_length=4, alias="referralCodeId")
    referral_link:  str = Field(min_length=8, alias="referralLink")
    confirmed:  bool = Field(default=False)
    referral_bonus:  float = Field(default=0.0, alias="referralBonus")
    created_at:  float = Field(
        default_factory=get_utc_timestamp, alias="createdAt")
    updated_at:  float = Field(
        default_factory=get_utc_timestamp, alias="updatedAt")

    model_config = SettingsConfigDict(populate_by_name=True)
