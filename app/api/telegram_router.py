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
from app.models.user_company import UserCompany
from app.models.tracked_company import TrackedCompany
from app.models.manager_request import ManagerRequest

from app.repositories.manager_request_repository import ManagerRequestRepository
from app.repositories.tracked_company_repository import TrackedCompanyRepository
from app.repositories.bank_operation_repository import BankOperationRepository

from app.services.company_service import ensure_company_exists
from app.services.tochka_sync_service import TochkaSyncService

from app.models.user_registration_request import UserRegistrationRequest
from datetime import datetime
from app.services.company_service import get_user_companies
from app.models.legal_entity import LegalEntity


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

    request = UserRegistrationRequest(
        id=uuid.uuid4(),
        user_id=user.id,
        status="pending"
    )

    db.add(request)

    db.commit()

    return {
        "status": "pending_approval",
        "request_id": str(request.id),
        "username": username
    }


# ---------------- TRACK COMPANY ----------------

@router.post("/track")
def request_track_inn(
    telegram_id: int,
    inn: str,
    db: Session = Depends(get_db)
):

    # очищаем ИНН
    inn = "".join(filter(str.isdigit, inn))

    telegram_account = (
        db.query(TelegramAccount)
        .filter(TelegramAccount.telegram_id == telegram_id)
        .first()
    )

    if not telegram_account:
        return {"error": "user_not_registered"}

    manager_id = telegram_account.user_id

    # ищем компанию в БД
    company = db.query(Company).filter(
        Company.inn == inn
    ).first()

    # --- если компании НЕТ → идём в Dadata

    if not company:

        company = ensure_company_exists(db, inn)

        # ❗ если Dadata НЕ вернула компанию → стоп
        if not company:
            return {
                "status": "invalid_inn"
            }

        # новая компания
        company.status = "new"
        db.commit()

        company_status = "new"

    else:
        company_status = company.status

    # --- проверка: уже отслеживается

    existing = db.query(TrackedCompany).filter(
        TrackedCompany.manager_id == manager_id,
        TrackedCompany.company_id == company.id,
        TrackedCompany.active == True
    ).first()

    if existing:
        return {
            "status": "already_tracking",
            "company_name": company.name
        }

    # --- создаём запрос

    request = ManagerRequest(
        manager_id=manager_id,
        inn=inn,
        status="pending"
    )

    db.add(request)
    db.commit()

    return {
        "status": "ok",
        "request_id": str(request.id),
        "company_name": company.name,
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

    if not telegram_account:
        return []

    user_id = telegram_account.user_id

    repo = TrackedCompanyRepository()

    tracked = repo.get_manager_companies(db, user_id)

    result = []

    for tracked_company, name, inn in tracked:

        result.append({
            "company_id": str(tracked_company.company_id),
            "name": name,
            "inn": inn
        })

    return result


# ---------------- OPERATIONS ----------------

@router.get("/company_operations")
def get_company_operations(
    telegram_id: int,
    inn: str,
    days: int,
    details: bool = False,
    db: Session = Depends(get_db)
):

    telegram_account = (
        db.query(TelegramAccount)
        .filter(TelegramAccount.telegram_id == telegram_id)
        .first()
    )

    if not telegram_account:
        return {"error": "user_not_found"}

    user_id = telegram_account.user_id

    company = db.query(Company).filter(Company.inn == inn).first()

    if not company:
        return {"error": "company_not_found"}

    access = (
        db.query(UserCompany)
        .filter(
            UserCompany.user_id == user_id,
            UserCompany.company_id == company.id
        )
        .first()
    )

    if not access:
        return {"error": "access_denied"}

    repo = BankOperationRepository()

    return repo.get_operations_for_period(
        db=db,
        manager_id=user_id,
        inn=inn,
        days=days,
        details=details
    )


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


#_________________pending 

@router.get("/users/pending")
def get_pending_user_requests(db: Session = Depends(get_db)):

    requests = (
        db.query(UserRegistrationRequest, User, TelegramAccount)
        .join(User, User.id == UserRegistrationRequest.user_id)
        .join(TelegramAccount, TelegramAccount.user_id == User.id)
        .filter(UserRegistrationRequest.status == "pending")
        .all()
    )

    result = []

    for req, user, telegram in requests:
        result.append({
            "request_id": str(req.id),
            "user_id": str(user.id),
            "username": telegram.username,
            "telegram_id": telegram.telegram_id,
            "created_at": req.created_at
        })

    return result

#_____________________

@router.post("/users/{request_id}/approve")
def approve_user_request(
    request_id: str,
    director_telegram_id: int,
    db: Session = Depends(get_db)
):

    request = db.query(UserRegistrationRequest).filter(
        UserRegistrationRequest.id == request_id
    ).first()

    if not request:
        return {"status": "not_found"}

    director_account = db.query(TelegramAccount).filter(
        TelegramAccount.telegram_id == director_telegram_id
    ).first()

    if not director_account:
        return {"status": "director_not_found"}

    request.status = "approved"
    request.approved_by = director_account.user_id
    request.approved_at = datetime.utcnow()

    db.commit()

    return {"status": "approved"}

#____________________список пользователей

@router.get("/users")
def get_users(db: Session = Depends(get_db)):

    users = (
        db.query(User, TelegramAccount, Role)
        .join(TelegramAccount, TelegramAccount.user_id == User.id)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .filter(Role.name == "manager")
        .all()
    )

    result = []

    for user, telegram, role in users:
        result.append({
            "user_id": str(user.id),
            "name": user.name,
            "username": telegram.username,
            "telegram_id": telegram.telegram_id
        })

    return result

#__________________доступы пользователей к юрлицам

@router.get("/users/{user_id}/companies")
def get_user_company_access(
    user_id: str,
    db: Session = Depends(get_db)
):

    companies = (
        db.query(Company, UserCompany)
        .outerjoin(
            UserCompany,
            (UserCompany.company_id == Company.id) &
            (UserCompany.user_id == user_id)
        )
        .all()
    )

    result = []

    for company, access in companies:
        result.append({
            "company_id": str(company.id),
            "name": company.name,
            "inn": company.inn,
            "has_access": access is not None
        })

    return result

#____________________выдача и отзыв доступа

@router.post("/users/{user_id}/companies")
def update_user_companies(
    user_id: str,
    company_ids: list[str],
    db: Session = Depends(get_db)
):

    # удалить старые доступы
    db.query(UserCompany).filter(
        UserCompany.user_id == user_id
    ).delete()

    # добавить новые
    for company_id in company_ids:

        access = UserCompany(
            id=uuid.uuid4(),
            user_id=user_id,
            company_id=company_id
        )

        db.add(access)

    db.commit()

    return {"status": "access_updated"}

@router.post("/users/{user_id}/legal_entities")
def update_user_legal_entities(
    user_id: str,
    legal_entity_ids: list[str],
    db: Session = Depends(get_db)
):

    # удалить старые доступы
    db.query(UserCompany).filter(
        UserCompany.user_id == user_id
    ).delete()

    # добавить новые
    for entity_id in legal_entity_ids:

        access = UserCompany(
            id=uuid.uuid4(),
            user_id=user_id,
            legal_entity_id=entity_id
        )

        db.add(access)

    db.commit()

    return {"status": "access_updated"}

@router.get("/users/{user_id}/legal_entities")
def get_user_legal_entities(
    user_id: str,
    db: Session = Depends(get_db)
):

    entities = db.query(LegalEntity).all()

    user_access = (
        db.query(UserCompany.legal_entity_id)
        .filter(UserCompany.user_id == user_id)
        .distinct()
        .all()
    )

    access_ids = {str(e[0]) for e in user_access if e[0]}

    result = []

    for entity in entities:
        result.append({
            "legal_entity_id": str(entity.id),
            "name": entity.name,
            "inn": entity.inn,
            "has_access": str(entity.id) in access_ids
        })

    return result