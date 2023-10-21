from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from pydantic_settings import SettingsConfigDict
from libs.utils.pure_functions import *
from enum import Enum


class NotificationTypes(str, Enum):
    system = "system"
    transaction = "transaction"
    investment = "investment"
    savings = "savings"
    wallet = "wallet"
    kyc = "kyc"
    account = "account"
    security = "security"
    support = "support"
    referral = "referral"


class NotificationPreferencesInput(BaseModel):
    email: bool = True
    push: bool = True
    sms: bool = False


class NotificationPreferences(NotificationPreferencesInput):
    uid: str = Field(alias="uid", default_factory=get_uuid4)
    user_id: str = Field(min_length=8, alias="userId")
    created_at: float = Field(
        default_factory=get_utc_timestamp, alias="createdAt")
    updated_at: float = Field(
        default_factory=get_utc_timestamp, alias="updatedAt")

    model_config = SettingsConfigDict(populate_by_name=True)


class NotificationInput(BaseModel):
    title: str
    body: str


class Notification(BaseModel):
    uid: str = Field(alias="uid", default_factory=get_uuid4)
    user_id: str = Field(min_length=8, alias="userId")
    notification_type: NotificationTypes = Field(alias="notificationType")
    title: str
    body: str
    created_at: float = Field(
        default_factory=get_utc_timestamp, alias="createdAt")
    updated_at: float = Field(
        default_factory=get_utc_timestamp, alias="updatedAt")
    read: bool = False
    read_at: float | None = Field(alias="readAt", default=None)
    read_by: str | None = Field(alias="readBy", default=None)
    read_by_name: str | None = Field(
        alias="readByName", default=None)
    read_by_avatar_url: str | None = Field(
        alias="readByAvatarUrl", default=None)

    model_config = SettingsConfigDict(populate_by_name=True)


class UserNotificationStats(BaseModel):
    unread_count: int = Field(alias="unreadCount")
    read_count: int = Field(alias="readCount")
    total_count: int = Field(alias="totalCount")

    model_config = SettingsConfigDict(populate_by_name=True)
