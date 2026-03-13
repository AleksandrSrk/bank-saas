from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import time

from sqlalchemy import func

from app.models.bank_connection import BankConnection
from app.models.bank_account import BankAccount
from app.models.bank_operation import BankOperation

from app.integrations.tochka.client import TochkaClient
from app.services.import_service import ImportService
from app.domain.dto import OperationImportDTO
from app.services.bank_token_service import BankTokenService


class TochkaSyncService:

    @staticmethod
    def sync_company(db: Session, company_id):

        # 1. получаем подключение банка
        connection = (
            db.query(BankConnection)
            .filter(
                BankConnection.company_id == company_id,
                BankConnection.bank_name == "tochka"
            )
            .first()
        )

        if not connection:
            return {"error": "tochka connection not found"}

        # 2. проверяем и обновляем токен
        token = BankTokenService.ensure_valid_token(db, connection)

        # 3. создаем клиента банка
        client = TochkaClient(
            access_token=token,
            consent_id=connection.consent_id
        )

        now = datetime.utcnow()

        # 4. определяем дату последней операции
        last_operation = (
            db.query(func.max(BankOperation.operation_date))
            .filter(BankOperation.company_id == company_id)
            .scalar()
        )

        if last_operation:
            from_date = last_operation - timedelta(days=3)
        else:
            from_date = now - timedelta(days=90)

        to_date = now

        # 5. получаем счета из банка
        try:
            accounts_response = client.get_accounts()
        except Exception as e:
            return {
                "status": "bank_api_error",
                "message": str(e)
            }

        accounts = accounts_response.get("Data", {}).get("Account", [])

        if not accounts:
            return {"error": "no accounts found"}

        # 6. сохраняем счета в БД
        for account in accounts:

            account_id = account.get("accountId")

            if not account_id:
                continue

            account_number = account_id.split("/")[0]

            existing_account = (
                db.query(BankAccount)
                .filter(
                    BankAccount.account_number == account_number,
                    BankAccount.company_id == company_id
                )
                .first()
            )

            if not existing_account:

                new_account = BankAccount(
                    company_id=company_id,
                    bank_connection_id=connection.id,
                    account_number=account_number,
                    currency=account.get("currency")
                )

                db.add(new_account)

        db.commit()

        all_operations = []

        # 7. получаем операции по каждому счету
        for account in accounts:

            account_id = account.get("accountId")

            if not account_id:
                continue

            try:

                # создаем выписку
                statement = client.create_statement(
                    account_id=account_id,
                    from_date=from_date,
                    to_date=to_date
                )

                statement_id = statement["Data"]["Statement"]["statementId"]

                # ждем пока банк сформирует выписку
                time.sleep(2)

                # получаем готовую выписку
                statement_data = client.get_statement(
                    account_id=account_id,
                    statement_id=statement_id
                )

            except Exception as e:
                print("STATEMENT ERROR:", e)
                continue

            statement_list = statement_data.get("Data", {}).get("Statement", [])

            for statement in statement_list:

                account_id = statement.get("accountId")

                transactions = statement.get("Transaction", [])

                for tx in transactions:
                    tx["accountId"] = account_id
                    all_operations.append(tx)

        # 8. конвертируем операции в DTO
        dtos = []

        for op in all_operations:

            amount = op.get("Amount", {}).get("amount")

            if not amount:
                continue

            debit = None
            credit = None

            if op.get("creditDebitIndicator") == "Debit":
                debit = amount
            else:
                credit = amount

            counterparty_account = None
            counterparty_inn = None
            counterparty_name = None

            if op.get("CreditorAccount"):
                counterparty_account = op["CreditorAccount"].get("identification")

            if op.get("DebtorAccount"):
                counterparty_account = op["DebtorAccount"].get("identification")

            if op.get("CreditorParty"):
                counterparty_inn = op["CreditorParty"].get("inn")
                counterparty_name = op["CreditorParty"].get("name")

            if op.get("DebtorParty"):
                counterparty_inn = op["DebtorParty"].get("inn")
                counterparty_name = op["DebtorParty"].get("name")

            operation_date_raw = op.get("documentProcessDate")

            if not operation_date_raw:
                continue

            try:
                operation_date = datetime.strptime(
                    operation_date_raw,
                    "%Y-%m-%d"
                )
            except Exception:
                continue

            account_id = op.get("accountId")
            account_number = account_id.split("/")[0] if account_id else None

            dto = OperationImportDTO(
                document_number=op.get("transactionId"),
                document_type="bank_payment",
                operation_date=operation_date,
                document_date=operation_date,
                debit_amount=debit,
                credit_amount=credit,
                account_number=account_number,
                counterparty_account=counterparty_account,
                counterparty_inn=counterparty_inn,
                counterparty_name=counterparty_name,
                description=op.get("description")
            )

            dtos.append(dto)

        # 9. импортируем операции
        service = ImportService(db)

        batch = service.import_operations(
            dtos=dtos,
            company_id=company_id,
            filename="tochka_api"
        )

        return {
            "status": "success",
            "accounts_processed": len(accounts),
            "operations_received": len(all_operations),
            "imported": batch.inserted_count,
            "duplicates": batch.duplicate_count
        }