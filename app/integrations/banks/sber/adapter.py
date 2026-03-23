from datetime import datetime, timedelta
from decimal import Decimal
from typing import List
import os

from app.integrations.banks.base.bank_adapter import BankAdapter
from app.domain.dto import OperationImportDTO
from app.integrations.banks.sber.client import SberClient


class SberAdapter(BankAdapter):

    def __init__(self, db):
        self.db = db
        self.client = SberClient()

    # 🔥 bootstrap счет (пока Sber API не даёт список счетов)
    def get_accounts(self):
        account = os.getenv("SBER_BOOTSTRAP_ACCOUNT")

        if not account:
            print("❌ SBER_BOOTSTRAP_ACCOUNT not set")
            return []

        return [
            {
                "account_number": account,
                "currency": "RUB"
            }
        ]

    def _parse_date(self, raw: str) -> datetime:
        if not raw:
            raise ValueError("Empty date")

        raw = raw.replace("T", "")

        if raw.count("-") > 2:
            parts = raw.split("-")
            raw = "-".join(parts[:3]) + parts[3]

        try:
            return datetime.strptime(raw, "%Y-%m-%d%H:%M:%S")
        except ValueError:
            return datetime.strptime(raw[:10], "%Y-%m-%d")

    def get_operations(self, account_number, start_date, end_date) -> List[OperationImportDTO]:

        all_transactions = []

        current_date = start_date.date()
        end_date_only = end_date.date()

        while current_date <= end_date_only:

            date_str = current_date.strftime("%Y-%m-%d")
            page = 1

            while True:
                data = self.client.get_operations(
                    account_number,
                    date_str,
                    page=page
                )

                transactions = data.get("transactions", [])

                if not transactions:
                    break

                all_transactions.extend(transactions)

                if len(transactions) < 100:
                    break

                page += 1

            current_date += timedelta(days=1)

        result = []

        for tx in all_transactions:

            raw_amount = tx.get("amount", {}).get("amount")
            if not raw_amount:
                continue

            amount = Decimal(str(raw_amount))

            direction = (
                "incoming"
                if tx.get("direction") == "CREDIT"
                else "outgoing"
            )

            operation_date = self._parse_date(tx.get("operationDate"))

            rur = tx.get("rurTransfer", {})

            if tx.get("direction") == "CREDIT":
                op_account = rur.get("payeeAccount")
                counterparty_account = rur.get("payerAccount")
                counterparty_inn = rur.get("payerInn")
                counterparty_name = rur.get("payerName")
            else:
                op_account = rur.get("payerAccount")
                counterparty_account = rur.get("payeeAccount")
                counterparty_inn = rur.get("payeeInn")
                counterparty_name = rur.get("payeeName")

            dto = OperationImportDTO(
                document_number=tx.get("operationId"),
                document_type="bank_payment",

                operation_date=operation_date,
                document_date=datetime.strptime(
                    tx.get("documentDate"),
                    "%Y-%m-%d"
                ).date(),

                amount=amount,
                direction=direction,

                account_number=op_account,
                counterparty_account=counterparty_account,
                counterparty_inn=counterparty_inn,
                counterparty_name=counterparty_name,

                description=tx.get("paymentPurpose"),
            )

            result.append(dto)

        return result