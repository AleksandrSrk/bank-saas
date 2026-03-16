from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyUpdate
from app.integrations.dadata.client import DadataClient


def create_company(db: Session, company_data: CompanyCreate) -> Company:

    company = Company(
        name=company_data.name,
        inn=company_data.inn,
        status="new"
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


def update_company(db: Session, company: Company, update_data: CompanyUpdate) -> Company:

    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(company, field, value)

    db.commit()
    db.refresh(company)

    return company


def delete_company(db: Session, company: Company) -> None:

    db.delete(company)
    db.commit()


# ---------------- MAIN LOGIC ----------------

def ensure_company_exists(db: Session, inn: str):

    company = db.query(Company).filter(Company.inn == inn).first()

    if company:
        return company

    dadata = DadataClient()

    data = dadata.find_company_by_inn(inn)

    # если компания не найдена в DaData
    if not data:

        company = Company(
            inn=inn,
            name=None,
            status="new"
        )

        db.add(company)
        db.flush()

        return company

    # компания найдена в DaData
    company = Company(
        inn=data["inn"],
        name=data["name"],
        status="new"
    )

    db.add(company)
    db.flush()

    return company