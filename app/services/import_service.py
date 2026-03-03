from typing import Iterable
from uuid import UUID
from sqlalchemy.orm import Session

from app.domain.dto import OperationImportDTO, ImportResult
from app.domain.enums import ImportStatus
from app.models.operation_batch import OperationBatch

from decimal import Decimal
from app.domain.dto import OperationImportDTO

class ImportService:

    def __init__(self, db: Session):
        self.db = db

    def import_operations(
        self,
        dtos: Iterable[OperationImportDTO],
        company_id: UUID,
        filename: str,
    ) -> ImportResult:
        """
        Основной метод импорта операций.
        """

        batch = self._create_batch(company_id, filename)

        try:
            total_count = 0

            # TODO: валидация DTO
            # TODO: формирование ORM-объектов
            # TODO: bulk insert
            # TODO: подсчёт duplicate

            batch.status = ImportStatus.SUCCESS.value
            self.db.commit()

            return ImportResult(
                batch_id=batch.id,
                status=ImportStatus.SUCCESS,
                total_count=total_count,
                inserted_count=0,
                duplicate_count=0,
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

        # 1. Обязательные поля
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

        # 2. Debit / Credit логика
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

        # 3. Проверка > 0
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
    
class ImportValidationError(Exception):
    def __init__(self, message: str, index: int):
        self.message = message
        self.index = index
        super().__init__(message)