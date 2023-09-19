import os
from uuid import uuid4
from datetime import datetime, timezone


def get_utc_timestamp() -> float:
    return datetime.now(tz=timezone.utc).timestamp()


def get_uuid4():
    return str(uuid4().hex)


def get_complex_id():
    return os.urandom(16).hex()


def get_simple_id():
    return os.urandom(8).hex()
