import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.database import SessionLocal
from app.models.user import User
from app.models.role import Role
from app.models.user_role import UserRole
from app.models.telegram_account import TelegramAccount
from app.models.company import Company
from app.models.tracked_company import TrackedCompany

from app.repositories.manager_request_repository import ManagerRequestRepository
from app.repositories.tracked_company_repository import TrackedCompanyRepository
from app.repositories.bank_operation_repository import BankOperationRepository

router = APIRouter(prefix="/telegram", tags=["telegram"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------- REGISTER ----------------

@router.post("/register")
def register_telegram_user(telegram_id: int, username: str | None = None, db: Session = Depends(get_db)):

    existing = db.query(TelegramAccount).filter_by(telegram_id=telegram_id).first()

    if existing:
        return {"status": "already_registered"}

    company = db.query(Company).first()

    user = User(
        id=uuid.uuid4(),
        company_id=company.id,
        name=username,
    )

    db.add(user)
    db.flush()

    telegram = TelegramAccount(
        id=uuid.uuid4(),
        user_id=user.id,
        telegram_id=telegram_id,
        username=username,
    )

    db.add(telegram)

    role = db.query(Role).filter_by(name="manager").first()

    user_role = UserRole(
        id=uuid.uuid4(),
        user_id=user.id,
        role_id=role.id,
    )

    db.add(user_role)

    db.commit()

    return {"status": "registered"}


# ---------------- TRACK ----------------

@router.post("/track")
def request_track_inn(telegram_id: int, inn: str, db: Session = Depends(get_db)):

    # нормализация ИНН
    inn = "".join(filter(str.isdigit, inn))

    telegram_account = (
        db.query(TelegramAccount)
        .filter(TelegramAccount.telegram_id == telegram_id)
        .first()
    )

    if not telegram_account:
        return {"error": "user not registered"}

    manager_id = telegram_account.user_id

    company = (
        db.query(Company)
        .filter(func.trim(Company.inn) == inn)
        .first()
    )

    is_new_company = False

    if not company:

        company = Company(
            inn=inn,
            name=None,
            status="reserved",
        )

        db.add(company)
        db.flush()

        is_new_company = True

    tracked_repo = TrackedCompanyRepository()

    if tracked_repo.is_company_tracked(db, manager_id, company.id):

        return {
            "status": "already_tracking",
            "company_name": company.name,
        }

    repo = ManagerRequestRepository()

    request = repo.create_request(
        db=db,
        manager_id=manager_id,
        inn=inn,
    )

    db.commit()

    return {
        "status": "request_created",
        "request_id": str(request.id),
        "inn": inn,
        "company_name": company.name,
        "is_new_company": is_new_company,
    }


# ---------------- APPROVE ----------------

@router.post("/requests/{request_id}/approve")
def approve_request(request_id: str, director_id: int, db: Session = Depends(get_db)):

    repo = ManagerRequestRepository()

    request = repo.get_by_id(db, request_id)

    telegram = (
        db.query(TelegramAccount)
        .filter(TelegramAccount.telegram_id == director_id)
        .first()
    )

    director_user_id = telegram.user_id

    request, company_name = repo.approve_request(
        db=db,
        request=request,
        director_id=director_user_id,
    )

    db.commit()

    manager_account = (
        db.query(TelegramAccount)
        .filter(TelegramAccount.user_id == request.manager_id)
        .first()
    )

    return {
        "status": "approved",
        "manager_telegram_id": manager_account.telegram_id,
        "inn": request.inn,
        "company_name": company_name,
    }


# ---------------- REJECT ----------------

@router.post("/requests/{request_id}/reject")
def reject_request(request_id: str, director_id: int, db: Session = Depends(get_db)):

    repo = ManagerRequestRepository()

    request = repo.get_by_id(db, request_id)

    telegram = (
        db.query(TelegramAccount)
        .filter(TelegramAccount.telegram_id == director_id)
        .first()
    )

    director_user_id = telegram.user_id

    request = repo.reject_request(
        db=db,
        request=request,
        director_id=director_user_id,
    )

    db.commit()

    manager_account = (
        db.query(TelegramAccount)
        .filter(TelegramAccount.user_id == request.manager_id)
        .first()
    )

    return {
        "status": "rejected",
        "manager_telegram_id": manager_account.telegram_id,
        "inn": request.inn,
    }


# ---------------- MY COMPANIES ----------------

@router.get("/my_companies")
def get_my_companies(telegram_id: int, db: Session = Depends(get_db)):

    telegram_account = (
        db.query(TelegramAccount)
        .filter(TelegramAccount.telegram_id == telegram_id)
        .first()
    )

    manager_id = telegram_account.user_id

    repo = TrackedCompanyRepository()

    companies = repo.get_manager_companies(db, manager_id)

    result = []

    for tracked, name, inn in companies:

        result.append({
            "name": name,
            "inn": inn
        })

    return result


# ---------------- OPERATIONS ----------------

@router.get("/company_operations")
def get_company_operations(telegram_id: int, inn: str, days: int, db: Session = Depends(get_db)):

    telegram_account = (
        db.query(TelegramAccount)
        .filter(TelegramAccount.telegram_id == telegram_id)
        .first()
    )

    manager_id = telegram_account.user_id

    repo = BankOperationRepository()

    return repo.get_operations_for_period(db, manager_id, inn, days)


from uuid import UUID
from fastapi import Depends
from sqlalchemy.orm import Session

# from app.db.database import get_db
from app.services.tochka_sync_service import TochkaSyncService


@router.post("/debug/sync")
def debug_sync(db: Session = Depends(get_db)):

    result = TochkaSyncService.sync_company(
        db=db,
        company_id=UUID("11111111-1111-1111-1111-111111111111")
    )

    return result