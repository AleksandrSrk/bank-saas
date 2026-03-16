from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models.bank_connection import BankConnection


class BankConnectionService:

    @staticmethod
    def create_connection(
        db: Session,
        company_id,
        bank_name,
        access_token,
        refresh_token=None,
        expires_in=None
    ):

        expires_at = None

        if expires_in:
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        connection = BankConnection(
            company_id=company_id,
            bank_name=bank_name,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at
        )

        db.add(connection)
        db.commit()
        db.refresh(connection)

        return connection
    
    @staticmethod
    def get_connection(db: Session, bank_name: str):
        return (
                db.query(BankConnection)
                .filter(BankConnection.bank_name == bank_name)
                .first()
            )

            