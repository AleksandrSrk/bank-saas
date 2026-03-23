from sqlalchemy.orm import Session

from app.integrations.banks.adapter_factory import BankAdapterFactory
from app.models.bank_account import BankAccount
from app.models.bank_connection import BankConnection


class AccountSyncService:

    def __init__(self, db: Session):
        self.db = db

    def sync_accounts(self):

        connections = self.db.query(BankConnection).all()

        for connection in connections:

            adapter = BankAdapterFactory.get_adapter(
                self.db,
                connection.bank_name
            )

            accounts = adapter.get_accounts()

            if not accounts:
                print(f"[{connection.bank_name}] no accounts returned")
                continue

            for acc in accounts:

                account_number = acc.get("account_number")

                if not account_number:
                    continue

                existing = (
                    self.db.query(BankAccount)
                    .filter(
                        BankAccount.account_number == account_number,
                        BankAccount.bank_connection_id == connection.id
                    )
                    .first()
                )

                if existing:
                    continue

                new_account = BankAccount(
                    company_id=connection.company_id,
                    bank_connection_id=connection.id,
                    account_number=account_number,
                    currency=acc.get("currency")
                )

                self.db.add(new_account)

        self.db.commit()