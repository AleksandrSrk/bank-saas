from abc import ABC, abstractmethod
from typing import List
from app.domain.dto import OperationImportDTO


class BankAdapter(ABC):

    @abstractmethod
    def get_accounts(self) -> list:
        pass

    @abstractmethod
    def get_operations(
        self,
        account,
        date_from,
        date_to
    ) -> List[OperationImportDTO]:
        pass