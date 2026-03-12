from uuid import UUID
from pathlib import Path

from app.parsers.kl_to_1c_parser import parse_1c_client_bank
from app.services.import_service import ImportService
from app.db.database import SessionLocal


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def main():
    files = list(FIXTURES_DIR.glob("*.txt"))

    if not files:
        print("No test files found in fixtures")
        return

    db = SessionLocal()

    try:
        service = ImportService(db)

        for file_path in files:
            print(f"\nImporting file: {file_path.name}")

            dtos = parse_1c_client_bank(str(file_path))

            result = service.import_operations(
                dtos,
                UUID("11111111-1111-1111-1111-111111111111"),
                file_path.name
            )

            print(result)

    finally:
        db.close()


if __name__ == "__main__":
    main()