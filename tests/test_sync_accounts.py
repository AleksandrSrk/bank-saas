from app.db.database import SessionLocal
from app.services.account_sync_service import AccountSyncService


def run():

    db = SessionLocal()

    service = AccountSyncService(db)

    service.sync_accounts()

    db.close()


if __name__ == "__main__":
    run()