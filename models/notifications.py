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
