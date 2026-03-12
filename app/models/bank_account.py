import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base


class BankAccount(Base):

    __tablename__ = "bank_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id"),
        nullable=False
    )

    bank_connection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("bank_connections.id"),
        nullable=False
    )

    account_number = Column(String(30), nullable=False)

    currency = Column(String(10), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    last_synced_at = Column(DateTime, nullable=True)