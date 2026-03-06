from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.integrations.tochka import client
from app.models.bank_connection import BankConnection
from app.integrations.tochka.client import TochkaClient
from app.services.import_service import ImportService
from app.domain.dto import OperationImportDTO


class TochkaSyncService:

    @staticmethod
    def sync_company(db: Session, company_id):

        # 1 получаем подключение банка
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

        # 2 создаем клиента банка
        # client = TochkaClient(connection.access_token)
        client = TochkaClient(
            access_token=connection.access_token,
            consent_id=connection.consent_id
        )

        # 3 получаем операции

        from datetime import datetime, timedelta

        to_date = datetime.utcnow().date()
        from_date = to_date - timedelta(days=30)

        # сначала получаем счета
        # accounts = client.get_accounts()
        try:
            accounts = client.get_accounts()
            print("TOCHKA ACCOUNTS:", accounts)
        except Exception as e:
            return {
                "status": "bank_api_error",
                "message": str(e)
            }

        if not accounts:
            return {"error": "no accounts found"}

        account_id = accounts["Data"]["Account"][0]["AccountId"]

        statements = client.get_statements(
            account_id=account_id,
            from_date=from_date,
            to_date=to_date
        )

        # 4 конвертируем в DTO
        dtos = []

        operations = statements["Data"]["Statement"]

        for op in operations:

            dto = OperationImportDTO(
                document_number=op.get("documentNumber"),
                document_type="bank_payment",
                operation_date=op.get("operationDate"),
                document_date=op.get("documentDate"),
                debit_amount=op.get("debitAmount"),
                credit_amount=op.get("creditAmount"),
                account_number=op.get("accountNumber"),
                counterparty_account=op.get("counterpartyAccount"),
                counterparty_inn=op.get("counterpartyInn"),
                counterparty_name=op.get("counterpartyName"),
                description=op.get("description")
            )

            dtos.append(dto)

        # 5 отправляем в ImportService
        batch = ImportService.import_operations(
            dtos=dtos,
            company_id=company_id,
            filename="tochka_api"
        )

        return {
            "status": "success",
            "imported": batch.inserted_count,
            "duplicates": batch.duplicate_count
        }