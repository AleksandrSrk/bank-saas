from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.services.balance_service import BalanceService


router = APIRouter(prefix="/balances", tags=["balances"])


@router.get("/")
def get_balances(db: Session = Depends(get_db)):
    return BalanceService.get_balances(db)

