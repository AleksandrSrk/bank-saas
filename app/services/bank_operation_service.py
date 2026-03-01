from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from app.models.bank_operation import BankOperation
from app.schemas.bank_operation import BankOperationCreate

from sqlalchemy import select
from app.models.bank_operation import BankOperation
from sqlalchemy import func

from datetime import datetime, time


def bulk_create_operations(
    db: Session,
    company_id,
    operations: list[BankOperationCreate]
):
    if not operations:
        return {"created": 0, "duplicates": 0}

    values = [
        {
            "company_id": company_id,
            "bank_operation_id": op.bank_operation_id,
            "inn": op.inn,
            "amount": op.amount,
            "operation_date": op.operation_date,
        }
        for op in operations
    ]

    stmt = insert(BankOperation).values(values)

    stmt = stmt.on_conflict_do_nothing(
        index_elements=["company_id", "bank_operation_id"]
    )

    result = db.execute(stmt)
    db.commit()

    created = result.rowcount
    duplicates = len(operations) - created

    return {
        "created": created,
        "duplicates": duplicates
    }


def get_company_operations(
    db: Session,
    company_id,
    inn: str | None = None,
    date_from=None,
    date_to=None,
):
    stmt = select(BankOperation).where(
        BankOperation.company_id == company_id
    )

    if inn:
        stmt = stmt.where(BankOperation.inn == inn)

    if date_from:
        stmt = stmt.where(BankOperation.operation_date >= datetime.combine(date_from, time.min))

    if date_to:
        stmt = stmt.where(BankOperation.operation_date >= datetime.combine(date_from, time.min))

    stmt = stmt.order_by(BankOperation.operation_date.desc())

    result = db.execute(stmt)
    return result.scalars().all()

def get_company_summary(
    db: Session,
    company_id,
    inn: str | None = None,
    date_from=None,
    date_to=None,
):
    stmt = select(
        func.count(BankOperation.id),
        func.sum(BankOperation.amount)
    ).where(
        BankOperation.company_id == company_id
    )

    if inn:
        stmt = stmt.where(BankOperation.inn == inn)

    if date_from:
        stmt = stmt.where(BankOperation.operation_date >= datetime.combine(date_from, time.min))

    if date_to:
        stmt = stmt.where(BankOperation.operation_date >= datetime.combine(date_from, time.min))

    result = db.execute(stmt).first()

    total_count = result[0] or 0
    total_amount = result[1] or 0

    return {
        "total_operations": total_count,
        "total_amount": float(total_amount)
    }