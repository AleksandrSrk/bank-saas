from uuid import UUID
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class BankOperationCreate(BaseModel):
    bank_operation_id: str
    inn: str
    amount: Decimal
    operation_date: datetime


class BankOperationRead(BankOperationCreate):
    id: UUID
    company_id: UUID

    model_config = ConfigDict(from_attributes=True)


class BankOperationListItem(BaseModel):
    id: UUID
    company_id: UUID

    document_number: str
    document_type: str

    amount: Decimal
    direction: str

    operation_date: datetime
    document_date: date | None = None

    account_number: str
    counterparty_account: str | None = None

    counterparty_inn: str | None = None
    counterparty_name: str | None = None

    description: str | None = None
    operation_category: str

    is_internal: bool | None = None
    created_at: datetime

    counterparty_legal_entity_id: UUID | None = None
    legal_entity_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)