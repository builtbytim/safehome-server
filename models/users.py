from pydantic import BaseModel, Field, EmailStr, validator, constr
from enum import Enum
from typing import Union
from libs.utils.pure_functions import *
from libs.db import _db, Collections
from time import time
from libs.config.settings import get_settings
from pydantic_settings import SettingsConfigDict
import phonenumbers


settings = get_settings()


def passes_phonenumber_test(value):
    """checks whether  a phone number is valid or not"""

    try:
        res = phonenumbers.parse(value, "NG")
        return phonenumbers.is_valid_number(res)
    except phonenumbers.NumberParseException:
        return False


class UserRoles(str, Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"
    NONE = "none"


class KYCStatus(str, Enum):
    APPROVED = "approved"
    PENDING = "pending"
    REJECTED = "rejected"


class AuthProviders(str, Enum):
    GOOGLE = "GOOGLE"
    FACEBOOK = "FACEBOOK"
    DEFAULT = "DEFAULT"


class Genders(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"


class Channels(str, Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"


class PasswordResetChannels(str, Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"


class ActionIdentifiers(str, Enum):
    RESET_PASSWORD_VIA_EMAIL = "RESET_PASSWORD_VIA_EMAIL"
    RESET_PASSWORD_VIA_SMS = "RESET_PASSWORD_VIA_SMS"
    VERIFY_EMAIL = "VERIFY_EMAIL"
    VERIFY_PHONE = "VERIFY_PHONE"
    VERIFY_KYC_DOCUMENT = "VERIFY_KYC_DOCUMENT"
    VERIFY_KYC_PHOTO = "VERIFY_KYC_PHOTO"
    AUTHENTICATION = "AUTHENTICATION"


class DocumentTypes(str, Enum):
    PASSPORT = "PASSPORT"
    NATIONAL_ID = "NATIONAL_ID"
    DRIVERS_LICENSE = "DRIVERS_LICENSE"
    OTHER = "OTHER"


class QueueStatus(str, Enum):
    QUEUED = "QUEUED"
    FAILED = "FAILED"


class RequestEmailOrSMSVerificationInput(BaseModel):
    email: EmailStr
    channel: PasswordResetChannels


class RequestEmailOrSMSVerificationOutput(BaseModel):
    uid: str = Field(min_length=32)
    channel: PasswordResetChannels
    pk:  EmailStr | str


class PasswordResetSaveInput(BaseModel):
    uid: str = Field(min_length=32)
    token: str = Field(min_length=16)


class VerifyEmailOrSMSConfirmationInput(BaseModel):
    uid: str = Field(min_length=32)
    foreign_key: str = Field(min_length=3, alias="foreignKey")
    channel: PasswordResetChannels
    token: str = Field(min_length=6, max_length=32)


class RequestAccountConfirmationInput(BaseModel):
    uid: str = Field(min_length=32)
    channel: PasswordResetChannels


class RequestAccountConfirmationOutput(BaseModel):
    uid: str = Field(min_length=32)
    channel: PasswordResetChannels


class VerifyAccountConfirmationInput(BaseModel):
    uid: str = Field(min_length=32)
    channel: PasswordResetChannels
    token: str = Field(min_length=6, max_length=12)


class RequestPasswordResetInput(BaseModel):
    email: EmailStr
    new_password: str = Field(min_length=8, max_length=25, alias="newPassword")
    channel: PasswordResetChannels


class CreateUserViaGoogleAuthInput(BaseModel):
    token: str = Field(min_length=16)


class ConfirmPasswordResetInput(BaseModel):
    channel: PasswordResetChannels
    email: EmailStr
    token: str = Field(min_length=6, max_length=12)
    new_password: str = Field(min_length=8, max_length=25, alias="newPassword")

    model_config = SettingsConfigDict(populate_by_name=True)


class TOTPDB(BaseModel):
    uid: str = Field(default_factory=get_uuid4, min_length=32)
    action: ActionIdentifiers = Field(min_length=8, alias="action")
    foreign_key: str = Field(min_length=8, alias="foreignKey")
    key: str = Field(min_length=32)
    time_interval: int = Field(default=settings.otp_interval)
    created_at: float = Field(
        default_factory=get_utc_timestamp, alias="createdAt")

    model_config = SettingsConfigDict(populate_by_name=True)


class IdentityDocumentBase(BaseModel):
    document_type: DocumentTypes = Field(alias="documentType")
    document_number: str | None = Field(alias="documentNumber")

    model_config = SettingsConfigDict(populate_by_name=True)


class IdentityDocumentInput(IdentityDocumentBase):
    model_config = SettingsConfigDict(populate_by_name=True)


class IdentityDocument(IdentityDocumentBase):
    user_id: str = Field(alias="userId")
    uid: str = Field(default_factory=get_uuid4)
    document_url: str = Field(alias="documentUrl")
    created_at: float = Field(default_factory=time, alias="createdAt")
    updated_at: float = Field(default_factory=time, alias="updatedAt")

    model_config = SettingsConfigDict(populate_by_name=True)


class PasswordResetStore(BaseModel):
    uid: str = Field(min_length=32, default_factory=get_uuid4)
    user_id: str = Field(min_length=32, alias="userId")
    new_password_hash: str = Field(min_length=32, alias="newPasswordHash")
    channel: PasswordResetChannels
    valid: bool = Field(default=True)
    token: str = Field(min_length=6, max_length=32,
                       default_factory=get_random_string)
    created_at: float = Field(
        default_factory=get_utc_timestamp, alias="createdAt")

    model_config = SettingsConfigDict(populate_by_name=True)


class UserBaseModel(BaseModel):

    """ User Model """
    first_name: str = Field(
        min_length=2, max_length=35, alias="firstName")
    last_name: str = Field(
        min_length=2, max_length=35, alias="lastName")

    email: EmailStr

    phone: str = Field(min_length=10, max_length=15)

    @validator('email', pre=True, always=True)
    def normalize_email(cls, value):
        if value is not None:
            return value.lower()
        return value

    model_config = SettingsConfigDict(populate_by_name=True)


class UserInputModel(UserBaseModel):
    password: str = Field(min_length=8, max_length=25)

    model_config = SettingsConfigDict(populate_by_name=True)


class UserDBModel(UserBaseModel):
    uid: str = Field(default_factory=get_uuid4)
    role: UserRoles = Field(default=UserRoles.USER)
    kyc_document: IdentityDocument | None = Field(
        default=None, alias="kycDocument")
    kyc_photo: Union[str, None] = Field(default=None, alias="kycPhoto")
    address: Union[str, None] = Field(
        default=None,  min_length=2, max_length=35)
    country: Union[str, None] = Field(
        default=None,  min_length=2, max_length=35)
    avatar_url: Union[str, None] = Field(default=None, alias="avatarUrl")
    gender: Union[Genders, None] = None
    auth_provider: AuthProviders = Field(
        default=AuthProviders.DEFAULT, alias="authProvider")
    activation_channel: Union[PasswordResetChannels, None] = Field(
        default=None, alias="activationChannel")
    is_superuser: bool = Field(default=False, alias="isSuperuser")
    is_verified: bool = Field(default=False, alias="isVerified")
    email_verified: bool = Field(default=False, alias="emailVerified")
    kyc_status: KYCStatus | None = Field(default=None, alias="kycStatus")
    phone_verified: bool = Field(default=False, alias="phoneVerified")
    password_hash: Union[None, str] = Field(
        default=None, min_length=32, alias="passwordHash")
    is_active: bool = Field(default=False, alias="isActive")
    created_at: float = Field(default_factory=time, alias="createdAt")
    last_login: Union[float, None] = Field(alias="lastLogin", default=None)
    true_last_login: Union[float, None] = Field(
        alias="trueLastLogin", default=None)
    updated_at: float = Field(default_factory=time, alias="updatedAt")
    password_updated_at: float = Field(
        default_factory=time, alias="passwordUpdatedAt")

    @validator('phone')
    def validate_phone(v, values):
        value = v

        if value is None:
            return value

        if not passes_phonenumber_test(value):
            raise ValueError("invalid phone number")

        return value

    model_config = SettingsConfigDict(populate_by_name=True)


# Authentication Related Models


class AuthCode(BaseModel):
    uid: str = Field(default_factory=get_uuid4)
    user_id: str = Field(alias="userId")
    code: str = Field(default_factory=get_random_string)
    action: ActionIdentifiers = Field(min_length=8, alias="action")
    valid: bool = Field(default=True)
    created_at: float = Field(
        default_factory=get_utc_timestamp, alias="createdAt")

    model_config = SettingsConfigDict(populate_by_name=True)

    def verify(self,  user_id:  str, action: ActionIdentifiers) -> bool:
        return self.user_id == user_id and self.action == action

    def verify_action(self, action: ActionIdentifiers) -> bool:
        return self.action == action

    async def destroy(self):
        self.valid = False
        await _db[Collections.authcodes].update_one({"uid": self.uid}, {"$set": self.model_dump()})


class AuthSession(BaseModel):
    uid: str = Field(alias="uid")
    user_id: str = Field(alias="userId")
    is_valid: bool = Field(alias="isValid", default=True)
    created: float = Field(default_factory=get_utc_timestamp)
    duration_in_hours: float = Field(alias="durationInHours")
    last_used: Union[float, None] = Field(alias="lastUsed", default=None)
    usage_count: int = Field(alias="usageCount", default=0)

    model_config = SettingsConfigDict(populate_by_name=True)


class RequestAccessTokenInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=25)

    model_config = SettingsConfigDict(populate_by_name=True)


class AccessToken(BaseModel):
    access_token: str
    token_type: str = Field(default=settings.bearer_header_name)

    model_config = SettingsConfigDict(populate_by_name=True)


class Throttler(BaseModel):
    action: str
    author: str
    action_id: ActionIdentifiers = Field(alias="actionId")
    last_request: Union[float, None] = Field(alias="lastRequest", default=None)
    requests_count: int = Field(alias="requestsCount", default=0)
    pauseRequests: bool = Field(alias="pauseRequests", default=False)

    model_config = SettingsConfigDict(populate_by_name=True)


class AuthenticationContext(BaseModel):

    session: AuthSession
    user: UserDBModel
