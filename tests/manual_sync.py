import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.db.database import SessionLocal
from app.services.account_sync_service import AccountSyncService
from app.services.operation_sync_service import OperationSyncService


def run():
    db = SessionLocal()

    try:
        print("🔄 Sync started")

        # 1. счета
        account_service = AccountSyncService(db)
        account_service.sync_accounts()

        # 2. операции
        operation_service = OperationSyncService(db)
        operation_service.sync_operations()

        print("✅ Sync finished")

    finally:
        db.close()


if __name__ == "__main__":
    run()