from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.services.operation_sync_service import OperationSyncService

router = APIRouter(prefix="/sync", tags=["bank sync"])


@router.post("/tochka")
def sync_tochka(
    company_id: str,
    db: Session = Depends(get_db)
):

    service = OperationSyncService(db)

    service.sync_operations()

    return {"status": "sync_started"}