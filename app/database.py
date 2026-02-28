from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = "postgresql://bank_user:bank_pass@localhost:5432/bank_saas"


class Base(DeclarativeBase):
    pass


engine = create_engine(DATABASE_URL, echo=True)

SessionLocal = sessionmaker(bind=engine)

import app.models.company