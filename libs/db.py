from motor import motor_asyncio
from libs.config.settings import get_settings
from enum import Enum


settings = get_settings()


class Collections(str, Enum):
    users = "users"
    totps = "totps"
    authsessions = "auth_sessions"
    id_documents = "identity_documents"
    throttles = "throttles"
    authcodes = "auth_codes"
    passwordresetstores = "password_reset_stores"
    waitlist_applications = "waitlist_applications"
    notification_preferences = "notification_preferences"
    next_of_kins = "next_of_kins"
    wallets = "wallets"
    transactions = "transactions"
    bank_accounts = "bank_accounts"
    investible_assets = "investible_assets"
    investments = "investments"
    notifications = "notifications"
    goal_savings_plans = "goal_savings_plans"
    locked_savings_plans = "locked_savings_plans"
    cards = "cards"


client = motor_asyncio.AsyncIOMotorClient(settings.db_url)


_db = client[settings.db_name]
