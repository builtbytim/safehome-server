from pydantic import HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):

    """ Application Settings """

    model_config = SettingsConfigDict(env_file=".env")

    maintenance_mode: bool = False
    debug: bool = True
    log_level: str = "DEBUG"
    app_name: str = "safehome"
    db_name: str = "safehome"
    dump_mail: str = "dump@safehome.xyz"
    fee_percent: float = 0.1
    fee_percent_cap: float = 1000
    base_fee: float = 100
    api_key_lifetime: int = 24
    coinprofile_api_key: str = "key"
    coinprofile_username: str = "testuser"
    webhook_url: str = "https://skilled-severely-platypus.ngrok-free.app/api/v1/payment/webhook"
    coinprofile_test_api_url: HttpUrl = "https://staging-biz.coinprofile.co/v2"
    coinprofile_api_production_url: HttpUrl = "https://staging-biz.coinprofile.co/v2"
    api_key_header_name: str = "x-safehome-api"
    tx_reference_prefix: str = "xpnd"
    tx_reference_length: int = 24
    tx_validity_lax_mins: int = 5
    db_url: str = "mongodb://localhost:4000"
    mail_username: str = "safehome"
    mail_password: str = "mail_pass"
    mail_from: str = "safehometeam@safehome.xyz"
    mail_port: int = 587
    mail_server:  str = "https://mail.com"
    mail_starttls: bool = False
    mail_ssl_tls:  bool = True
    mail_display_name: str = "safehome Team"
    mail_domain:  str = "https://mail.com"
    mail_domain_username:  str = "admin"

    allowed_origins: list[str] = ["http://localhost:5173", "https://esafehome.onrender.com", "https://safehome.xyz", "https://www.safehome.xyz",
                                  "http://localhost:7000", "https://esafehome-tau.vercel.app"]


@lru_cache()
def get_settings():
    return Settings()
