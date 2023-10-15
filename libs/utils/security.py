from cryptography.hazmat.primitives.twofactor.totp import TOTP
from cryptography.hazmat.primitives.twofactor import InvalidToken
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidKey
from fastapi import HTTPException
from libs.config.settings import get_settings
from cryptography.fernet import MultiFernet, Fernet
from libs.db import Collections, _db
from models.users import TOTPDB, ActionIdentifiers
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from .pure_functions import get_uuid4
from datetime import datetime, timedelta, timezone
from models.users import AuthSession
import jwt
import base64
import pyotp


settings = get_settings()


# Function to encode a string to Base64
def encode_to_base64(input_string):
    encoded_bytes = base64.b64encode(input_string.encode())
    return encoded_bytes.decode()

# Function to decode a Base64 string to the original string


def decode_from_base64(encoded_string):
    decoded_bytes = base64.b64decode(encoded_string.encode())
    return decoded_bytes.decode('utf-8')


def _decode_jwt_token(token: str):

    try:

        decoded = jwt.decode(token, settings.jwt_secret_key, algorithms='HS256',
                             issuer=settings.app_name, options={"require": ["exp", "iss", "sub", "iat"]})

        return decoded

    except jwt.exceptions.ExpiredSignatureError as e:
        raise HTTPException(401, "unauthenticated request : expired token")

    except jwt.exceptions.InvalidAudienceError as e:
        raise HTTPException(401, "unauthenticated request : invalid audience")

    except jwt.exceptions.InvalidIssuerError as e:
        raise HTTPException(401, "unauthenticated request : invalid issuer")

    except jwt.exceptions.DecodeError as e:
        raise HTTPException(401, "unauthenticated request : decode error")

    except Exception as e:
        raise HTTPException(500, f"unauthenticated request : {str(e)}")


async def _create_access_token(user_id: str):

    session_id = get_uuid4()

    payload = {
        "sub": {

            "user_id": user_id,
            "session_id": session_id,
        },
        "exp": datetime.now(tz=timezone.utc) + timedelta(hours=settings.jwt_access_token_expiration_hours),
        "iss":  settings.app_name,
        "iat": datetime.now(tz=timezone.utc)
    }

    _token = jwt.encode(payload, settings.jwt_secret_key, algorithm='HS256')

    authsession = AuthSession(uid=session_id, userId=user_id,
                              duration_in_hours=settings.jwt_access_token_expiration_hours)

    await _db[Collections.authsessions].insert_one(authsession.model_dump())

    return _token


def scrypt_hash(password: str, salt: str, n: int = 2 ** 14, r: int = 8, p: int = 1,):

    try:

        kdf = Scrypt(
            salt=(salt + settings.password_salt).encode(),
            length=32,
            n=n, r=r, p=p
        )

        return None, base64.encodebytes(kdf.derive(password.encode())).decode()

    except Exception as e:
        return str(e), None


def scrypt_verify(guessed_password: str,  expected_hash: str, salt: str, n: int = 2 ** 14, r: int = 8, p: int = 1,):

    try:

        kdf = Scrypt(
            salt=(salt + settings.password_salt).encode(),
            length=32,
            n=n, r=r, p=p
        )

        kdf.verify(guessed_password.encode(),
                   base64.decodebytes(expected_hash.encode()))

        return True

    except InvalidKey:
        return False

    except Exception as e:
        raise HTTPException(500, str(e))


def sha256(message: str) -> str:

    digest = hashes.Hash(hashes.SHA256())
    digest.update(message.encode())
    _bytes = digest.finalize()
    return base64.b64encode(_bytes).decode()


def encrypt(message: bytes) -> bytes:
    keys = [settings.kek1, settings.kek2, settings.kek3]
    f = MultiFernet(Fernet(sha256(x)) for x in keys)
    token = f.encrypt(message)
    return token


def decrypt(token: bytes) -> bytes:
    bytes_token = token
    keys = [settings.kek1, settings.kek2, settings.kek3]
    f = MultiFernet(Fernet(sha256(x)) for x in keys)
    message = f.decrypt(bytes_token)
    return message


async def generate_totp(action:  ActionIdentifiers, foreign_key: str):

    # delete existing matches

    # await _db[Collections.totps].delete_many(
    #     {"action": action, "foreign_key": foreign_key})

    key = pyotp.random_base32()

    totp = pyotp.TOTP(key, interval=settings.otp_interval,
                      digits=settings.otp_length, )

    encrypted_key = base64.encodebytes(encrypt(key.encode())).decode()

    totp_model = TOTPDB(key=encrypted_key, action=action,
                        foreign_key=foreign_key, )

    _data = totp_model.model_dump()

    await _db[Collections.totps].insert_one(_data)

    return totp.now(), totp_model.uid


async def validate_totp(totp_uid:  str):

    totp_dict = await _db[Collections.totps].find_one({"uid": totp_uid})

    if not totp_dict:
        raise HTTPException(400, "totp not found")

    decrypted_key = decrypt(base64.decodebytes(
        totp_dict["key"].encode())).decode()

    totp_obj = pyotp.TOTP(decrypted_key, interval=settings.otp_interval,
                          digits=settings.otp_length)

    return totp_obj, totp_dict
