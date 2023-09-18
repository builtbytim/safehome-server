from huey import SqliteHuey
from lib.config.settings import get_settings


settings = get_settings()

huey = SqliteHuey(filename="./huey.db")

# if settings.debug:
#     huey.immediate = True
