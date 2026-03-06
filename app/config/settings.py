from dotenv import load_dotenv
import os

load_dotenv()


class Settings:

    TOCHKA_ACCESS_TOKEN = os.getenv("TOCHKA_ACCESS_TOKEN")


settings = Settings()