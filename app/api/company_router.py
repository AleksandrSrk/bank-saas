from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.schemas.company import CompanyCreate, CompanyRead, CompanyUpdate
from app.services.company_service import (
    create_company,
    get_company,
    get_companies,
    update_company,
    delete_company,
)

router = APIRouter(prefix="/companies", tags=["Companies"])


@router.post("/", response_model=CompanyRead)
def create(company_data: CompanyCreate, db: Session = Depends(get_db)):
    return create_company(db, company_data)


@router.get("/", response_model=list[CompanyRead])
def list_companies(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_companies(db, skip=skip, limit=limit)


@router.get("/{company_id}", response_model=CompanyRead)
def get(company_id: UUID, db: Session = Depends(get_db)):
    company = get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.patch("/{company_id}", response_model=CompanyRead)
def update(
    company_id: UUID,
    update_data: CompanyUpdate,
    db: Session = Depends(get_db),
):
    company = get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    return update_company(db, company, update_data)


@router.delete("/{company_id}")
def delete(company_id: UUID, db: Session = Depends(get_db)):
    company = get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    delete_company(db, company)
    return {"detail": "Company deleted"}