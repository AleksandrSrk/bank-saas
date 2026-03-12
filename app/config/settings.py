from dotenv import load_dotenv
import os

load_dotenv()


class Settings:

    DATABASE_URL = os.getenv("DATABASE_URL")

    # OAuth приложения
    TOCHKA_CLIENT_ID = os.getenv("TOCHKA_CLIENT_ID")
    TOCHKA_CLIENT_SECRET = os.getenv("TOCHKA_CLIENT_SECRET")

    # API endpoints
    TOCHKA_API_URL = os.getenv(
        "TOCHKA_API_URL",
        "https://enter.tochka.com/upapi/open-banking/v1.0"
    )

    TOCHKA_TOKEN_URL = os.getenv(
        "TOCHKA_TOKEN_URL",
        "https://enter.tochka.com/connect/token"
    )


settings = Settings()