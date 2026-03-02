import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.database import Base


class OperationBatch(Base):
    __tablename__ = "operation_batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False
    )

    source_type = Column(String, nullable=False)  # пока только "file_upload"

    filename = Column(String, nullable=True)

    status = Column(
        String,
        nullable=False,
        default="pending",
        server_default="pending"
    )  # pending / success / failed

    total_count = Column(Integer, nullable=False, default=0, server_default="0")
    inserted_count = Column(Integer, nullable=False, default=0, server_default="0")
    duplicate_count = Column(Integer, nullable=False, default=0, server_default="0")
    error_count = Column(Integer, nullable=False, default=0, server_default="0")

    error_message = Column(Text, nullable=True)
    error_operation_index = Column(Integer, nullable=True)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # Связь с операциями
    operations = relationship(
        "BankOperation",
        back_populates="batch",
        cascade="all, delete"
    )