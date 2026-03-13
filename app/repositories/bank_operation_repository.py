from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.bank_operation import BankOperation
from app.models.company import Company
from app.models.tracked_company import TrackedCompany


class BankOperationRepository:

    def get_operations_for_period(
        self,
        db: Session,
        manager_id,
        inn: str,
        days: int
    ):

        company = (
            db.query(Company)
            .filter(Company.inn == inn)
            .first()
        )

        if not company:
            return None

        access = (
            db.query(TrackedCompany)
            .filter(
                TrackedCompany.manager_id == manager_id,
                TrackedCompany.company_id == company.id,
                TrackedCompany.active == True
            )
            .first()
        )

        if not access:
            return None

        # ------------------------------------------------
        # определяем дату последней операции
        # ------------------------------------------------

        last_operation = (
            db.query(func.max(BankOperation.operation_date))
            .filter(BankOperation.company_id == company.id)
            .scalar()
        )

        if not last_operation:
            return None

        date_from = last_operation - timedelta(days=days)

        # ------------------------------------------------
        # операции
        # ------------------------------------------------

        operations = (
            db.query(BankOperation)
            .filter(
                BankOperation.company_id == company.id,
                BankOperation.operation_date >= date_from
            )
            .order_by(BankOperation.operation_date.desc())
            .all()
        )

        # ------------------------------------------------
        # агрегаты
        # ------------------------------------------------

        total_in = (
            db.query(func.coalesce(func.sum(BankOperation.amount), 0))
            .filter(
                BankOperation.company_id == company.id,
                BankOperation.operation_date >= date_from,
                BankOperation.direction == "incoming"
            )
            .scalar()
        )

        total_out = (
            db.query(func.coalesce(func.sum(BankOperation.amount), 0))
            .filter(
                BankOperation.company_id == company.id,
                BankOperation.operation_date >= date_from,
                BankOperation.direction == "outgoing"
            )
            .scalar()
        )

        # ------------------------------------------------
        # название компании
        # ------------------------------------------------

        company_name = company.name

        if not company_name:

            op = (
                db.query(BankOperation.counterparty_name)
                .filter(BankOperation.company_id == company.id)
                .filter(BankOperation.counterparty_name != None)
                .first()
            )

            if op:
                company_name = op[0]
            else:
                company_name = "Компания"

        # ------------------------------------------------
        # список операций
        # ------------------------------------------------

        result = []

        for op in operations:

            result.append({
                "date": op.operation_date.strftime("%Y-%m-%d"),
                "amount": float(op.amount),
                "direction": op.direction,
                "counterparty": op.counterparty_name,
                "description": op.description
            })

        return {
            "company_name": company_name,
            "inn": inn,
            "total_in": float(total_in),
            "total_out": float(total_out),
            "operations": result
        }