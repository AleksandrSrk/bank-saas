from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.services.tochka_sync_service import TochkaSyncService

router = APIRouter(prefix="/sync", tags=["bank sync"])


@router.post("/tochka")
def sync_tochka(
    company_id: str,
    db: Session = Depends(get_db)
):

    result = TochkaSyncService.sync_company(
        db=db,
        company_id=company_id
    )

    return result