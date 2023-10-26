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

USER_EXLUCUDE_FIELDS = {"password_hash",
                        "is_superuser",  "is_staff", "is_admin", "kyc_info",  "password_reset_at", "password_changed_at", }


def passes_phonenumber_test(value):
    """checks whether  a phone number is valid or not"""

    try:
        res = phonenumbers.parse(value, "NG")
        return phonenumbers.is_valid_number(res)
    except phonenumbers.NumberParseException:
        return False


class SecurityQuestions(str, Enum):
    MOTHERS_MAIDEN_NAME = "WhatIsYourMotherSMaidenName"
    BORN_CITY = "InWhichCityWereYouBorn"
    FAVORITE_PET_NAME = "WhatIsYourFavoritePetSName"
    FAVORITE_TEACHER = "WhoIsYourFavoriteTeacher"
    FIRST_CAR_NAME = "WhatIsTheNameOfYourFirstCar"


class States(str, Enum):
    ABIA = "ABIA"
    ADAMAWA = "ADAMAWA"
    AKWA_IBOM = "AKWA_IBOM"
    ANAMBRA = "ANAMBRA"
    BAUCHI = "BAUCHI"
    BAYELSA = "BAYELSA"
    BENUE = "BENUE"
    BORNO = "BORNO"
    CROSS_RIVER = "CROSS_RIVER"
    DELTA = "DELTA"
    EBONYI = "EBONYI"
    EDO = "EDO"
    EKITI = "EKITI"
    ENUGU = "ENUGU"
    FCT = "FCT"
    GOMBE = "GOMBE"
    IMO = "IMO"
    JIGAWA = "JIGAWA"
    KADUNA = "KADUNA"
    KANO = "KANO"
    KATSINA = "KATSINA"
    KEBBI = "KEBBI"
    KOGI = "KOGI"
    KWARA = "KWARA"
    LAGOS = "LAGOS"
    NASARAWA = "NASARAWA"
    NIGER = "NIGER"
    OGUN = "OGUN"
    ONDO = "ONDO"
    OSUN = "OSUN"
    OYO = "OYO"
    PLATEAU = "PLATEAU"
    RIVERS = "RIVERS"
    SOKOTO = "SOKOTO"
    TARABA = "TARABA"
    YOBE = "YOBE"
    ZAMFARA = "ZAMFARA"


class UserRoles(str, Enum):
    ADMIN = "ADMIN"
    USER = "USER"
    GUEST = "GUEST"
    NONE = "NONE"


class KYCDocumentType(str, Enum):
    BVN = "BVN"
    NIN = "NIN"
    PASSPORT = "PASSPORT"
    NATIONAL_ID = "NATIONAL_ID"
    DRIVERS_LICENSE = "DRIVERS_LICENSE"


class KYCStatus(str, Enum):
    APPROVED = "APPROVED"
    PENDING = "PENDING"
    REJECTED = "REJECTED"


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


