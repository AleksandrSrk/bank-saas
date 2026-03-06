from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session
from uuid import UUID
import tempfile

from app.db.dependencies import get_db
from app.services.import_service import ImportService
from app.parsers.kl_to_1c_parser import parse_1c_client_bank

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("/bank-statement")
async def import_bank_statement(
    company_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    # сохраняем файл во временный
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    # парсим операции
    operations = list(parse_1c_client_bank(tmp_path))

    # запускаем импорт
    service = ImportService(db)

    result = service.import_operations(
    operations,
    company_id,
    file.filename
)

    return result