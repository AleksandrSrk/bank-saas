from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    DATABASE_URL: str

    TELEGRAM_BOT_TOKEN: str

    # Tochka
    TOCHKA_CLIENT_ID: str | None = None
    TOCHKA_CLIENT_SECRET: str | None = None

    TOCHKA_API_URL: str = "https://enter.tochka.com/uapi/open-banking/v1.0"
    TOCHKA_TOKEN_URL: str = "https://enter.tochka.com/connect/token"
    TOCHKA_REDIRECT_URI: str | None = None

    # DaData
    DADATA_API_KEY: str
    DADATA_SECRET_KEY: str

    # Sber: токены живут в bank_connections (авто-refresh), не в .env.
    # SBER_ACCESS_TOKEN / SBER_REFRESH_TOKEN оставлены только чтобы старый .env не ронял strict Settings.
    SBER_ACCESS_TOKEN: str | None = None
    SBER_REFRESH_TOKEN: str | None = None
    SBER_CLIENT_ID: str | None = None
    SBER_CLIENT_SECRET: str | None = None
    SBER_BOOTSTRAP_ACCOUNT: str | None = None
    SBER_API_URL: str = "https://fintech.sberbank.ru:9443"
    SBER_TOKEN_URL: str = "https://fintech.sberbank.ru:9443/ic/sso/api/v2/oauth/token"
    SBER_CERT_FILE: str = "certs/cert.pem"
    SBER_KEY_FILE: str = "certs/key.pem"
    SBER_CA_BUNDLE: str = "certs/sber_ca_bundle.pem"

    # Куда слать алерты (личка директора в bank_bot)
    ALERT_TELEGRAM_CHAT_ID: int | None = None
    DEBUG: bool = False
    INTERNAL_API_KEY: str | None = None

    # Google Drive — бэкап БД
    GOOGLE_SERVICE_ACCOUNT_FILE: str | None = None
    BACKUP_FILE_ID: str | None = None

    class Config:
        env_file = ".env"


settings = Settings()