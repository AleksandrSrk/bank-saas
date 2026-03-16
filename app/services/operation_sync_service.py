from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.integrations.banks.tochka.client import TochkaClient
from app.models.bank_account import BankAccount
from app.models.bank_operation import BankOperation
from app.models.operation_batch import OperationBatch


class OperationSyncService:

    def __init__(self, db: Session):
        self.db = db
        self.client = TochkaClient(db)

    def sync_operations(self):

        accounts = self.db.query(BankAccount).all()

        for account in accounts:

            now = datetime.utcnow()

            # ---------- период синхронизации ----------

            if account.last_synced_at:

                start_date = account.last_synced_at - timedelta(days=1)

            else:

                start_date = now.replace(year=now.year - 1)

            end_date = now

            # ---------- получаем statement ----------

            statement_id = self.client.create_statement(
                account.account_number,
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d")
            )

            transactions = self.client.get_transactions(statement_id)

            print(
                f"Account {account.account_number} transactions: {len(transactions)}"
            )

            if not transactions:
                account.last_synced_at = now
                continue

            # ---------- создаём batch ----------

            batch = OperationBatch(
                company_id=account.company_id,
                source_type="bank_api",
                total_count=len(transactions),
                status="processing"
            )

            self.db.add(batch)
            self.db.flush()

            inserted = 0
            duplicates = 0

            for tx in transactions:

                amount = tx.get("Amount", {}).get("amount")

                if not amount:
                    continue

                direction = (
                    "incoming"
                    if tx.get("creditDebitIndicator") == "Credit"
                    else "outgoing"
                )

                operation_date_raw = tx.get("documentProcessDate")

                if not operation_date_raw:
                    continue

                operation_date = datetime.strptime(
                    operation_date_raw,
                    "%Y-%m-%d"
                )

                document_number = tx.get("transactionId")

                # ---------- проверка дублей ----------

                existing = self.db.query(BankOperation).filter_by(
                    company_id=account.company_id,
                    document_number=document_number,
                    document_type="bank_payment",
                    operation_date=operation_date,
                    amount=amount,
                    direction=direction
                ).first()

                if existing:
                    duplicates += 1
                    continue

                # ---------- определяем контрагента ----------

                if direction == "incoming":

                    counterparty_account = tx.get(
                        "DebtorAccount", {}
                    ).get("identification")

                    counterparty_inn = tx.get(
                        "DebtorParty", {}
                    ).get("inn")

                    counterparty_name = tx.get(
                        "DebtorParty", {}
                    ).get("name")

                else:

                    counterparty_account = tx.get(
                        "CreditorAccount", {}
                    ).get("identification")

                    counterparty_inn = tx.get(
                        "CreditorParty", {}
                    ).get("inn")

                    counterparty_name = tx.get(
                        "CreditorParty", {}
                    ).get("name")

                # ---------- создаём операцию ----------

                operation = BankOperation(

                    company_id=account.company_id,
                    import_batch_id=batch.id,

                    document_number=document_number,
                    document_type="bank_payment",

                    amount=amount,
                    direction=direction,

                    operation_date=operation_date,
                    document_date=operation_date.date(),

                    account_number=account.account_number,

                    counterparty_account=counterparty_account,
                    counterparty_inn=counterparty_inn,
                    counterparty_name=counterparty_name,

                    description=tx.get("description")
                )

                self.db.add(operation)
                inserted += 1

            # ---------- финализация batch ----------

            batch.inserted_count = inserted
            batch.duplicate_count = duplicates
            batch.status = "success"

            account.last_synced_at = now

        self.db.commit()