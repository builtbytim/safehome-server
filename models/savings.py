from pydantic import BaseModel, Field, validator
from enum import Enum
from pydantic_settings import SettingsConfigDict
from libs.utils.pure_functions import *
from .payments import FundSource
from .investments import InvestibleAsset


class PaymentModes(str, Enum):
    manual = "manual"
    auto = "auto"


class Intervals(str, Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    quarterly = "quarterly"
    yearly = "yearly"


class IntervalsToSeconds(str, Enum):
    daily = 86400
    weekly = 604800
    monthly = 2592000
    quarterly = 7776000
    yearly = 31536000


class UserSavingsStats(BaseModel):
    balance: float
    savings_count: int = Field(alias="savingsCount")
    goal_savings_balance: float = Field(alias="goalSavingsBalance")
    locked_savings_balance: float = Field(alias="lockedSavingsBalance")
    total_saved: float = Field(alias="totalSaved")
    total_withdrawn: float = Field(alias="totalWithdrawn")

    model_config = SettingsConfigDict(populate_by_name=True)


def is_valid_savings_plan_date_range(start_date:  float, end_date:  float, interval:  Intervals):

    diff = end_date - start_date
    threshold = float(IntervalsToSeconds[interval.name].value) * 2
    if diff <= threshold:
        return False

    return True


class GoalSavingsPlanInput(BaseModel):

    created_at:  float = Field(
        default_factory=get_utc_timestamp_with_zero_hours_mins_secs, alias="createdAt")
    goal_name: str = Field(min_length=3, max_length=64, alias="goalName")
    goal_amount: float = Field(gt=0.0, alias="goalAmount")
    payment_mode: PaymentModes = Field(alias="paymentMode")
    goal_image_url: str | None = Field(default=None, alias="goalImageUrl")
    goal_description: str | None = Field(
        alias="goalDescription", min_length=8, default=None)
    fund_source: FundSource = Field(alias="fundSource")
    interval: Intervals = Field(alias="interval")
    start_date: float = Field(alias="startDate")
    end_date: float = Field(alias="endDate")
    amount_to_save_at_interval: float = Field(
        gt=0.0, alias="amountToSaveAtInterval")

    model_config = SettingsConfigDict(populate_by_name=True)

    @validator("goal_amount")
    def goal_amount_must_be_2dp(cls, v):
        return round(v, 2)

    @validator("amount_to_save_at_interval")
    def amount_to_save_at_interval_must_be_2dp(cls, v):
        return round(v, 2)

    @validator("amount_to_save_at_interval")
    def amount_to_save_at_interval_must_be_less_than_goal_amount(cls, v, values, **kwargs):
        if v > values["goal_amount"]:
            raise ValueError(
                "Amount to save at interval must be less than goal amount")
        return v

    @validator("start_date")
    def start_date_must_be_today_or_later(cls, v, values):
        if v < values["created_at"]:
            raise ValueError("Start date must be today or later")
        return v

    @validator("end_date")
    def end_date_is_greater_than_start_date(cls, v, values, **kwargs):

        if v <= values["start_date"]:
            raise ValueError("End date must be greater than start date")

        return v

    @validator("end_date")
    def end_date_is_at_least_7_days_from_start_date(cls, v, values, **kwargs):
        if v < values["start_date"] + 604800:
            raise ValueError(
                "End date must be at least 7 days from start date")
        return v

    @validator("end_date")
    def validate_is_valid_savings_plan_date_range(cls, v, values, **kwargs):
        if not is_valid_savings_plan_date_range(values["start_date"], v, IntervalsToSeconds[values["interval"]]):
            raise ValueError(
                "Savings plan date range is too short. It must be at least twice the interval")
        return v


class GoalSavingsPlan(GoalSavingsPlanInput):
    uid: str = Field(alias="uid", default_factory=get_uuid4)
    cycles: float = Field(ge=1)
    is_active: bool = Field(default=True, alias="isActive")
    completed: bool = Field(default=False, alias="completed")
    withdrawn: bool = Field(default=False, alias="withdrawn")
    amount_saved: float = Field(ge=0.0, alias="amountSaved", default=0.0)
    amount_withdrawn: float = Field(
        ge=0.0, alias="amountWithdrawn", default=0.0)
    payment_references: list[str] = Field(
        default_factory=list, alias="paymentReferences")
    user_id: str = Field(alias="userId")
    wallet_id: str = Field(alias="walletId")
    updated_at:  float = Field(
        default_factory=get_utc_timestamp, alias="updatedAt")

    model_config = SettingsConfigDict(populate_by_name=True)


class FundSavingsInput(BaseModel):
    amount_to_add: float = Field(gt=0.0, alias="amountToAdd")
    fund_source: FundSource = Field(alias="fundSource")
    savings_id: str = Field(alias="savingsId")

    model_config = SettingsConfigDict(populate_by_name=True)


# ---------------------------------------------


class LockedSavingsPlanInput(BaseModel):
    payment_mode: PaymentModes = Field(alias="paymentMode")
    fund_source: FundSource = Field(alias="fundSource")
    interval: Intervals = Field(alias="interval")
    asset_uid: str = Field(alias="assetUid")
    lock_duration_in_months: int = Field(
        ge=1, le=6, alias="lockDurationInMonths")
    amount_to_save_at_interval: float = Field(
        gt=0.0, alias="amountToSaveAtInterval")

    model_config = SettingsConfigDict(populate_by_name=True)

    @validator("amount_to_save_at_interval")
    def amount_to_save_at_interval_must_be_2dp(cls, v):
        return round(v, 2)


class LockedSavingsPlan(LockedSavingsPlanInput):
    lock_name: str = Field(min_length=3, max_length=64, alias="lockName")
    uid: str = Field(alias="uid", default_factory=get_uuid4)
    is_active: bool = Field(default=True, alias="isActive")
    completed: bool = Field(default=False, alias="completed")
    invested: bool = Field(default=False, alias="invested")
    ready_for_investment: bool = Field(
        default=False, alias="readyForInvestment")
    amount_saved: float = Field(ge=0.0, alias="amountSaved", default=0.0)
    payment_references: list[str] = Field(
        default_factory=list, alias="paymentReferences")
    user_id: str = Field(alias="userId")
    wallet_id: str = Field(alias="walletId")
    asset_info: InvestibleAsset | None = Field(
        alias="assetInfo", default=None)
    created_at:  float = Field(
        default_factory=get_utc_timestamp, alias="createdAt")
    updated_at:  float = Field(
        default_factory=get_utc_timestamp, alias="updatedAt")

    model_config = SettingsConfigDict(populate_by_name=True)
