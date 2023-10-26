from pydantic import EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):

    """ Application Settings """

    model_config = SettingsConfigDict(env_file=".env")

    maintenance_mode: bool = False
    default_currency: str = "NGN"
    debug: bool = True
    app_url: str = "http://localhost:3000"
    server_url: str = "http://localhost:7000/api/v1"
    log_level: str = "DEBUG"
    app_name: str = "Safehome"
    membership_fee: float = 5000
    db_name: str = "Safehome"
    cloudinary_cloud_name: str = "cloud_name"
    cloudinary_api_key: str = "api_key"
    cloudinary_api_secret: str = "api_secret"
    images_dir: str = "safehome_images"
    allowed_image_content_types: list[str] = [
        "image/png", "image/jpeg", "image/gif"]
    dump_mail: str = "dump@Safehome.xyz"
    api_key_header_name: str = "x-Safehome-api"
    tx_reference_prefix: str = "SFH"
    tx_reference_length: int = 24
    tx_validity_lax_mins: int = 5
    db_url: str = "mongodb://localhost:4000"
    mail_username: str = "Safehome"
    mail_password: str = "mail_pass"
    mail_from: str = "Safehometeam@Safehome.xyz"
    mail_port: int = 587
    mail_server:  str = "https://mail.com"
    mail_starttls: bool = False
    mail_ssl_tls:  bool = True
    mail_display_name: str = "Safehome Cooperative"
    mail_domain:  str = "https://mail.com"
    mail_domain_username:  str = "admin"
    otp_interval: int = 300  # seconds
    otp_length: int = 6
    support_email:  EmailStr = "support@safehome.com"
    bearer_header_name:  str = "Bearer"
    password_salt: str = "passwordsalt"
    jwt_access_token_expiration_hours: int = 24
    auth_code_validity_mins: int = 10
    jwt_secret_key: str = "jwtsecretkey"
    flutterwave_public_key: str = "flutterwavepublickey"
    flutterwave_secret_key: str = "flutterwavesecretkey"
    flutterwave_encryption_key: str = "flutterwaveencryptionkey"
    verifyme_secret_key: str = "verifymesecretkey"
    referral_withdrawal_threshold: float = 5000
    kek: str = "kek"
    kek1: str = "kek1"
    kek2: str = "kek2"
    kek3: str = "kek3"

    allowed_origins: list[str] = [
        "https://safehomecoop.com", "https://www.safehomecoop.com", "https://app.safehomecoop.com",
        "http://localhost:3000", "http://localhost:3001", "https://safehome-gg.vercel.app", "https://app.safehome.timmypelumy.dev", "https://safehome.timmypelumy.dev"]


@lru_cache()
def get_settings():
    return Settings()
