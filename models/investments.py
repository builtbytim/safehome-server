from pydantic import BaseModel, Field
from enum import Enum
from pydantic_settings import SettingsConfigDict
from libs.utils.pure_functions import *


class OwnersClubs(str, Enum):
    land_owners_club = "land_owners_club"
    home_owners_club = "home_owners_club"
    office_owners_club = "office_owners_club"
    all = "all"


class FundSource(str, Enum):
    wallet = "wallet"
    bank_account = "bank_account"


class AssetProps(BaseModel):
    investment_id: str = Field(alias="investmentId")
    investment_exit: str = Field(alias="investmentExit")
    maturity_date: str = Field(alias="maturityDate")
    roi: str = Field(alias="roi")

    model_config = SettingsConfigDict(populate_by_name=True)


class InvestibleAssetBase(BaseModel):
    asset_name: str = Field(min_length=3, max_length=64, alias="assetName")
    location: str | None = Field(min_length=3, max_length=256, default=None)
    price: float = Field(gt=0.0)
    units: int = Field(ge=0)
    duration: float = Field(ge=0, default=0.0)
    available_units: int = Field(ge=0, alias="availableUnits", default=0)
    about: str | None = Field(default=None)
    owner_club: OwnersClubs = Field(alias="ownerClub")

    props:  AssetProps

    model_config = SettingsConfigDict(populate_by_name=True)


class InvestibleAssetInput(InvestibleAssetBase):
    props: AssetProps


class InvestibleAsset(InvestibleAssetBase):
    uid: str = Field(default_factory=get_uuid4)
    investor_count: int = Field(ge=0, alias="investorCount")
    investors: list[str] = Field(default=[], alias="investors")
    cover_image_url: str | None = Field(default=None, alias="coverImageUrl")
    is_active: bool = True
    sold_out: bool = Field(default=False, alias="soldOut")
    asset_image_urls: list[str] | None = Field(default=None,
                                               min_length=0, alias="assetImageUrls")
    created_at: float = Field(
        default_factory=get_utc_timestamp, alias="createdAt")
    updated_at: float = Field(
        default_factory=get_utc_timestamp, alias="updatedAt")
    author: str | None = Field(default=None)

    def get_price_per_unit(self):
        return round(self.price / self.units, 2)

    def model_dump(self, *args, **kwargs):
        temp = super().model_dump(*args, **kwargs)
        temp.update({
            "pricePerUnit": self.get_price_per_unit()
        })
        return temp

    model_config = SettingsConfigDict(populate_by_name=True)


class InvestmentBase(BaseModel):
    asset_uid: str = Field(alias="assetUid")
    units: int = Field(ge=0)

    model_config = SettingsConfigDict(populate_by_name=True)


class InvestmentInput(InvestmentBase):
    fund_source: FundSource = Field(alias="fundSource")

    model_config = SettingsConfigDict(populate_by_name=True)


class Investment(InvestmentBase):
    uid: str = Field(default_factory=get_uuid4)
    investor_uid: str = Field(alias="investorUid")
    payment_reference: str | None = Field(
        alias="paymentReference", default=None)
    amount: float = Field(gt=0.0)
    roi: str
    investment_exit: str = Field(alias="investmentExit")
    investment_exit_date: float = Field(
        alias="investmentExitDate")
    is_active: bool = Field(alias="isActive", default=False)
    completed: bool = False
    cashed_out: bool = Field(alias="cashedOut", default=False)
    created_at: float = Field(
        default_factory=get_utc_timestamp, alias="createdAt")
    updated_at: float = Field(
        default_factory=get_utc_timestamp, alias="updatedAt")

    model_config = SettingsConfigDict(populate_by_name=True)


class InvestmentWithAsset(Investment):
    asset_info:  InvestibleAsset | None = Field(
        alias="assetInfo", default=None)

    model_config = SettingsConfigDict(populate_by_name=True)
