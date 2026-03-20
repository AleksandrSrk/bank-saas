from app.integrations.banks.tochka.adapter import TochkaAdapter
from app.integrations.banks.sber.adapter import SberAdapter




class BankAdapterFactory:

    @staticmethod
    def get_adapter(db, bank_name: str):
        if bank_name == "tochka":
            return TochkaAdapter(db)

        if bank_name == "sber":
            return SberAdapter(db)

        raise ValueError(f"Unsupported bank: {bank_name}")