from datetime import timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.bank_operation import BankOperation
from app.models.user_company import UserCompany


class BankOperationRepository:

    def get_operations_for_period(
        self,
        db: Session,
        manager_id,
        inn: str,
        days: int,
        details: bool = False
    ):

        # ------------------------------------------------
        # получаем доступные юрлица менеджера
        # ------------------------------------------------

        user_entities = (
            db.query(UserCompany.legal_entity_id)
            .filter(
                UserCompany.user_id == manager_id,
                UserCompany.legal_entity_id != None
            )
            .all()
        )

        entity_ids = [e[0] for e in user_entities]

        if not entity_ids:
            return None

        # ------------------------------------------------
        # определяем последнюю операцию по этим юрлицам
        # ------------------------------------------------

        last_operation = (
            db.query(func.max(BankOperation.operation_date))
            .filter(
                BankOperation.legal_entity_id.in_(entity_ids),
                BankOperation.counterparty_inn == inn,
                BankOperation.is_internal == False
            )
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
                BankOperation.counterparty_inn == inn,
                BankOperation.legal_entity_id.in_(entity_ids),
                BankOperation.is_internal == False,
                BankOperation.operation_date >= date_from
            )
            .order_by(BankOperation.operation_date.desc())
            .all()
        )

        if not operations:
            return None

        # ------------------------------------------------
        # агрегаты
        # ------------------------------------------------

        total_in = (
            db.query(func.coalesce(func.sum(BankOperation.amount), 0))
            .filter(
                BankOperation.counterparty_inn == inn,
                BankOperation.legal_entity_id.in_(entity_ids),
                BankOperation.is_internal == False,
                BankOperation.operation_date >= date_from,
                BankOperation.direction == "incoming"
            )
            .scalar()
        )

        total_out = (
            db.query(func.coalesce(func.sum(BankOperation.amount), 0))
            .filter(
                BankOperation.counterparty_inn == inn,
                BankOperation.legal_entity_id.in_(entity_ids),
                BankOperation.is_internal == False,
                BankOperation.operation_date >= date_from,
                BankOperation.direction == "outgoing"
            )
            .scalar()
        )

        # ------------------------------------------------
        # название контрагента
        # ------------------------------------------------

        company_name = None

        op = (
            db.query(BankOperation.counterparty_name)
            .filter(
                BankOperation.counterparty_inn == inn,
                BankOperation.counterparty_name != None
            )
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

            if details:
                result.append({
                    "date": op.operation_date.strftime("%Y-%m-%d"),
                    "amount": float(op.amount),
                    "direction": op.direction,
                    "counterparty": op.counterparty_name,
                    "description": op.description
                })
            else:
                result.append({
                    "date": op.operation_date.strftime("%Y-%m-%d"),
                    "amount": float(op.amount),
                    "direction": op.direction
                })

        # ------------------------------------------------
        # ответ
        # ------------------------------------------------

        return {
            "company_name": company_name,
            "inn": inn,
            "total_in": float(total_in),
            "total_out": float(total_out),
            "operations": result
        }