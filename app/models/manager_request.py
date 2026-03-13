import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.database import Base


class ManagerRequest(Base):
    __tablename__ = "manager_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    manager_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    inn = Column(String(12), nullable=False)

    status = Column(
        String,
        nullable=False,
        default="pending"
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    approved_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True
    )

    approved_at = Column(DateTime, nullable=True)

    manager = relationship("User", foreign_keys=[manager_id])