from datetime import datetime

from sqlalchemy.orm import Session

from app.integrations.banks.tochka.client import TochkaClient
from app.models.bank_account import BankAccount
from app.models.bank_operation import BankOperation
import uuid


class OperationSyncService:

    def __init__(self, db: Session):

        self.db = db
        self.client = TochkaClient(db)

    def sync_operations(self):

        accounts = self.db.query(BankAccount).all()

        for account in accounts:

            if account.last_synced_at:
                start_date = account.last_synced_at.strftime("%Y-%m-%d")
            else:
                start_date = "2023-01-01"

            end_date = datetime.utcnow().strftime("%Y-%m-%d")

            statement_id = self.client.create_statement(
                account.bank_account_id,
                start_date,
                end_date
            )

            transactions = self.client.get_transactions(statement_id)

            print(
                f"Account {account.bank_account_id} "
                f"transactions: {len(transactions)}"
            )

            for tx in transactions:
                existing = self.db.query(BankOperation).filter_by(
                    company_id=uuid.UUID("7da25e26-689d-4bff-ab3d-5bcb444b69af"),
                    document_number=tx.get("documentNumber", "unknown"),
                    document_type=tx.get("transactionTypeCode", "bank_operation"),
                    operation_date=tx["documentProcessDate"],
                    amount=tx["Amount"]["amount"],
                    direction="incoming" if tx["creditDebitIndicator"] == "Credit" else "outgoing"
                ).first()

                if existing:
                    continue

                operation = BankOperation(

                    company_id=uuid.UUID("7da25e26-689d-4bff-ab3d-5bcb444b69af"),

                    # import_batch_id=None,

                    document_number=tx.get("documentNumber", "unknown"),
                    document_type=tx.get("transactionTypeCode", "bank_operation"),

                    amount=tx["Amount"]["amount"],

                    direction="incoming"
                    if tx["creditDebitIndicator"] == "Credit"
                    else "outgoing",

                    operation_date=tx["documentProcessDate"],

                    document_date=tx.get("documentProcessDate"),

                    account_number=account.bank_account_id,

                    counterparty_account=(
                        tx.get("CreditorAccount", {}).get("identification")
                    ),

                    counterparty_inn=(
                        tx.get("CreditorParty", {}).get("inn")
                    ),

                    counterparty_name=(
                        tx.get("CreditorParty", {}).get("name")
                    ),

                    description=tx.get("description")
                )

                self.db.add(operation)

            account.last_synced_at = datetime.utcnow()

        self.db.commit()