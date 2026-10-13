import os
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase


DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set")


class Base(DeclarativeBase):
    pass


# echo=True писал в docker logs все параметры запросов, включая банковские токены.
# hide_parameters=True — параметры не попадают и в тексты исключений SQLAlchemy.
# Для отладки SQL: SQL_ECHO=1 в окружении (параметры всё равно скрыты).
engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("SQL_ECHO") == "1",
    hide_parameters=True,
)

SessionLocal = sessionmaker(bind=engine)


# --- IMPORT ALL MODELS (обязательно) ---
import app.models.company
import app.models.bank_operation

import app.models.user
import app.models.role
import app.models.user_role
import app.models.telegram_account
import app.models.operation_batch
import app.models.manager_request

import app.models.bank_connection
import app.models.bank_account
import app.models.tracked_company
import app.models.user_company
import app.models.legal_entity