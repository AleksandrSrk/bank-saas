from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from uuid import uuid4
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base
from sqlalchemy.orm import relationship


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )

    bank_operations = relationship(
        "BankOperation",
        back_populates="company",
        cascade="all, delete-orphan",
        foreign_keys="BankOperation.company_id"
    )

    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    inn: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)

    status: Mapped[str] = mapped_column(String(50), default="reserved")