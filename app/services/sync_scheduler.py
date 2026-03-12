from apscheduler.schedulers.background import BackgroundScheduler

from app.db.database import SessionLocal
from app.models.bank_connection import BankConnection
from app.services.tochka_sync_service import TochkaSyncService


def run_bank_sync():

    db = SessionLocal()

    try:

        connections = db.query(BankConnection).all()

        for connection in connections:

            if connection.bank_name == "tochka":

                result = TochkaSyncService.sync_company(
                    db=db,
                    company_id=connection.company_id
                )

                print("AUTO SYNC:", result)

    finally:
        db.close()


def start_scheduler():

    scheduler = BackgroundScheduler()

    scheduler.add_job(
        run_bank_sync,
        "interval",
        minutes=5
    )

    scheduler.start()