import uuid
from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base
from app.models.legal_entity import LegalEntity

class UserCompany(Base):
    __tablename__ = "user_companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE")
    )

    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE")
    )

    legal_entity_id = Column(
        UUID(as_uuid=True),
        ForeignKey("legal_entities.id", ondelete="CASCADE"),
        nullable=True
    )