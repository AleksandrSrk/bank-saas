from datetime import datetime
from typing import List
from decimal import Decimal

from app.integrations.banks.base.bank_adapter import BankAdapter
from app.integrations.banks.tochka.client import TochkaClient
from app.domain.dto import OperationImportDTO


class TochkaAdapter(BankAdapter):

    def __init__(self, db):
        self.client = TochkaClient(db)

    def get_accounts(self):
        data = self.client.get_accounts()

        accounts = data.get("Data", {}).get("Account", [])

        result = []

        for acc in accounts:
            account_id = acc.get("accountId")

            if not account_id:
                continue

            account_number = account_id.split("/")[0]

            result.append({
                "account_number": account_number,
                "currency": acc.get("currency")
            })

        return result

    def get_operations(self, account_number, start_date, end_date) -> List[OperationImportDTO]:

        statement_id = self.client.create_statement(
            account_number,
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        )

        transactions = self.client.get_transactions(statement_id)

        result = []

        for tx in transactions:

            raw_amount = tx.get("Amount", {}).get("amount")

            if not raw_amount:
                continue

            amount = Decimal(str(raw_amount))

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

            if direction == "incoming":
                counterparty_account = tx.get("DebtorAccount", {}).get("identification")
                counterparty_inn = tx.get("DebtorParty", {}).get("inn")
                counterparty_name = tx.get("DebtorParty", {}).get("name")
            else:
                counterparty_account = tx.get("CreditorAccount", {}).get("identification")
                counterparty_inn = tx.get("CreditorParty", {}).get("inn")
                counterparty_name = tx.get("CreditorParty", {}).get("name")

            dto = OperationImportDTO(
                document_number=tx.get("transactionId"),
                document_type="bank_payment",

                operation_date=operation_date,
                document_date=operation_date.date(),

                amount=amount,
                direction=direction,

                account_number=account_number,
                counterparty_account=counterparty_account,
                counterparty_inn=counterparty_inn,
                counterparty_name=counterparty_name,

                description=tx.get("description"),
            )

            result.append(dto)

        return result