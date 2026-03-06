from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from datetime import date

from app.db.dependencies import get_db

from app.schemas.bank_operation import (
    BankOperationCreate,
    BankOperationRead
) 
from app.models.bank_operation import BankOperation
from app.services.company_service import get_company

from app.services.bank_operation_service import (
    bulk_create_operations,
    get_company_operations,
    get_company_summary,
)
router = APIRouter(
    prefix="/companies/{company_id}/operations",
    tags=["Bank Operations"]
)


@router.post("/bulk")
def create_operations(
    company_id: UUID,
    operations: list[BankOperationCreate],
    db: Session = Depends(get_db)
):
    company = get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    return bulk_create_operations(db, company_id, operations)


@router.get("/", response_model=list[BankOperationRead])
def list_operations(
    company_id: UUID,
    inn: str | None = None,
    date_from: date | None = None, 
    date_to: date | None = None,
    db: Session = Depends(get_db),
):
    company = get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    return get_company_operations(
        db=db,
        company_id=company_id,
        inn=inn,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/summary")
def operations_summary(
    company_id: UUID,
    inn: str | None = None,
    date_from: date | None = None, 
    date_to: date | None = None,
    db: Session = Depends(get_db),
):
    company = get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    return get_company_summary(
        db=db,
        company_id=company_id,
        inn=inn,
        date_from=date_from,
        date_to=date_to,
    )
@router.get("/operations")
def get_operations(
    company_id: str,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):

    operations = (
        db.query(BankOperation)
        .filter(BankOperation.company_id == company_id)
        .order_by(BankOperation.operation_date.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return operations