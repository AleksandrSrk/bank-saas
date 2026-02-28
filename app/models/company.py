from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from uuid import uuid4
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    inn: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)