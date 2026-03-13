import uuid
from datetime import datetime

from sqlalchemy import Column, ForeignKey, DateTime, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.database import Base


class TrackedCompany(Base):
    __tablename__ = "tracked_companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    manager_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False
    )

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    active = Column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("manager_id", "company_id", name="uq_manager_company_tracking"),
    )