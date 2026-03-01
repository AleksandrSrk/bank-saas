from uuid import UUID
from datetime import datetime
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