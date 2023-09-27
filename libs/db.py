from motor import motor_asyncio
from libs.config.settings import get_settings
from enum import Enum


settings = get_settings()


class Collections(str, Enum):
    users = "users"
    totps = "totps"
    authsessions = "authsessions"
    id_documents = "identity_documents"
    throttles = "throttles"
    authcodes = "authcodes"
    passwordresetstores = "passwordresetstores"


client = motor_asyncio.AsyncIOMotorClient(settings.db_url)


_db = client[settings.db_name]
