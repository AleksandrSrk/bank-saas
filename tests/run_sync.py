from app.db.database import SessionLocal
from app.services.operation_sync_service import OperationSyncService

db = SessionLocal()

service = OperationSyncService(db)
service.sync_operations()

print("SYNC DONE")