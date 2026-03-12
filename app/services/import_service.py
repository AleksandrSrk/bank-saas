from typing import Iterable
from uuid import UUID, uuid4
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from app.domain.dto import OperationImportDTO, ImportResult
from app.domain.enums import ImportStatus

from app.models.operation_batch import OperationBatch
from app.models.bank_operation import BankOperation
from app.domain.enums import OperationDirection


class ImportService:

    BATCH_SIZE = 1000

    def __init__(self, db: Session):
        self.db = db

    def import_operations(
        self,
        dtos: Iterable[OperationImportDTO],
        company_id: UUID,
        filename: str,
    ) -> ImportResult:

        batch = self._create_batch(company_id, filename)

        total_count = 0
        inserted_count = 0

        try:

            values = []

            for index, dto in enumerate(dtos):

                self._validate_dto(dto, index)

                operation_dict = self._build_operation_dict(
                    dto,
                    company_id,
                    batch.id
                )

                values.append(operation_dict)
                total_count += 1

                if len(values) >= self.BATCH_SIZE:
                    inserted_count += self._insert_batch(values)
                    values.clear()

            # вставляем остаток
            if values:
                inserted_count += self._insert_batch(values)

            duplicate_count = total_count - inserted_count

            batch.status = ImportStatus.SUCCESS.value
            batch.total_count = total_count
            batch.inserted_count = inserted_count
            batch.duplicate_count = duplicate_count

            self.db.commit()

            return ImportResult(
                batch_id=batch.id,
                status=ImportStatus.SUCCESS,
                total_count=total_count,
                inserted_count=inserted_count,
                duplicate_count=duplicate_count,
                error_count=0,
                error_message=None,
                created_at=batch.created_at,
            )

        except Exception as e:

            self.db.rollback()

            batch.status = ImportStatus.FAILED.value
            batch.error_message = str(e)

            self.db.commit()

            return ImportResult(
                batch_id=batch.id,
                status=ImportStatus.FAILED,
                total_count=0,
                inserted_count=0,
                duplicate_count=0,
                error_count=1,
                error_message=str(e),
                created_at=batch.created_at,
            )

    def _insert_batch(self, values):

        stmt = insert(BankOperation).values(values)

        stmt = stmt.on_conflict_do_nothing(
            index_elements=[
                "company_id",
                "document_number",
                "document_type",
                "operation_date",
                "amount",
                "direction",
            ]
        )

        result = self.db.execute(stmt)

        return result.rowcount or 0

    def _create_batch(self, company_id: UUID, filename: str) -> OperationBatch:

        batch = OperationBatch(
            company_id=company_id,
            source_type="file_upload",
            filename=filename,
            status=ImportStatus.PENDING.value,
        )

        self.db.add(batch)
        self.db.commit()
        self.db.refresh(batch)

        return batch

    def _validate_dto(self, dto: OperationImportDTO, index: int) -> None:

        if not dto.document_number:
            raise ImportValidationError(
                "Document number is required",
                index
            )

        if not dto.operation_date:
            raise ImportValidationError(
                "Operation date is required",
                index
            )

        if not dto.account_number:
            raise ImportValidationError(
                "Account number is required",
                index
            )

        debit = dto.debit_amount
        credit = dto.credit_amount

        if debit is None and credit is None:
            raise ImportValidationError(
                "Operation must contain either debit or credit amount",
                index
            )

        if debit is not None and credit is not None:
            raise ImportValidationError(
                "Operation cannot contain both debit and credit amounts",
                index
            )

        if debit is not None and debit <= Decimal("0"):
            raise ImportValidationError(
                "Debit amount must be greater than 0",
                index
            )

        if credit is not None and credit <= Decimal("0"):
            raise ImportValidationError(
                "Credit amount must be greater than 0",
                index
            )

    def _build_operation_dict(
        self,
        dto: OperationImportDTO,
        company_id: UUID,
        batch_id: UUID,
    ):

        debit = dto.debit_amount
        credit = dto.credit_amount

        if debit is not None:
            amount = debit
            direction = OperationDirection.OUTGOING
        else:
            amount = credit
            direction = OperationDirection.INCOMING

        return {
            "id": uuid4(),
            "company_id": company_id,
            "import_batch_id": batch_id,
            "document_number": dto.document_number,
            "document_type": dto.document_type,
            "amount": amount,
            "direction": direction,
            "operation_date": dto.operation_date,
            "document_date": dto.document_date,
            "account_number": dto.account_number,
            "counterparty_account": dto.counterparty_account,
            "counterparty_inn": dto.counterparty_inn,
            "counterparty_name": dto.counterparty_name,
            "description": dto.description,
            "operation_category": "other",
            "created_at": datetime.utcnow(),
        }


class ImportValidationError(Exception):

    def __init__(self, message: str, index: int):
        self.message = message
        self.index = index
        super().__init__(message)