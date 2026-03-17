import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.db.database import SessionLocal
from app.services.operation_sync_service import OperationSyncService


def run():
    db = SessionLocal()

    try:
        service = OperationSyncService(db)
        service.sync_operations()
    finally:
        db.close()


if __name__ == "__main__":
    run()