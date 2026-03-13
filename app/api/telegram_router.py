import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.user import User
from app.models.role import Role
from app.models.user_role import UserRole
from app.models.telegram_account import TelegramAccount
from app.models.company import Company

from app.repositories.manager_request_repository import ManagerRequestRepository
from app.models.manager_request import ManagerRequest

router = APIRouter(prefix="/telegram", tags=["telegram"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# регистрация telegram пользователя
@router.post("/register")
def register_telegram_user(
        telegram_id: int,
        username: str | None = None,
        db: Session = Depends(get_db)
):

    print("REGISTER REQUEST")
    print("telegram_id:", telegram_id)
    print("username:", username)

    existing = db.query(TelegramAccount).filter_by(telegram_id=telegram_id).first()

    if existing:
        return {"status": "already_registered"}

    company = db.query(Company).first()

    if not company:
        return {"error": "no company found"}

    user = User(
        id=uuid.uuid4(),
        company_id=company.id,
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

    role = db.query(Role).filter_by(name="manager").first()

    user_role = UserRole(
        id=uuid.uuid4(),
        user_id=user.id,
        role_id=role.id
    )

    db.add(user_role)

    db.commit()

    return {"status": "registered"}


# менеджер запрашивает отслеживание ИНН
@router.post("/track")
def request_track_inn(
        telegram_id: int,
        inn: str,
        db: Session = Depends(get_db)
):

    telegram_account = (
        db.query(TelegramAccount)
        .filter(TelegramAccount.telegram_id == telegram_id)
        .first()
    )

    if not telegram_account:
        return {"error": "user not registered"}

    manager_id = telegram_account.user_id

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
        "inn": inn
    }


# получить pending запросы
@router.get("/requests/pending")
def get_pending_requests(db: Session = Depends(get_db)):

    repo = ManagerRequestRepository()

    requests = repo.get_pending_requests(db)

    return [
        {
            "id": str(r.id),
            "inn": r.inn,
            "manager_id": str(r.manager_id),
            "status": r.status
        }
        for r in requests
    ]


# отклонить запрос
@router.post("/requests/{request_id}/reject")
def reject_request(
        request_id: str,
        director_id: int,
        db: Session = Depends(get_db)
):

    repo = ManagerRequestRepository()

    request = repo.get_by_id(db, request_id)

    if not request:
        return {"error": "request not found"}

    telegram = (
        db.query(TelegramAccount)
        .filter(TelegramAccount.telegram_id == director_id)
        .first()
    )

    if not telegram:
        return {"error": "director not found"}

    director_user_id = telegram.user_id

    repo.reject_request(
        db=db,
        request=request,
        director_id=director_user_id
    )

    return {"status": "rejected"}


# одобрить запрос
@router.post("/requests/{request_id}/approve")
def approve_request(
        request_id: str,
        director_id: int,
        db: Session = Depends(get_db)
):

    repo = ManagerRequestRepository()

    request = repo.get_by_id(db, request_id)

    if not request:
        return {"error": "request not found"}

    telegram = (
        db.query(TelegramAccount)
        .filter(TelegramAccount.telegram_id == director_id)
        .first()
    )

    if not telegram:
        return {"error": "director not found"}

    director_user_id = telegram.user_id

    repo.approve_request(
        db=db,
        request=request,
        director_id=director_user_id
    )

    return {"status": "approved"}


# получить директоров
@router.get("/directors")
def get_directors(db: Session = Depends(get_db)):

    result = (
        db.query(TelegramAccount.telegram_id)
        .join(User, TelegramAccount.user_id == User.id)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .filter(Role.name == "director")
        .all()
    )

    return [
        {"telegram_id": r.telegram_id}
        for r in result
    ]