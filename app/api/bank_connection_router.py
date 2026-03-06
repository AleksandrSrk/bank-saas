from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.schemas.bank_connection import BankConnectionCreate
from app.services.bank_connection_service import BankConnectionService

router = APIRouter(prefix="/bank-connections", tags=["bank connections"])


@router.post("/")
def create_bank_connection(
    data: BankConnectionCreate,
    db: Session = Depends(get_db)
):

    connection = BankConnectionService.create_connection(
        db=db,
        company_id=data.company_id,
        bank_name=data.bank_name,
        access_token=data.access_token,
        refresh_token=data.refresh_token,
        expires_in=data.expires_in
    )

    return {
        "id": str(connection.id),
        "bank": connection.bank_name
    }