import os
from uuid import uuid4
from datetime import datetime, timezone
import time


def get_random_string(length: int = 32):
    return os.urandom(length).hex()


def get_utc_timestamp() -> float:
    return datetime.now(tz=timezone.utc).timestamp()


def get_uuid4():
    return str(uuid4().hex)


def get_complex_id():
    return os.urandom(16).hex()


def get_simple_id():
    return os.urandom(8).hex()


def is_age_in_range(utc_float_time, min_age, max_age):
    # Calculate the current time in seconds since the epoch
    current_time = time.time()

    # Calculate the age in seconds
    age = current_time - utc_float_time

    # Convert age to years (assuming an average year has 365.25 days)
    age_years = age / (365.25 * 24 * 60 * 60)

    # Check if age is within the specified range
    return min_age <= age_years <= max_age
