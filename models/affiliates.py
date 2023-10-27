from pydantic import BaseModel, Field, EmailStr
from libs.utils.pure_functions import *
from libs.config.settings import get_settings
from pydantic_settings import SettingsConfigDict
import random
import string


settings = get_settings()
