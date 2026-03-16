from sqlalchemy.orm import Session
from datetime import datetime

from app.integrations.banks.tochka.client import TochkaClient

from app.models.bank_account import BankAccount
from app.models.bank_operation import BankOperation
from app.models.company import Company


class TochkaSyncService:

    @staticmethod
    def sync_company(db: Session, company_id):

        client = TochkaClient(db)

        company = db.query(Company).filter(
            Company.id == company_id
        ).first()

        if not company:
            return {"status": "company_not_found"}

        accounts = client.get_accounts()

        total_operations = 0

        for account in accounts:

            account_number = account["account_number"]

            db_account = db.query(BankAccount).filter(
                BankAccount.account_number == account_number
            ).first()

            if not db_account:
                continue

            operations = client.get_operations(account_number)

            for op in operations:

                existing = db.query(BankOperation).filter(
                    BankOperation.external_id == op["id"]
                ).first()

                if existing:
                    continue

                operation = BankOperation(
                    bank_account_id=db_account.id,
                    external_id=op["id"],
                    amount=op["amount"],
                    direction=op["direction"],
                    counterparty_name=op["counterparty_name"],
                    counterparty_inn=op["counterparty_inn"],
                    operation_date=op["date"],
                    created_at=datetime.utcnow()
                )

                db.add(operation)

                total_operations += 1

        if total_operations > 0 and company.status != "in_work":
            company.status = "in_work"

        if total_operations > 0:

            company = db.query(Company).filter(
                Company.id == company_id
            ).first()

            if company.status != "in_work":
                company.status = "in_work"

                db.commit()

        return {
            "status": "success",
            "operations_loaded": total_operations
        }