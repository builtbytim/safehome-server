from fastapi import APIRouter, Depends, HTTPException, Query
from libs.config.settings import get_settings
from models.notifications import *
from libs.db import _db, Collections
from libs.utils.pure_functions import *
from libs.deps.users import AuthenticationContext, get_auth_context, only_paid_users
from libs.utils.api_helpers import update_record, find_record
from libs.utils.pagination import Paginator, PaginatedResult


settings = get_settings()


router = APIRouter(responses={
    404: {"description": "The resource you requested does not exist!"}
}, tags=["Notfications"], dependencies=[Depends(only_paid_users)])


@router.post("", status_code=200, response_model=Notification)
async def create_user_notification(body: NotificationInput, auth_context: AuthenticationContext = Depends(get_auth_context)):
    notification = Notification(
        **body.model_dump(), user_id=auth_context.user.uid)

    await _db[Collections.notifications].insert_one(notification.model_dump())

    return notification


@router.get("/stats", status_code=200, response_model=UserNotificationStats)
async def get_user_notifications_stats(auth_context: AuthenticationContext = Depends(get_auth_context)):

    unread_count = await _db[Collections.notifications].count_documents({"user_id": auth_context.user.uid, "read": False})

    read_count = await _db[Collections.notifications].count_documents({"user_id": auth_context.user.uid, "read": True})

    total_count = unread_count + read_count

    return UserNotificationStats(unread_count=unread_count, read_count=read_count, total_count=total_count)


@router.get("", status_code=200, response_model=PaginatedResult)
async def get_user_notifications(page: int = 1, limit: int = 10, read: bool = Query(default=False), auth_context: AuthenticationContext = Depends(get_auth_context)):

    root_filter = {
        "user_id": auth_context.user.uid,
    }

    filters = {

    }

    if read:
        filters["read"] = read

    paginator = Paginator(Collections.notifications,
                          "created_at", top_down_sort=True,  root_filter=root_filter, filters=filters, per_page=limit)

    res = await paginator.get_paginated_result(page, Notification)
    return res


@router.get("/mark-all-as-read", status_code=200)
async def mark_all_user_notifications_as_read(auth_context: AuthenticationContext = Depends(get_auth_context)):
    await _db[Collections.notifications].update_many({"user_id": auth_context.user.uid, "read": False}, {"$set": {"read": True, "read_at": get_utc_timestamp()}})


@router.get("/clear-all", status_code=200)
async def clear_all_user_notifications(auth_context: AuthenticationContext = Depends(get_auth_context)):
    await _db[Collections.notifications].delete_many({"user_id": auth_context.user.uid})


@router.get("/{uid}/mark-as-read", status_code=200)
async def mark_user_notification_as_read(uid: str, auth_context: AuthenticationContext = Depends(get_auth_context)):
    notification = await find_record(Notification, uid, Collections.notifications)

    if notification.read:
        return

    if notification.user_id != auth_context.user.uid:
        raise HTTPException(
            status_code=403, detail="You are not authorized to perform this action")

    notification.read = True

    notification.read_at = get_utc_timestamp()

    notification.read_by = auth_context.user.uid

    notification.read_by_name = auth_context.get_full_name()

    notification.read_by_avatar_url = auth_context.user.avatar_url

    return await update_record(Notification, notification.model_dump(), Collections.notifications, "uid")


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


@router.get("/{uid}", status_code=200, response_model=Notification)
async def get_user_notification(uid: str, auth_context: AuthenticationContext = Depends(get_auth_context)):
    n = await find_record(Notification,  Collections.notifications, "uid", uid, raise_404=True)

    if n.user_id != auth_context.user.uid:
        raise HTTPException(
            status_code=403, detail="You are not authorized to perform this action")

    return n
