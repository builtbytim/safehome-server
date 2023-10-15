from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import RedirectResponse
from libs.config.settings import get_settings
from models.users import AuthenticationContext
from libs.db import _db, Collections
from libs.utils.api_helpers import find_record, update_record
from models.payments import *
from models.investments import *
from models.wallets import Wallet
from libs.utils.pure_functions import *
from libs.utils.pagination import Paginator, PaginatedResult
from libs.huey_tasks.tasks import task_send_mail
from libs.deps.users import get_auth_context, get_user_wallet
from libs.logging import Logger


logger = Logger(f"{__package__}.{__name__}")


settings = get_settings()


router = APIRouter(responses={
    404: {"description": "The resource you requested does not exist!"}
}, tags=["Investments"])


@router.post("/assets", status_code=200, response_model=InvestibleAsset)
async def create_investible_asset(body: InvestibleAssetInput, auth_context: AuthenticationContext = Depends(get_auth_context), user_wallet: Wallet = Depends(get_user_wallet)):

    if not user_wallet:
        raise HTTPException(status_code=400,
                            detail="You cannot create an investment asset as you do not have a wallet.")

    asset_props = AssetProps(
        **body.props.model_dump(),
    )

    # create the investment
    investment = InvestibleAsset(
        **body.model_dump(), investor_count=0, cover_image_url=None, asset_image_urls=[], author=auth_context.user.uid)

    await _db[Collections.investible_assets].insert_one(investment.model_dump())

    return InvestibleAsset(**investment.model_dump())


@router.get("/assets", status_code=200, response_model=PaginatedResult)
async def get_investible_assets(page: int = 1, limit: int = 10, owners_club:  OwnersClubs = Query(default=OwnersClubs.all, alias="ownerClub"), auth_context: AuthenticationContext = Depends(get_auth_context)):

    filters = {
        "is_active": True,
    }

    if owners_club != OwnersClubs.all:
        filters["owner_club"] = owners_club.value

    paginator = Paginator(
        col_name=Collections.investible_assets,
        filters=filters,
        sort_field="asset_name",
        top_down_sort=True,
        include_crumbs=True,
        per_page=limit,
    )

    return await paginator.get_paginated_result(page, InvestibleAsset)


@router.get("/assets/{uid}", status_code=200, response_model=InvestibleAsset)
async def get_investible_asset(uid: str, auth_context: AuthenticationContext = Depends(get_auth_context)):

    asset = await _db[Collections.investible_assets].find_one({"uid": uid})

    if not asset:
        raise HTTPException(status_code=404,
                            detail="The investment asset you requested does not exist!")

    return InvestibleAsset(**asset)
