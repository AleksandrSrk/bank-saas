from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.bank_operation import BankOperation
from app.models.operation_batch import OperationBatch
from app.models.legal_entity import LegalEntity
from app.models.company import Company
from app.models.bank_connection import BankConnection

from app.integrations.banks.adapter_factory import BankAdapterFactory
from app.models.bank_account import BankAccount

import os


class OperationSyncService:

    def __init__(self, db: Session):
        self.db = db

    def sync_operations(self):

        connections = self.db.query(BankConnection).all()

        for connection in connections:

            adapter = BankAdapterFactory.get_adapter(
                self.db,
                connection.bank_name
            )

            now = datetime.utcnow()

         
            # --- берем счета из БД ---
            db_accounts = (
                self.db.query(BankAccount)
                .filter(BankAccount.bank_connection_id == connection.id)
                .all()
            )

            # если счетов нет — используем стартовый (только для Sber)
        

            if not db_accounts and connection.bank_name == "sber":
                bootstrap_account = os.getenv("SBER_BOOTSTRAP_ACCOUNT")

                if not bootstrap_account:
                    print("❌ SBER_BOOTSTRAP_ACCOUNT not set")
                    continue

                print(f"⚡ Bootstrap Sber account: {bootstrap_account}")

                db_accounts = []

                db_accounts.append(
                    type("AccountObj", (), {"account_number": bootstrap_account})()
                )

            for account in db_accounts:
                if hasattr(account, "last_synced_at") and account.last_synced_at:
                    start_date = account.last_synced_at - timedelta(days=1)
                else:
                    start_date = now - timedelta(days=5)

                end_date = now

                account_number = account.account_number

                operations = adapter.get_operations(
                    account_number,
                    start_date,
                    end_date
                )

                print(
                    f"[{connection.bank_name}] {account.account_number}: {len(operations)} ops"
                )

                if not operations:
                    continue

                batch = OperationBatch(
                    company_id=connection.company_id,
                    source_type="bank_api",
                    total_count=len(operations),
                    status="processing"
                )

                self.db.add(batch)
                self.db.flush()

                inserted = 0
                duplicates = 0

                for op in operations:

                    amount = op.amount
                    direction = op.direction

                    if amount is None or direction not in ("incoming", "outgoing"):
                        continue

                    operation_date = op.operation_date
                    document_number = op.document_number

                    counterparty_account = op.counterparty_account
                    counterparty_inn = op.counterparty_inn
                    counterparty_name = op.counterparty_name

                    our_entity = None

                    if counterparty_inn:
                        our_entity = self.db.query(LegalEntity).filter(
                            LegalEntity.inn == counterparty_inn
                        ).first()

                    existing = self.db.query(BankOperation).filter_by(
                        company_id=connection.company_id,
                        document_number=document_number
                    ).first()

                    if existing:
                        duplicates += 1
                        continue

                    counterparty_id = None

                    if counterparty_inn:
                        company = (
                            self.db.query(Company)
                            .filter(Company.inn == counterparty_inn)
                            .first()
                        )

                        if not company:
                            company = Company(
                                name=counterparty_name,
                                inn=counterparty_inn
                            )
                            self.db.add(company)
                            self.db.flush()

                        counterparty_id = company.id
                    
                    db_account = (
                        self.db.query(BankAccount)
                        .filter(
                            BankAccount.account_number == op.account_number,
                            BankAccount.bank_connection_id == connection.id
                        )
                        .first()
                    )

                    if not db_account:
                        db_account = BankAccount(
                            company_id=connection.company_id,
                            bank_connection_id=connection.id,
                            account_number=op.account_number,
                            currency=None
                        )
                        self.db.add(db_account)
                        self.db.flush()

                    operation = BankOperation(
                        counterparty_id=counterparty_id,
                        bank_connection_id=connection.id,

                        company_id=connection.company_id,
                        legal_entity_id=None,
                        import_batch_id=batch.id,

                        document_number=document_number,
                        document_type="bank_payment",

                        amount=amount,
                        direction=direction,

                        operation_date=operation_date,
                        document_date=operation_date.date(),

                        account_number=op.account_number,
                        bank_account_id=db_account.id,

                        counterparty_account=counterparty_account,
                        counterparty_inn=counterparty_inn,
                        counterparty_name=counterparty_name,

                        is_internal=our_entity is not None,
                        counterparty_legal_entity_id=(
                            our_entity.id if our_entity else None
                        ),

                        description=op.description
                    )

                    self.db.add(operation)
                    inserted += 1

                batch.inserted_count = inserted
                batch.duplicate_count = duplicates
                batch.status = "success"
                
                
                # обновляем время синка
                if hasattr(account, "last_synced_at"):
                    account.last_synced_at = now
                    self.db.add(account)

        self.db.commit()