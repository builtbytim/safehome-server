from pydantic import BaseModel, Field, EmailStr, validator, constr
from enum import Enum
from typing import Union
from libs.utils.pure_functions import *
from libs.db import _db, Collections
from time import time
from libs.config.settings import get_settings
from pydantic_settings import SettingsConfigDict
import phonenumbers


class WaitlistEmailConfirmationInput(BaseModel):
    email:  EmailStr

    model_config = SettingsConfigDict(populate_by_name=True)


class WaitlistApplicationInput(BaseModel):
    full_name:  str = Field(min_length=3, alias="fullName")
    email:  EmailStr
    phone:  str | None = Field(min_length=10, max_length=15, default=None)
    code: str = Field(min_length=6, max_length=6, )
    uid: str = Field(min_length=16)

    model_config = SettingsConfigDict(populate_by_name=True)

    @validator("phone")
    def validate_phone(cls, v):
        try:
            phone_number = phonenumbers.parse(v, None)
            if not phonenumbers.is_valid_number(phone_number):
                raise ValueError("Invalid phone number")
        except Exception as e:
            raise ValueError("Invalid phone number")
        return v


class WaitlistApplication(WaitlistApplicationInput):
    uid: str = Field(default_factory=get_uuid4)
    created_at:  float = Field(default_factory=get_utc_timestamp)

    model_config = SettingsConfigDict(populate_by_name=True)

    @validator("phone")
    def validate_phone(cls, v):
        try:
            phone_number = phonenumbers.parse(v, None)
            if not phonenumbers.is_valid_number(phone_number):
                raise ValueError("Invalid phone number")
        except Exception as e:
            raise ValueError("Invalid phone number")
        return v
