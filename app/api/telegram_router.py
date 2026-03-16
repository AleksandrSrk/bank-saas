import uuid
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import SessionLocal

from app.models.user import User
from app.models.role import Role
from app.models.user_role import UserRole
from app.models.telegram_account import TelegramAccount
from app.models.company import Company
from app.models.tracked_company import TrackedCompany
from app.models.manager_request import ManagerRequest

from app.repositories.manager_request_repository import ManagerRequestRepository
from app.repositories.tracked_company_repository import TrackedCompanyRepository
from app.repositories.bank_operation_repository import BankOperationRepository

from app.services.company_service import ensure_company_exists
from app.services.tochka_sync_service import TochkaSyncService


router = APIRouter(prefix="/telegram", tags=["telegram"])


# ---------------- DB ----------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------- REGISTER ----------------

@router.post("/register")
def register_telegram_user(
    telegram_id: int,
    username: str | None = None,
    db: Session = Depends(get_db)
):

    existing = db.query(TelegramAccount).filter(
        TelegramAccount.telegram_id == telegram_id
    ).first()

    if existing:
        return {"status": "already_registered"}

    user = User(
        id=uuid.uuid4(),
        name=username
    )

    db.add(user)
    db.flush()

    telegram = TelegramAccount(
        id=uuid.uuid4(),
        user_id=user.id,
        telegram_id=telegram_id,
        username=username
    )

    db.add(telegram)

    role = db.query(Role).filter(Role.name == "manager").first()

    user_role = UserRole(
        id=uuid.uuid4(),
        user_id=user.id,
        role_id=role.id
    )

    db.add(user_role)

    db.commit()

    return {"status": "registered"}


# ---------------- TRACK COMPANY ----------------

@router.post("/track")
def request_track_inn(
    telegram_id: int,
    inn: str,
    db: Session = Depends(get_db)
):

    inn = "".join(filter(str.isdigit, inn))

    telegram_account = (
        db.query(TelegramAccount)
        .filter(TelegramAccount.telegram_id == telegram_id)
        .first()
    )

    if not telegram_account:
        return {"error": "user_not_registered"}

    manager_id = telegram_account.user_id

    company = db.query(Company).filter(
        Company.inn == inn
    ).first()

    # --- компания есть в системе

    if company:

        company_status = company.status or "reserved"

    # --- компании нет

    else:

        company = ensure_company_exists(db, inn)

        if company.status == "unknown":

            return {
                "status": "invalid_inn",
                "message": "Проверьте корректность ИНН"
            }

        company_status = "new"

    tracked_repo = TrackedCompanyRepository()

    if tracked_repo.is_company_tracked(db, manager_id, company.id):

        return {
            "status": "already_tracking",
            "company_name": company.name,
            "inn": company.inn
        }

    repo = ManagerRequestRepository()

    request = repo.create_request(
        db=db,
        manager_id=manager_id,
        inn=inn
    )

    db.commit()

    return {
        "status": "request_created",
        "request_id": str(request.id),
        "company_name": company.name,
        "inn": company.inn,
        "company_status": company_status
    }


# ---------------- REQUEST INFO ----------------

@router.get("/request_info")
def request_info(request_id: str, db: Session = Depends(get_db)):

    request = (
        db.query(ManagerRequest)
        .filter(ManagerRequest.id == request_id)
        .first()
    )

    if not request:
        return {"error": "request_not_found"}

    company = db.query(Company).filter(
        Company.inn == request.inn
    ).first()

    if not company:
        return {
            "inn": request.inn,
            "company_name": None,
            "company_status": "new"
        }

    return {
        "inn": request.inn,
        "company_name": company.name,
        "company_status": company.status
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
        director_id=director_user_id
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
        "company_name": company_name
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
        director_id=director_user_id
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
        "inn": request.inn
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


# ---------------- DIRECTORS ----------------

@router.get("/directors")
def get_directors(db: Session = Depends(get_db)):

    directors = (
        db.query(TelegramAccount.telegram_id)
        .join(User, User.id == TelegramAccount.user_id)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .filter(Role.name == "director")
        .all()
    )

    return [{"telegram_id": d[0]} for d in directors]


# ---------------- USER ROLE ----------------

@router.get("/user_role")
def get_user_role(telegram_id: int, db: Session = Depends(get_db)):

    role = (
        db.query(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .join(User, User.id == UserRole.user_id)
        .join(TelegramAccount, TelegramAccount.user_id == User.id)
        .filter(TelegramAccount.telegram_id == telegram_id)
        .first()
    )

    if not role:
        return {"role": "manager"}

    return {"role": role[0]}


# ---------------- MANAGERS + COMPANIES ----------------

@router.get("/managers_companies")
def managers_companies(db: Session = Depends(get_db)):

    managers = (
        db.query(User)
        .join(UserRole)
        .join(Role)
        .filter(Role.name == "manager")
        .all()
    )

    repo = TrackedCompanyRepository()

    result = []

    for manager in managers:

        companies = repo.get_manager_companies(db, manager.id)

        if not companies:

            result.append({
                "manager_name": manager.name,
                "companies": []
            })

        else:

            items = []

            for tracked, name, inn in companies:

                items.append({
                    "tracked_id": str(tracked.id),
                    "name": name,
                    "inn": inn
                })

            result.append({
                "manager_name": manager.name,
                "companies": items
            })

    return result


# ---------------- REVOKE ACCESS ----------------

@router.post("/revoke_access")
def revoke_access(tracked_id: str, db: Session = Depends(get_db)):

    tracked = db.query(TrackedCompany).filter(
        TrackedCompany.id == tracked_id
    ).first()

    if not tracked:
        return {"error": "not_found"}

    company = db.query(Company).filter(
        Company.id == tracked.company_id
    ).first()

    manager_account = db.query(TelegramAccount).filter(
        TelegramAccount.user_id == tracked.manager_id
    ).first()

    tracked.active = False

    db.commit()

    return {
        "status": "revoked",
        "inn": company.inn,
        "company_name": company.name,
        "manager_telegram_id": manager_account.telegram_id
    }


# ---------------- MANUAL SYNC ----------------

@router.post("/sync_company")
def sync_company(company_id: str, db: Session = Depends(get_db)):

    return TochkaSyncService.sync_company(
        db=db,
        company_id=UUID(company_id)
    )