class Genders(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"


class ActionIdentifiers(str, Enum):
    RESET_PASSWORD_VIA_EMAIL = "RESET_PASSWORD_VIA_EMAIL"
    RESET_PASSWORD_VIA_SMS = "RESET_PASSWORD_VIA_SMS"
    VERIFY_EMAIL = "VERIFY_EMAIL"
    VERIFY_PHONE = "VERIFY_PHONE"
    VERIFY_KYC_DOCUMENT = "VERIFY_KYC_DOCUMENT"
    ADD_KYC_INFO = "ADD_KYC_INFO"
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


class PasswordChangeInput(BaseModel):
    current_password:  str = Field(min_length=8, alias="currentPassword")
    new_password:  str = Field(min_length=8, alias="newPassword")

    model_config = SettingsConfigDict(populate_by_name=True)


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


class KYCVerificationInput(BaseModel):
    residential_address:  str = Field(
        min_length=10, max_length=100, alias="residentialAddress")

    state: States
    document_type: KYCDocumentType = Field(alias="documentType")
    IDNumber:  str = Field(min_length=10,
                           alias="IDNumber")
    BVN: str = Field(min_length=11,
                     max_length=11, alias="BVN")

    model_config = SettingsConfigDict(populate_by_name=True)

    @validator('BVN', pre=False, always=True)
    def validate_bvn(cls, v):
        value = v

        if not value.isdigit():
            raise ValueError("BVN must be digits")

        return value

    # @validator('NIN', pre=False, always=True)
    # def validate_nin(cls, v, values):
    #     value = v

    #     if value is None and values.get("documentType") == KYCDocumentType.NIN:
    #         raise ValueError("NIN is required")

    #     if value is None:
    #         return value

    #     if not value.isdigit():
    #         raise ValueError("NIN must be digits")

    #     return value


class NextOfKinInput(BaseModel):
    first_name: str = Field(
        min_length=2, max_length=35, alias="firstName")
    last_name: str = Field(
        min_length=2, max_length=35, alias="lastName")
    phone: str = Field(min_length=10, max_length=15)
    email: EmailStr
    relationship: str = Field(min_length=2, max_length=35)
    replace: bool = Field(default=False)

    model_config = SettingsConfigDict(populate_by_name=True)


class NextOfKinInfo(NextOfKinInput):
    uid: str = Field(default_factory=get_uuid4)
    user_id: str = Field(min_length=32, alias="userId")
    created_at: float = Field(
        default_factory=get_utc_timestamp, alias="createdAt")
    updated_at: float = Field(
        default_factory=get_utc_timestamp, alias="updatedAt")

    model_config = SettingsConfigDict(populate_by_name=True)


class UserSecurityQuestions(BaseModel):
    question1: SecurityQuestions
    question2: SecurityQuestions
    answer1: str = Field(min_length=2)
    answer2: str = Field(min_length=2)

    model_config = SettingsConfigDict(populate_by_name=True)


class UserSecurityQuestionsInput(UserSecurityQuestions):
    replace: bool = Field(default=False)

    model_config = SettingsConfigDict(populate_by_name=True)


class UserKYCInfo(BaseModel):
    residential_address:  str = Field(
        min_length=10, max_length=100, alias="residentialAddress")

    state: States
    document_type: KYCDocumentType = Field(alias="documentType")
    created_at:  float = Field(
        default_factory=get_utc_timestamp, alias="createdAt")
    BVN:  str = Field(min_length=11,  alias="BVN")
    IDNumber: str = Field(min_length=10, alias="IDNumber")
    document_url: str | None = Field(alias="documentUrl", default=None)
    approved:  bool = Field(default=False)
    flagged:  bool = Field(default=False)

    model_config = SettingsConfigDict(populate_by_name=True)


class PasswordResetStore(BaseModel):
    uid: str = Field(min_length=32, default_factory=get_uuid4)
    user_id: str = Field(min_length=32, alias="userId")
    new_password_hash: str = Field(min_length=32, alias="newPasswordHash")
    channel: PasswordResetChannels
    valid: bool = Field(default=True)
    token: str = Field(min_length=16, default_factory=get_random_string)
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

    gender:  Genders | None = None

    date_of_birth: float | None = Field(alias="dateOfBirth", default=None)

    phone: str = Field(min_length=10, max_length=15)

    # validate date of birth

    @validator("date_of_birth", pre=False, always=True)
    def enforce_age_constraints(cls, value):
        # age must be more than 18 years
        if value is not None:
            if not is_age_in_range(value, 18, 100):
                raise ValueError(
                    "You must be 18 years or older to use this service")
        return value

    @validator('email', pre=True, always=True)
    def normalize_email(cls, value):
        if value is not None:
            return value.lower()
        return value

    model_config = SettingsConfigDict(populate_by_name=True)


class UserUpdateModel(UserBaseModel):
    residential_address:  str = Field(
        min_length=10, max_length=100, alias="residentialAddress")
    state: States = Field(
        default=None,)

    model_config = SettingsConfigDict(populate_by_name=True)


class UserInputModel(UserBaseModel):
    password: str = Field(min_length=8, max_length=25)
    referralCode : str | None = None

    model_config = SettingsConfigDict(populate_by_name=True)


class UserOutputModel(UserBaseModel):
    uid: str = Field(default_factory=get_uuid4)
    role: UserRoles = Field(default=UserRoles.USER)
    kyc_info:  UserKYCInfo | None = Field(default=None, alias="kycInfo")
    security_questions: UserSecurityQuestions | None = Field(
        default=None, alias="securityQuestions")
    address: Union[str, None] = Field(
        default=None,  min_length=2, max_length=256)
    state: Union[str, None] = Field(
        default=None,  min_length=2, max_length=64)
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
    is_active: bool = Field(default=False, alias="isActive")
    created_at: float = Field(default_factory=time, alias="createdAt")
    last_login: Union[float, None] = Field(alias="lastLogin", default=None)
    has_paid_membership_fee: bool = Field(
        default=False, alias="hasPaidMembershipFee")
    true_last_login: Union[float, None] = Field(
        alias="trueLastLogin", default=None)
    updated_at: float = Field(default_factory=time, alias="updatedAt")
    profile_updated_at: float = Field(
        default_factory=get_utc_timestamp, alias="profileUpdatedAt")
    password_changed_at: float = Field(
        default_factory=get_utc_timestamp, alias="passwordChangedAt")
    password_reset_at: float = Field(
        default_factory=get_utc_timestamp, alias="passwordResetAt")

    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @validator('phone')
    def validate_phone(v):
        value = v

        if value is None:
            return value

        if not passes_phonenumber_test(value):
            raise ValueError("invalid phone number")

        return value

    model_config = SettingsConfigDict(populate_by_name=True)


class UserDBModel(UserOutputModel):
    password_hash:  str = Field(
        min_length=32, alias="passwordHash")

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
    user: UserDBModel | UserOutputModel

    def get_user_dict(self) -> dict:
        return self.user.model_dump(exclude=USER_EXLUCUDE_FIELDS)

    def get_full_name(self) -> str:
        return f"{self.user.first_name} {self.user.last_name}"
