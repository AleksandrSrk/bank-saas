from apscheduler.schedulers.background import BackgroundScheduler

from app.db.database import SessionLocal
from app.services.operation_sync_service import OperationSyncService
from app.services.account_sync_service import AccountSyncService
from app.services.drive_backup import backup_database

scheduler = BackgroundScheduler()




def run_bank_sync():
    db = SessionLocal()

    try:
        # 1. СНАЧАЛА счета
        account_service = AccountSyncService(db)
        account_service.sync_accounts()

        # 2. ПОТОМ операции
        operation_service = OperationSyncService(db)
        operation_service.sync_operations()

    except Exception as e:
        # Avoid printing sensitive runtime context to stdout.
        # If needed, add structured logging with redaction.
        raise

    finally:
        db.close()


def start_scheduler():

    scheduler.add_job(
        run_bank_sync,
        "interval",
        minutes=5,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=30
    )

    scheduler.add_job(
        backup_database, "cron", day_of_week="mon,wed,fri", hour=3, minute=0
    )
    scheduler.add_job(backup_database, "date")  # разовый прогон сразу при старте

    scheduler.start()