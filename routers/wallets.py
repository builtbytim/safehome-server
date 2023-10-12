from fastapi import APIRouter, HTTPException, Depends
from libs.config.settings import get_settings
from models.users import AuthenticationContext
from libs.db import _db, Collections
from libs.utils.api_helpers import find_record, update_record
from models.payments import *
from models.wallets import Wallet
from libs.utils.pure_functions import *
from libs.huey_tasks.tasks import task_send_mail
from libs.deps.users import get_auth_context, get_user_wallet
from libs.logging import Logger
from libs.utils.req_helpers import make_req, make_url, Endpoints, handle_response


logger = Logger(f"{__package__}.{__name__}")

settings = get_settings()


router = APIRouter(responses={
    404: {"description": "The resource you requested does not exist!"}
}, tags=["Wallets"])


@router.get("", status_code=200, response_model=Wallet)
async def get_wallet(auth_context: AuthenticationContext = Depends(get_auth_context), wallet:  Wallet = Depends(get_user_wallet)):

    if not wallet:
        logger.error(f"User {auth_context.user.uid} does not have a wallet")

        raise HTTPException(
            status_code=400, detail="You do not have a wallet yet! Please contact support.")

    return wallet
