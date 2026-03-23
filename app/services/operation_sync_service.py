from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.bank_operation import BankOperation
from app.models.operation_batch import OperationBatch
from app.models.legal_entity import LegalEntity
from app.models.company import Company
from app.models.bank_connection import BankConnection
from app.models.bank_account import BankAccount

from app.integrations.banks.adapter_factory import BankAdapterFactory

import os
import json
from pathlib import Path


# =========================================================
# ЛОГИРОВАНИЕ
# =========================================================

def write_sync_log(data: dict):
    """
    Пишет лог синка в файл.
    Хранит максимум 5 файлов (ротация).
    """

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    files = sorted(log_dir.glob("sync_*.json"))

    # удаляем самый старый файл
    if len(files) >= 5:
        files[0].unlink()

    filename = log_dir / f"sync_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

    with open(filename, "w") as f:
        json.dump(data, f, indent=2, default=str)


# =========================================================
# ОСНОВНОЙ СЕРВИС СИНКА
# =========================================================

class OperationSyncService:

    def __init__(self, db: Session):
        self.db = db

    def sync_operations(self):
        """
        Основной процесс синка:
        1. Берем все подключения банков
        2. По каждому — получаем счета
        3. По каждому счету — тянем операции
        4. Сохраняем в БД
        """

        connections = self.db.query(BankConnection).all()

        for connection in connections:

            # получаем адаптер конкретного банка
            adapter = BankAdapterFactory.get_adapter(
                self.db,
                connection.bank_name
            )

            now = datetime.utcnow()

            # =========================================
            # ПОЛУЧАЕМ СЧЕТА
            # =========================================

            db_accounts = (
                self.db.query(BankAccount)
                .filter(BankAccount.bank_connection_id == connection.id)
                .all()
            )

            # fallback для Sber (если счетов нет)
            if not db_accounts and connection.bank_name == "sber":

                bootstrap_account = os.getenv("SBER_BOOTSTRAP_ACCOUNT")

                if not bootstrap_account:
                    print("❌ SBER_BOOTSTRAP_ACCOUNT not set")
                    continue

                print(f"⚡ Bootstrap Sber account: {bootstrap_account}")

                db_accounts = [
                    type("AccountObj", (), {"account_number": bootstrap_account})()
                ]

            # =========================================
            # ПРОХОД ПО СЧЕТАМ
            # =========================================

            for account in db_accounts:

                # определяем период синка
                if hasattr(account, "last_synced_at") and account.last_synced_at:
                    start_date = account.last_synced_at - timedelta(days=1)
                else:
                    start_date = now - timedelta(days=90)

                end_date = now
                account_number = account.account_number

                # =========================================
                # ПОЛУЧЕНИЕ ОПЕРАЦИЙ
                # =========================================

                try:
                    operations = adapter.get_operations(
                        account_number,
                        start_date,
                        end_date
                    )
                except Exception as e:
                    print(f"❌ ERROR [{connection.bank_name}] {account_number}: {e}")

                    write_sync_log({
                        "bank": connection.bank_name,
                        "account": account_number,
                        "error": str(e),
                        "stage": "get_operations",
                        "timestamp": datetime.utcnow().isoformat()
                    })

                    continue

                print(
                    f"[{connection.bank_name}] {account_number}: {len(operations)} ops"
                )

                if not operations:
                    write_sync_log({
                        "bank": connection.bank_name,
                        "account": account_number,
                        "warning": "no operations returned",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    continue

                # =========================================
                # СОЗДАЕМ БАТЧ
                # =========================================

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

                # =========================================
                # ОБРАБОТКА ОПЕРАЦИЙ
                # =========================================

                for op in operations:
                    try:

                        if op.amount is None or op.direction not in ("incoming", "outgoing"):
                            continue

                        # проверка дублей
                        existing = self.db.query(BankOperation).filter_by(
                            company_id=connection.company_id,
                            document_number=op.document_number
                        ).first()

                        if existing:
                            duplicates += 1
                            continue

                        # -------------------------------------
                        # НАШЕ ЮРЛИЦО
                        # -------------------------------------

                        company = self.db.query(Company).filter(
                            Company.id == connection.company_id
                        ).first()

                        legal_entity = None

                        if company and company.inn:
                            legal_entity = self.db.query(LegalEntity).filter(
                                LegalEntity.inn == company.inn
                            ).first()

                        legal_entity_id = legal_entity.id if legal_entity else None

                        # -------------------------------------
                        # КОНТРАГЕНТ
                        # -------------------------------------

                        counterparty_id = None

                        if op.counterparty_inn:
                            counterparty = (
                                self.db.query(Company)
                                .filter(Company.inn == op.counterparty_inn)
                                .first()
                            )

                            if not counterparty:
                                counterparty = Company(
                                    name=op.counterparty_name,
                                    inn=op.counterparty_inn
                                )
                                self.db.add(counterparty)
                                self.db.flush()

                            counterparty_id = counterparty.id

                        # -------------------------------------
                        # ПРОВЕРКА СЧЕТА
                        # -------------------------------------

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

                        # -------------------------------------
                        # INTERNAL ОПЕРАЦИИ
                        # -------------------------------------

                        our_entity = None

                        if op.counterparty_inn:
                            our_entity = self.db.query(LegalEntity).filter(
                                LegalEntity.inn == op.counterparty_inn
                            ).first()

                        # -------------------------------------
                        # СОЗДАНИЕ ОПЕРАЦИИ
                        # -------------------------------------

                        operation = BankOperation(
                            counterparty_id=counterparty_id,
                            bank_connection_id=connection.id,

                            company_id=connection.company_id,
                            legal_entity_id=legal_entity_id,

                            import_batch_id=batch.id,

                            document_number=op.document_number,
                            document_type="bank_payment",

                            amount=op.amount,
                            direction=op.direction,

                            operation_date=op.operation_date,
                            document_date=op.operation_date.date(),

                            account_number=op.account_number,
                            bank_account_id=db_account.id,

                            counterparty_account=op.counterparty_account,
                            counterparty_inn=op.counterparty_inn,
                            counterparty_name=op.counterparty_name,

                            is_internal=our_entity is not None,
                            counterparty_legal_entity_id=(
                                our_entity.id if our_entity else None
                            ),

                            description=op.description
                        )

                        self.db.add(operation)
                        inserted += 1

                    except Exception as e:
                        print(f"❌ OP ERROR: {e}")

                        write_sync_log({
                            "bank": connection.bank_name,
                            "account": account_number,
                            "error": str(e),
                            "stage": "process_operation",
                            "raw_op": str(op),
                            "timestamp": datetime.utcnow().isoformat()
                        })

                        continue

                # =========================================
                # ФИНАЛИЗАЦИЯ БАТЧА
                # =========================================

                batch.inserted_count = inserted
                batch.duplicate_count = duplicates
                batch.status = "success"

                # лог результата
                write_sync_log({
                    "bank": connection.bank_name,
                    "account": account_number,
                    "company_id": str(connection.company_id),
                    "total_received": len(operations),
                    "inserted": inserted,
                    "duplicates": duplicates,
                    "timestamp": datetime.utcnow().isoformat()
                })

                # обновляем дату синка
                if hasattr(account, "last_synced_at"):
                    account.last_synced_at = now
                    self.db.add(account)

        self.db.commit()