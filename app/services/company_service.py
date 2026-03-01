from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyUpdate


def create_company(db: Session, company_data: CompanyCreate) -> Company:
    company = Company(
        name=company_data.name,
        inn=company_data.inn,
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def get_company(db: Session, company_id: UUID) -> Company | None:
    stmt = select(Company).where(Company.id == company_id)
    result = db.execute(stmt)
    return result.scalar_one_or_none()


def get_companies(db: Session, skip: int = 0, limit: int = 100):
    stmt = select(Company).offset(skip).limit(limit)
    result = db.execute(stmt)
    return result.scalars().all()


def update_company(
    db: Session,
    company: Company,
    update_data: CompanyUpdate
) -> Company:
    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(company, field, value)

    db.commit()
    db.refresh(company)
    return company


def delete_company(db: Session, company: Company) -> None:
    db.delete(company)
    db.commit()