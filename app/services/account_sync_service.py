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
            account_number = account_id.split("/")[0]

            existing = (
                self.db.query(BankAccount)
                .filter(BankAccount.account_number == account_number)
                .first()
            )

            if existing:
                continue

            new_account = BankAccount(
                company_id=self.client.connection.company_id,
                bank_connection_id=self.client.connection.id,
                account_number=account_number,
                currency=acc["currency"]
            )

            self.db.add(new_account)

        self.db.commit()