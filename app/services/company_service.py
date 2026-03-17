from uuid import UUID
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyUpdate
from app.integrations.dadata.client import DadataClient
from app.models.user_company import UserCompany


# ---------------- CRUD ----------------

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

    # 🔴 базовая проверка ИНН
    if len(inn) not in (10, 12):
        return None

    # ищем в БД
    company = db.query(Company).filter(Company.inn == inn).first()

    if company:
        return company

    dadata = DadataClient()

    data = dadata.find_company_by_inn(inn)

    # 🔴 ВАЖНО: если Dadata ничего не нашла → НЕ создаём компанию
    if not data:
        return None

    name = data.get("name")

    # дополнительная защита
    if not name:
        return None

    # создаём компанию ТОЛЬКО если есть нормальные данные
    company = Company(
        id=uuid.uuid4(),
        inn=data["inn"],
        name=name,
        status="new"
    )

    db.add(company)
    db.commit()

    return company


# ---------------- USER COMPANIES ----------------

def get_user_companies(db: Session, user_id: UUID):

    stmt = (
        select(Company)
        .join(UserCompany, UserCompany.company_id == Company.id)
        .where(UserCompany.user_id == user_id)
    )

    result = db.execute(stmt)

    return result.scalars().all()

# ---------------- СОЗДАТЬ КОМПАНИИ ДЛЯ ВСЕХ INN ИЗ ОПЕРАЦИЙ ----------------

def ensure_companies_from_operations(db: Session):
    """
    Создаёт компании для всех INN из bank_operations,
    которых ещё нет в таблице companies.
    """

    from app.models.bank_operation import BankOperation

    inns = (
        db.query(BankOperation.counterparty_inn)
        .distinct()
        .filter(BankOperation.counterparty_inn != None)
        .all()
    )

    created = 0

    for (inn,) in inns:

        existing = db.query(Company).filter(Company.inn == inn).first()

        if existing:
            continue

        # создаём "пустую" компанию (без Dadata)
        company = Company(
            id=uuid.uuid4(),
            inn=inn,
            name=f"INN {inn}",
            status="from_operations"
        )

        db.add(company)
        created += 1

    db.commit()

    print(f"Created companies: {created}")