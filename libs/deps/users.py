from typing import Union
from fastapi import HTTPException,  BackgroundTasks, Depends
from pydantic import EmailStr
from libs.db import _db, Collections
from libs.utils.api_helpers import update_record
from libs.config.settings import get_settings
from models.users import AuthenticationContext,  RequestAccountConfirmationInput, UserDBModel, AuthSession
from libs.utils.security import _decode_jwt_token
from datetime import datetime, timezone, timedelta
from libs.utils.pure_functions import get_utc_timestamp
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/v1/users/oauth2-password-request-form", auto_error=False)

settings = get_settings()


async def __get_auth_context(bg_tasks, token):
    if not token:
        raise HTTPException(
            401, "unauthenticated request : no authorization header present")

    payload = _decode_jwt_token(token)

    user_id = payload["sub"]["user_id"]

    user = await _db[Collections.users].find_one({"uid": user_id})

    if not user:
        raise HTTPException(401, f"unauthenticated request : user not found ")

    session_id = payload["sub"]["session_id"]

    auth_session = await _db[Collections.authsessions].find_one({"uid": session_id})

    if not auth_session:
        raise HTTPException(
            401, f"unauthenticated request : session not found ")

    session = AuthSession(**auth_session)

    if user_id != session.user_id:
        raise HTTPException(
            401, f"unauthenticated request :  user id mismatch ")

    if not session.is_valid:
        raise HTTPException(
            401, f"unauthenticated request :  session invalidated ")

    session_created = datetime.fromtimestamp(session.created, timezone.utc)
    utc_now = datetime.now(tz=timezone.utc)

    if utc_now >= session_created + timedelta(hours=session.duration_in_hours):
        raise HTTPException(
            401, f"unauthenticated request :  session expired ")

    session.last_used = get_utc_timestamp()
    session.usage_count += 1

    bg_tasks.add_task(update_record, AuthSession,
                      session.model_dump(), Collections.authsessions, "uid")

    return AuthenticationContext(
        session=session, user=UserDBModel(**user)
    )


async def get_auth_context(bg_tasks: BackgroundTasks, token: str = Depends(oauth2_scheme)) -> AuthenticationContext:
    return await __get_auth_context(bg_tasks, token)


async def get_auth_context_optionally(bg_tasks: BackgroundTasks, token: str = Depends(oauth2_scheme)) -> Union[AuthenticationContext, None]:

    if not token:
        return None

    return await __get_auth_context(bg_tasks, token)


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
