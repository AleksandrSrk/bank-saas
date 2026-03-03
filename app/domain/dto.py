from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from uuid import UUID
from datetime import datetime
from typing import Optional
from .enums import ImportStatus


@dataclass
class OperationImportDTO:
    document_number: str
    document_type: str

    operation_date: datetime
    document_date: Optional[date]

    debit_amount: Optional[Decimal]
    credit_amount: Optional[Decimal]

    account_number: str
    counterparty_account: Optional[str]
    counterparty_inn: Optional[str]
    counterparty_name: Optional[str]

    description: Optional[str]

    

@dataclass
class ImportResult:
    batch_id: UUID
    status: ImportStatus

    total_count: int
    inserted_count: int
    duplicate_count: int
    error_count: int

    error_message: Optional[str]
    created_at: datetime