from app.db.database import SessionLocal
from app.services.operation_sync_service import OperationSyncService


def run():

    db = SessionLocal()

    service = OperationSyncService(db)

    service.sync_operations()

    db.close()


if __name__ == "__main__":
    run()