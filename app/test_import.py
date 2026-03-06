from uuid import UUID

from app.parsers.kl_to_1c_parser import parse_1c_client_bank
from app.services.import_service import ImportService
from app.db.database import SessionLocal


file_path = "app/kl_to_1c_40702810020000066887_044525104_01.02.2026-27.02.2026.txt"

# парсим файл
dtos = parse_1c_client_bank(file_path)

# подключаемся к БД
db = SessionLocal()

service = ImportService(db)

result = service.import_operations(
    dtos,
    UUID("11111111-1111-1111-1111-111111111111"),
    "test_statement.txt"
)

print(result)