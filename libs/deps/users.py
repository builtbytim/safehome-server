from typing import Union
from fastapi import HTTPException,  BackgroundTasks, Depends, Header
from pydantic import EmailStr
from libs.db import _db, Collections
from libs.utils.api_helpers import update_record
from libs.config.settings import get_settings
from models.users import AuthenticationContext,  RequestAccountConfirmationInput, UserDBModel, AuthSession, AuthCode, USER_EXLUCUDE_FIELDS, UserOutputModel
from models.wallets import Wallet
from libs.utils.security import _decode_jwt_token
from datetime import datetime, timezone, timedelta
from libs.utils.pure_functions import get_utc_timestamp
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/users/sign-in")

settings = get_settings()


async def __get_auth_context(bg_tasks, token):
    if not token:
        raise HTTPException(
            401, "unauthenticated request : no authorization header present", headers={"WWW-Authenticate": "Bearer", "X-ACTION": "SIGN_IN"})

    payload = _decode_jwt_token(token)

    user_id = payload["sub"]["user_id"]

    user = await _db[Collections.users].find_one({"uid": user_id})

    if not user:
        raise HTTPException(401, f"unauthenticated request : user not found ", headers={
                            "WWW-Authenticate": "Bearer", "X-ACTION": "SIGN_IN"})

    session_id = payload["sub"]["session_id"]

    auth_session = await _db[Collections.authsessions].find_one({"uid": session_id})

    if not auth_session:
        raise HTTPException(
            401, f"unauthenticated request : session not found ", headers={"WWW-Authenticate": "Bearer", "X-ACTION": "SIGN_IN"})

    session = AuthSession(**auth_session)

    if user.get("is_active", False) is False:
        raise HTTPException(
            401, f"unauthenticated request :  user is inactive ", headers={"WWW-Authenticate": "Bearer", "X-ACTION": "SIGN_IN"})

    if user_id != session.user_id:
        raise HTTPException(
            401, f"unauthenticated request :  user id mismatch ", headers={"WWW-Authenticate": "Bearer", "X-ACTION": "SIGN_IN"})

    if not session.is_valid:
        raise HTTPException(
            401, f"unauthenticated request :  session invalidated ", headers={"WWW-Authenticate": "Bearer", "X-ACTION": "SIGN_IN"})

    session_created = datetime.fromtimestamp(session.created, timezone.utc)
    utc_now = datetime.now(tz=timezone.utc)

    if utc_now >= session_created + timedelta(hours=session.duration_in_hours):
        raise HTTPException(
            401, f"unauthenticated request :  session expired ", headers={"WWW-Authenticate": "Bearer", "X-ACTION": "SIGN_IN"})

    session.last_used = get_utc_timestamp()
    session.usage_count += 1

    async def make_update(uid, last_used, usage_count):

        await _db[Collections.authsessions].update_one(
            {"uid": uid}, {"$set": {"last_used": last_used, "usage_count": usage_count}})

    bg_tasks.add_task(make_update, session.uid,
                      session.last_used, session.usage_count)

    _user_model = UserDBModel(**user)

    return AuthenticationContext(
        session=session,
        user=_user_model
    )


async def get_auth_context(bg_tasks: BackgroundTasks, token: str = Depends(oauth2_scheme)) -> AuthenticationContext:
    return await __get_auth_context(bg_tasks, token)


async def get_auth_context_optionally(bg_tasks: BackgroundTasks, token: str = Depends(oauth2_scheme)) -> Union[AuthenticationContext, None]:

    if not token:
        return None

    return await __get_auth_context(bg_tasks, token)


async def get_user_wallet(context: AuthenticationContext = Depends(get_auth_context)) -> UserDBModel:

    wallet = await _db[Collections.wallets].find_one({"user_id": context.user.uid})

    if wallet:
        return Wallet(**wallet)

    return None


async def _get_user_by_uid(uid: str) -> UserDBModel:

    if not uid:
        raise HTTPException(status_code=400, detail="invalid user uid")

    user = await _db[Collections.users].find_one({"uid": uid})

    if not user:
        raise HTTPException(
            status_code=404, detail=f" user with uid {uid} does not exist")

    return UserDBModel(**user)


async def get_user_by_uid(body: RequestAccountConfirmationInput) -> UserDBModel:

    return await _get_user_by_uid(body.uid)


async def _get_user_by_email(email: EmailStr) -> UserDBModel:

    if not email:
        raise HTTPException(status_code=400, detail="invalid user email")

    user = await _db[Collections.users].find_one({"email": email})

    if not user:
        raise HTTPException(
            status_code=404, detail=f" user with email {email} does not exist")

    return UserDBModel(**user)


async def get_user_by_email(body: OAuth2PasswordRequestForm = Depends()) -> UserDBModel:
    return await _get_user_by_email(body.username)


async def get_auth_code(auth_code:  str | None = Header(default=None, alias="X-AUTH-CODE")):

    if auth_code is None:
        raise HTTPException(status_code=400, detail="Missing auth code")

    auth_code_from_db = await _db[Collections.authcodes].find_one({"code": auth_code})

    if auth_code_from_db is None:
        raise HTTPException(
            status_code=404, detail=f"invalid auth code")

    r = AuthCode(**auth_code_from_db)

    future_ts = r.created_at + (settings.auth_code_validity_mins * 60)

    if get_utc_timestamp() > future_ts:
        raise HTTPException(status_code=400, detail="Expired auth code")

    if not r.valid:
        raise HTTPException(
            status_code=404, detail=f"invalid auth code")

    return r
