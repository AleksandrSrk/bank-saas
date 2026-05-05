import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = "http://backend:8000"
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")

# API_URL = "http://localhost:8000"