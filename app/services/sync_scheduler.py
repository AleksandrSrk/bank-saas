from apscheduler.schedulers.background import BackgroundScheduler

from app.db.database import SessionLocal
from app.services.operation_sync_service import OperationSyncService


scheduler = BackgroundScheduler()


def run_bank_sync():

    db = SessionLocal()

    try:
        service = OperationSyncService(db)
        service.sync_operations()

    finally:
        db.close()


def start_scheduler():

    scheduler.add_job(
        run_bank_sync,
        "interval",
        minutes=1
    )

    scheduler.start()