from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models.bank_connection import BankConnection
from app.models.bank_account import BankAccount

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

        # 4. определяем период синхронизации
        now = datetime.utcnow()

        if connection.last_synced_at:
            from_date = connection.last_synced_at - timedelta(minutes=5)
        else:
            from_date = now - timedelta(days=30)

        to_date = now

        # 5. получаем список счетов
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

        # ---- сохраняем счета в БД ----
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

        # ---- получаем операции ----
        all_operations = []

        for account in accounts:

            account_id = account.get("accountId")

            if not account_id:
                continue

            try:
                statements = client.get_statements(
                    account_id=account_id,
                    from_date=from_date,
                    to_date=to_date
                )
            except Exception:
                continue

            statement_list = statements.get("Data", {}).get("Statement", [])

            for statement in statement_list:
                transactions = statement.get("Transaction", [])
                all_operations.extend(transactions)

        # ---- конвертируем операции в DTO ----
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

            # счет контрагента
            if op.get("CreditorAccount"):
                counterparty_account = op["CreditorAccount"].get("identification")

            if op.get("DebtorAccount"):
                counterparty_account = op["DebtorAccount"].get("identification")

            # данные контрагента
            if op.get("CreditorParty"):
                counterparty_inn = op["CreditorParty"].get("inn")
                counterparty_name = op["CreditorParty"].get("name")

            if op.get("DebtorParty"):
                counterparty_inn = op["DebtorParty"].get("inn")
                counterparty_name = op["DebtorParty"].get("name")

            # дата операции
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

            account_number = account_id

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

        # ---- импорт операций ----

        
        service = ImportService(db)

        batch = service.import_operations(
            dtos=dtos,
            company_id=company_id,
            filename="tochka_api"
        )

        # 9. обновляем время синхронизации
        connection.last_synced_at = datetime.utcnow()
        db.commit()

        return {
            "status": "success",
            "accounts_processed": len(accounts),
            "operations_received": len(all_operations),
            "imported": batch.inserted_count,
            "duplicates": batch.duplicate_count
        }