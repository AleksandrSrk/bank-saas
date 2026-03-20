from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    DATABASE_URL: str

    TELEGRAM_BOT_TOKEN: str

    # Tochka
    TOCHKA_CLIENT_ID: str | None = None
    TOCHKA_CLIENT_SECRET: str | None = None

    TOCHKA_API_URL: str = "https://enter.tochka.com/uapi/open-banking/v1.0"
    TOCHKA_TOKEN_URL: str = "https://enter.tochka.com/connect/token"

    # DaData
    DADATA_API_KEY: str
    DADATA_SECRET_KEY: str

    SBER_ACCESS_TOKEN: str | None = None
    SBER_BOOTSTRAP_ACCOUNT: str | None = None

    class Config:
        env_file = ".env"


settings = Settings()