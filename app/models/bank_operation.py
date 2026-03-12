import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Date,
    Numeric,
    ForeignKey,
    Text,
    UniqueConstraint,
    Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.database import Base


class BankOperation(Base):
    __tablename__ = "bank_operations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False
    )

    # import_batch_id = Column(
    #     UUID(as_uuid=True),
    #     ForeignKey("operation_batches.id", ondelete="CASCADE"),
    #     nullable=True
    # )

    company = relationship(
        "Company",
        back_populates="bank_operations"
    )

    # batch = relationship(
    #     "OperationBatch",
    #     back_populates="operations"
    # )

    # Документ
    document_number = Column(String, nullable=False)
    document_type = Column(String, nullable=False)

    # Деньги
    amount = Column(Numeric(15, 2), nullable=False)
    direction = Column(String, nullable=False)  # incoming / outgoing

    # Даты
    operation_date = Column(DateTime, nullable=False)
    document_date = Column(Date, nullable=True)

    # Счета
    account_number = Column(String, nullable=False)
    counterparty_account = Column(String, nullable=True)

    # Контрагент
    counterparty_inn = Column(String, nullable=True)
    counterparty_name = Column(String, nullable=True)

    # Текст
    description = Column(Text, nullable=True)

    # Категория
    operation_category = Column(
        String,
        nullable=False,
        default="other",
        server_default="other"
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "document_number",
            "document_type",
            "operation_date",
            "amount",
            "direction",
            name="uq_operation_identity"
        ),
        Index("idx_operation_company_date", "company_id", "operation_date"),
        Index("idx_operation_company_inn", "company_id", "counterparty_inn"),
    )