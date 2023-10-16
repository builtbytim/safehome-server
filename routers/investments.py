from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import RedirectResponse
from libs.config.settings import get_settings
from models.users import AuthenticationContext
from libs.db import _db, Collections
from libs.utils.api_helpers import find_record, update_record
from models.payments import Transaction
from libs.utils.flutterwave import _initiate_payment
from models.payments import *
from models.investments import *
from models.wallets import Wallet
from libs.utils.pure_functions import *
from libs.utils.pagination import Paginator, PaginatedResult
from libs.huey_tasks.tasks import task_send_mail
from libs.deps.users import get_auth_context, get_user_wallet
from libs.logging import Logger
import random

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
async def get_investible_assets(page: int = 1, limit: int = 10, owners_club:  OwnersClubs = Query(default=OwnersClubs.all, alias="ownersClub"), auth_context: AuthenticationContext = Depends(get_auth_context)):

    filters = {
        "is_active": True,
    }

    if owners_club != OwnersClubs.all:
        filters["owner_club"] = owners_club.value

    # print(filters)
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


@router.post("/assets/invest", status_code=200, response_model=TopupOutput | None)
async def create_investment(body: InvestmentInput, auth_context: AuthenticationContext = Depends(get_auth_context), user_wallet: Wallet = Depends(get_user_wallet)):

    if not user_wallet:
        raise HTTPException(status_code=400,
                            detail="You cannot create an investment as you do not have a wallet.")

    asset: InvestibleAsset = await find_record(InvestibleAsset, Collections.investible_assets, "uid", body.asset_uid, raise_404=False)

    if not asset:
        raise HTTPException(status_code=404,
                            detail="The investment asset you requested does not exist!")

    if body.units > asset.available_units:
        raise HTTPException(status_code=400,
                            detail=f"The investment asset you requested does not have enough units! Only {asset.available_units} units are available.")

    amount = round(body.units * (asset.price/asset.units), 2)

    transaction = Transaction(
        initiator=auth_context.user.uid,
        wallet=user_wallet.uid,
        amount=amount,
        direction=TransactionDirection.outgoing,
        type=TransactionType.investment,
        description=f"Investment in {asset.asset_name}",
    )

    investment = Investment(
        asset_uid=asset.uid,  units=body.units, investor_uid=auth_context.user.uid, payment_reference=transaction.reference, roi=asset.props.roi, investment_exit=asset.props.investment_exit, amount=amount, investment_exit_date=get_utc_timestamp())

    # if the funding source is the wallet then we need to check if the user has enough funds in the wallet

    if body.fund_source == FundSource.wallet:

        if user_wallet.balance < amount:
            raise HTTPException(status_code=400,
                                detail=f"You do not have enough funds in your wallet to make this investment. Please add funds to your wallet and try again.")

        transaction.tx_id = get_uuid4()
        transaction.status = TransactionStatus.successful

        user_wallet.balance -= amount

        # update the wallet balance
        await update_record(Wallet, user_wallet.model_dump(), Collections.wallets, "uid")

        # update the asset available units
        asset.available_units -= body.units

        if asset.available_units == 0:
            asset.sold_out = True

        # update the asset investors
        if not auth_context.user.uid in asset.investors:
            asset.investors.append(auth_context.user.uid)
            # update the asset investor count
            asset.investor_count += 1

        await update_record(InvestibleAsset, asset.model_dump(), Collections.investible_assets, "uid")

        # update the investment
        investment.is_active = True

        await _db[Collections.investments].insert_one(investment.model_dump())
        await _db[Collections.transactions].insert_one(transaction.model_dump())

    else:

        # initiate the transaction on flutterwave

        result = _initiate_payment(transaction, auth_context, customizations={
            "title": "SafeHome",
            "description": "Investment in SafeHome",
        })

        api_response = {
            "redirect_url": result["link"],
        }

        # save the investment and the tx

        await _db[Collections.investments].insert_one(investment.model_dump())
        await _db[Collections.transactions].insert_one(transaction.model_dump())

        return api_response


@router.get("", status_code=200, response_model=PaginatedResult)
async def get_my_investments(page: int = 1, limit: int = 10, owners_club:  OwnersClubs = Query(default=OwnersClubs.all, alias="ownersClub"), include_asset: bool = Query(alias="includeAsset", default=True), auth_context: AuthenticationContext = Depends(get_auth_context)):

    filters = {
        "investor_uid": auth_context.user.uid,
    }

    paginator = Paginator(
        col_name=Collections.investments,
        filters=filters,
        sort_field="created_at",
        top_down_sort=True,
        include_crumbs=True,
        per_page=limit,
    )

    result = await paginator.get_paginated_result(page, InvestmentWithAsset)

    # get the asset for each investment and set it to the asset info propert of each item in the result

    if include_asset:
        for item in result.items:

            asset = await _db[Collections.investible_assets].find_one({"uid": item['assetUid']})
            item['assetInfo'] = InvestibleAsset(
                **asset).model_dump(by_alias=True)

        # filter out the items that have no matching owner club in the query
        if owners_club != OwnersClubs.all:
            result.items = [
                x for x in result.items if x['assetInfo']['ownerClub'] == owners_club.value]

        result.entries = len(result.items)

    return result
