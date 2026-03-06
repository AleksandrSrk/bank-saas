from datetime import datetime
from decimal import Decimal
from typing import Generator

from app.domain.dto import OperationImportDTO


def parse_1c_client_bank(file_path: str) -> Generator[OperationImportDTO, None, None]:

    current_doc = {}

    with open(file_path, "r", encoding="cp1251") as f:

        for line in f:

            line = line.strip()

            if line.startswith("СекцияДокумент"):
                current_doc = {}
                continue

            if line == "КонецДокумента":

                dto = _build_dto(current_doc)

                if dto:
                    yield dto

                continue

            if "=" in line:

                key, value = line.split("=", 1)

                current_doc[key] = value


def _build_dto(data: dict) -> OperationImportDTO | None:

    document_number = data.get("Номер")
    document_date = _parse_date(data.get("Дата"))

    amount = Decimal(data.get("Сумма", "0"))

    date_debit = _parse_date(data.get("ДатаСписано"))
    date_credit = _parse_date(data.get("ДатаПоступило"))

    payer_account = data.get("ПлательщикСчет")
    receiver_account = data.get("ПолучательСчет")

    payer_inn = data.get("ПлательщикИНН")
    receiver_inn = data.get("ПолучательИНН")

    payer_name = data.get("Плательщик1")
    receiver_name = data.get("Получатель1")

    description = data.get("НазначениеПлатежа")

    if date_credit:
        return OperationImportDTO(
            document_number=document_number,
            document_type="bank_payment",
            operation_date=date_credit,
            document_date=document_date,
            debit_amount=None,
            credit_amount=amount,
            account_number=receiver_account,
            counterparty_account=payer_account,
            counterparty_inn=payer_inn,
            counterparty_name=payer_name,
            description=description,
        )

    if date_debit:
        return OperationImportDTO(
            document_number=document_number,
            document_type="bank_payment",
            operation_date=date_debit,
            document_date=document_date,
            debit_amount=amount,
            credit_amount=None,
            account_number=payer_account,
            counterparty_account=receiver_account,
            counterparty_inn=receiver_inn,
            counterparty_name=receiver_name,
            description=description,
        )

    return None


def _parse_date(date_str: str | None):

    if not date_str:
        return None

    try:
        return datetime.strptime(date_str, "%d.%m.%Y")
    except:
        return None