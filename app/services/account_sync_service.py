from sqlalchemy.orm import Session

from app.integrations.banks.tochka.client import TochkaClient
from app.models.bank_account import BankAccount


class AccountSyncService:

    def __init__(self, db: Session):
        self.db = db
        self.client = TochkaClient(db)

    def sync_accounts(self):

        data = self.client.get_accounts()

        accounts = data["Data"]["Account"]

        for acc in accounts:

            account_id = acc["accountId"]

            existing = (
                self.db.query(BankAccount)
                .filter(BankAccount.bank_account_id == account_id)
                .first()
            )

            if existing:
                continue

            new_account = BankAccount(
                bank_account_id=account_id,
                currency=acc["currency"],
                account_type=acc["accountType"],
                account_sub_type=acc["accountSubType"],
                status=acc["status"]
            )

            self.db.add(new_account)

        self.db.commit()