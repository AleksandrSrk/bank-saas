from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase


DATABASE_URL = "postgresql://bank_user:bank_pass@postgres:5432/bank_saas"


class Base(DeclarativeBase):
    pass


engine = create_engine(DATABASE_URL, echo=True)

SessionLocal = sessionmaker(bind=engine)

import app.models.company
import app.models.bank_operation

import app.models.user
import app.models.role
import app.models.user_role
import app.models.telegram_account
import app.models.operation_batch
import app.models.manager_request