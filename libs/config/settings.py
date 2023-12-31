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
    landing_page_url: str = "http://localhost:3000"
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
    quore_id_client_id: str = "IS1MQVHBUNFU10MSM6SK"
    quore_id_secret_key: str = "a869f4d5b707440184b44c58ee4c85ae"
    quore_id_api_token: str = "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICIzaVgtaEFrS3RmNUlsYWhRcElrNWwwbFBRVlNmVnpBdG9WVWQ4UXZ1OHJFIn0.eyJleHAiOjE3MDQwMzA4MDQsImlhdCI6MTcwNDAyMzYwNCwianRpIjoiOWEyOTk4ZWItNWJjMS00Yjk5LWJkZmItYjBhMzE5MGJkZjM0IiwiaXNzIjoiaHR0cHM6Ly9hdXRoLnFvcmVpZC5jb20vYXV0aC9yZWFsbXMvcW9yZWlkIiwiYXVkIjoiYWNjb3VudCIsInN1YiI6IjE4Y2Y1NTNlLTBiYzgtNGEyMS1hMjQ4LTUxNzg1MzQzNzUzOSIsInR5cCI6IkJlYXJlciIsImF6cCI6IklTMU1RVkhCVU5GVTEwTVNNNlNLIiwiYWNyIjoiMSIsInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJvZmZsaW5lX2FjY2VzcyIsInVtYV9hdXRob3JpemF0aW9uIiwiZGVmYXVsdC1yb2xlcy1xb3JlaWQiXX0sInJlc291cmNlX2FjY2VzcyI6eyJhY2NvdW50Ijp7InJvbGVzIjpbIm1hbmFnZS1hY2NvdW50IiwibWFuYWdlLWFjY291bnQtbGlua3MiLCJ2aWV3LXByb2ZpbGUiXX19LCJzY29wZSI6InByb2ZpbGUgZW1haWwiLCJlbnZpcm9ubWVudCI6InNhbmRib3giLCJvcmdhbmlzYXRpb25JZCI6MjE5MTk5LCJjbGllbnRJZCI6IklTMU1RVkhCVU5GVTEwTVNNNlNLIiwiY2xpZW50SG9zdCI6IjE5Mi4xNjguMTY3LjE5MyIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwicHJlZmVycmVkX3VzZXJuYW1lIjoic2VydmljZS1hY2NvdW50LWlzMW1xdmhidW5mdTEwbXNtNnNrIiwiYXBwbGljYXRpb25JZCI6MTg1ODcsImNsaWVudEFkZHJlc3MiOiIxOTIuMTY4LjE2Ny4xOTMifQ.q7pjGZCXyZ6ZOVx1EeMMvGFQTJO_nLfa7nwRtIl8_PLsorbWpC9Y_9NeH7imIwfhIxgr9M-CZs--pW6sB60DyY1-tUjDQTSRo_iQYZtGpe5xL__EgXwSNzGYyzm-TQUBOprg2lqed7kAjc14mq4PXepw0t31mpu_BUL9JtGexrHy7xzAbOtcmS9JNm_KV8aEen0eyb84nCvLuF75A6PmVrHjPLDBRhdoXkIJxpFckDRrU7QOaQIh_J_IcWmrWOm26iRvNA0nn52qiyKjGptafTdPNfz74ODgHVRuKnuKr6TVKh0n1wZy9pV6cbN3q9C0ZlbkZP3Baa_ZZs0a5OIywA"
    quore_id_api_url: str = "https://api.qoreid.com"
    referral_withdrawal_threshold: float = 5000
    referral_bonus: float = 2000
    affiliate_bonus: float = 2000
    affiliate_withdrawal_threshold: float = 5000
    kek: str = "kek"
    kek1: str = "kek1"
    kek2: str = "kek2"
    kek3: str = "kek3"

    allowed_origins: list[str] = [
        "https://safehomecoop.com", "https://www.safehomecoop.com", "https://app.safehomecoop.com", "https://safehomecoop-affiliates.vercel.app",
        "https://main.d259adcvsfh045.amplifyapp.com",
        "https://affiliates.safehomecoop.com",
        "http://localhost:3000", "http://0.0.0.0:3000", "http://localhost:3001", "https://safehome-gg.vercel.app", "https://app.safehome.timmypelumy.dev", "https://safehome.timmypelumy.dev"]


@lru_cache()
def get_settings():
    return Settings()
