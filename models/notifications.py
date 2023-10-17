from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from pydantic_settings import SettingsConfigDict
from libs.utils.pure_functions import *


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
    title: str
    body: str
    created_at: float = Field(
        default_factory=get_utc_timestamp, alias="createdAt")
    updated_at: float = Field(
        default_factory=get_utc_timestamp, alias="updatedAt")
    read: bool = False
    read_at: Optional[float] = Field(alias="readAt")
    read_by: Optional[str] = Field(alias="readBy")
    read_by_name: Optional[str] = Field(alias="readByName")
    read_by_avatar_url: Optional[str] = Field(alias="readByAvatarUrl")

    model_config = SettingsConfigDict(populate_by_name=True)



class UserNotificationStats(BaseModel):
    unread_count: int = Field(alias="unreadCount")
    read_count: int = Field(alias="readCount")
    total_count: int = Field(alias="totalCount")

    model_config = SettingsConfigDict(populate_by_name=True)
    
