from datetime import timedelta, datetime
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
        # получаем название компании
        # ------------------------------------------------

        company_name_row = (
            db.query(BankOperation.counterparty_name)
            .filter(
                BankOperation.counterparty_inn == inn,
                BankOperation.counterparty_name != None
            )
            .first()
        )

        company_name = company_name_row[0] if company_name_row else "Компания"

        # ------------------------------------------------
        # есть ли вообще операции по этой компании
        # ------------------------------------------------

        has_any_operations = (
            db.query(BankOperation.id)
            .filter(
                BankOperation.counterparty_inn == inn,
                BankOperation.is_internal == False
            )
            .first()
        )

        # ❗ НОВАЯ / "подвешенная" компания
        if not has_any_operations:
            return {
                "company_name": company_name,
                "inn": inn,
                "total_in": 0,
                "total_out": 0,
                "operations": []
            }

        # ------------------------------------------------
        # доступные юрлица менеджера
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

        # ❗ вообще нет доступа к юрлицам
        if not entity_ids:
            if not has_any_operations:
                return {
                    "company_name": company_name,
                    "inn": inn,
                    "total_in": 0,
                    "total_out": 0,
                    "operations": []
                }

            return {"error": "access_denied"}

        # ------------------------------------------------
        # есть ли операции в ДОСТУПНЫХ юрлицах
        # ------------------------------------------------

        has_accessible_operations = (
            db.query(BankOperation.id)
            .filter(
                BankOperation.counterparty_inn == inn,
                BankOperation.legal_entity_id.in_(entity_ids),
                BankOperation.is_internal == False
            )
            .first()
        )

        # ❗ операции есть, но не в твоих юрлицах → доступ запрещён
        if not has_accessible_operations:
            return {"error": "access_denied"}

        # ------------------------------------------------
        # период
        # ------------------------------------------------

        date_from = datetime.utcnow() - timedelta(days=days)

        # ------------------------------------------------
        # операции за период
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

        # ------------------------------------------------
        # если в периоде нет операций
        # ------------------------------------------------

        if not operations:
            return {
                "company_name": company_name,
                "inn": inn,
                "total_in": 0,
                "total_out": 0,
                "operations": []
            }

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
        # формирование ответа
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

        return {
            "company_name": company_name,
            "inn": inn,
            "total_in": float(total_in),
            "total_out": float(total_out),
            "operations": result
        }