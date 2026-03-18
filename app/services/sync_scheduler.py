from apscheduler.schedulers.background import BackgroundScheduler

from app.db.database import SessionLocal
from app.services.operation_sync_service import OperationSyncService


scheduler = BackgroundScheduler()


def run_bank_sync():

    print("🔄 Sync started")

    db = SessionLocal()

    try:
        service = OperationSyncService(db)
        service.sync_operations()
        print("✅ Sync finished")

    except Exception as e:
        print("❌ Sync error:", e)

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

    scheduler.start()