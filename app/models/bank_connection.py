import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime

from app.db.database import Base


class BankConnection(Base):
    __tablename__ = "bank_connections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)

    bank_name = Column(String, nullable=False)

    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=True)

    expires_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    consent_id = Column(String)

    last_synced_at = Column(DateTime, nullable=True)