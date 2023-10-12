from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File, Response
from libs.config.settings import get_settings
from models.notifications import *
from libs.db import _db, Collections
from libs.utils.pure_functions import *
from libs.deps.users import AuthenticationContext, get_auth_context
from libs.utils.api_helpers import update_record, find_record


settings = get_settings()


router = APIRouter(responses={
    404: {"description": "The resource you requested does not exist!"}
}, tags=["Notfications"])


@router.get("/preferences", status_code=200, response_model=NotificationPreferences)
async def get_user_notifications_preferences(auth_context: AuthenticationContext = Depends(get_auth_context)):
    notification_preferences = await _db[Collections.notification_preferences].find_one({"user_id": auth_context.user.uid})

    if not notification_preferences:
        # create one and return it

        notification_preferences = NotificationPreferences(
            user_id=auth_context.user.uid)

        await _db[Collections.notification_preferences].insert_one(notification_preferences.model_dump())

        return notification_preferences

    return NotificationPreferences(**notification_preferences)


@router.post("/preferences", status_code=200, response_model=NotificationPreferences)
async def set_user_notifications_preferences(body:  NotificationPreferencesInput, auth_context: AuthenticationContext = Depends(get_auth_context)):

    # first try to locate if a notification preferences document exists for the user

    notification_preferences = await _db[Collections.notification_preferences].find_one({"user_id": auth_context.user.uid})

    if notification_preferences:
        # update the existing document

        notification_preferences = NotificationPreferences(
            **notification_preferences)

        notification_preferences.email = body.email

        notification_preferences.push = body.push

        notification_preferences.sms = body.sms

        notification_preferences.updated_at = get_utc_timestamp()

        updated_prefs = await update_record(NotificationPreferences, notification_preferences.model_dump(), Collections.notification_preferences, "uid", refresh_from_db=True)

        return updated_prefs

    # create a new document

    notification_preferences = NotificationPreferences(
        user_id=auth_context.user.uid, email=body.email, push=body.push, sms=body.sms)

    # save to db

    await _db[Collections.notification_preferences].insert_one(notification_preferences.model_dump())

    return notification_preferences
