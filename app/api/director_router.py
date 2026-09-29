from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.db.dependencies import get_db
from app.models.telegram_account import TelegramAccount
from app.models.role import Role
from app.models.user_role import UserRole
from app.models.company import Company
from app.repositories.bank_operation_repository import BankOperationRepository

router = APIRouter(prefix="/director", tags=["director"])


def _is_director(db: Session, telegram_id: int) -> bool:
    """
    Проверка роли строго на входе: не директор — сразу отказ,
    дальше в функции ничего не выполняется.
    """
    telegram_account = (
        db.query(TelegramAccount)
        .filter(TelegramAccount.telegram_id == telegram_id)
        .first()
    )

    if not telegram_account:
        return False

    role = (
        db.query(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(
            UserRole.user_id == telegram_account.user_id,
            Role.name == "director"
        )
        .first()
    )

    return role is not None


@router.get("/companies/search")
def search_companies(telegram_id: int, q: str, db: Session = Depends(get_db)):

    if not _is_director(db, telegram_id):
        return {"error": "forbidden"}

    q = q.strip()

    if not q:
        return {"companies": []}

    # сначала точная подстрока по названию/ИНН (регистронезависимо)
    companies = (
        db.query(Company)
        .filter(
            or_(
                Company.name.ilike(f"%{q}%"),
                Company.inn.ilike(f"%{q}%")
            )
        )
        .order_by(Company.name)
        .limit(20)
        .all()
    )

    # если по подстроке ничего — пробуем нечёткий поиск (опечатки) через pg_trgm
    if not companies:
        companies = (
            db.query(Company)
            .filter(Company.name.op("%")(q))
            .order_by(Company.name.op("<->")(q))
            .limit(20)
            .all()
        )

    return {
        "companies": [
            {"name": c.name, "inn": c.inn} for c in companies
        ]
    }


@router.get("/company_operations")
def director_company_operations(
    telegram_id: int,
    inn: str,
    days: int,
    details: bool = False,
    db: Session = Depends(get_db),
):

    if not _is_director(db, telegram_id):
        return {"error": "forbidden"}

    telegram_account = (
        db.query(TelegramAccount)
        .filter(TelegramAccount.telegram_id == telegram_id)
        .first()
    )

    repo = BankOperationRepository()

    return repo.get_operations_for_period(
        db=db,
        manager_id=telegram_account.user_id,
        inn=inn,
        days=days,
        details=details,
        unrestricted=True,
    )
