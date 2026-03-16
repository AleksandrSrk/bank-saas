import time
import requests

from app.config.settings import settings
from app.services.bank_connection_service import BankConnectionService
from app.services.bank_token_service import BankTokenService
from app.integrations.banks.tochka.config import TOCHKA_BIC


class TochkaClient:

    def __init__(self, db):

        self.db = db
        self.rs_url = settings.TOCHKA_API_URL

        connection = BankConnectionService.get_connection(db, "tochka")

        if not connection:
            raise Exception("Tochka connection not found")

        self.connection = connection

        self.access_token = BankTokenService.ensure_valid_token(
            db,
            connection
        )

    def _headers(self):

        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-consent-id": self.connection.consent_id
        }

    def _request(self, method, url, **kwargs):

        response = requests.request(
            method,
            url,
            headers=self._headers(),
            **kwargs
        )

        if response.status_code in (401, 403):

            self.access_token = BankTokenService.ensure_valid_token(
                self.db,
                self.connection
            )

            response = requests.request(
                method,
                url,
                headers=self._headers(),
                **kwargs
            )

        response.raise_for_status()

        if response.text:
            return response.json()

        return {}

    def build_account_id(self, account_number: str) -> str:
        return f"{account_number}/{TOCHKA_BIC}"

    def create_statement(self, account_number, start_date, end_date):

        account_id = self.build_account_id(account_number)

        url = f"{self.rs_url}/open-banking/v1.0/statements"

        payload = {
            "Data": {
                "Statement": {
                    "accountId": account_id,
                    "startDateTime": start_date,
                    "endDateTime": end_date
                }
            }
        }

        data = self._request(
            "POST",
            url,
            json=payload
        )

        return data["Data"]["Statement"]["statementId"]

    def get_statement(self, statement_id):

        url = f"{self.rs_url}/open-banking/v1.0/statements"

        params = {
            "statementId": statement_id
        }

        return self._request(
            "GET",
            url,
            params=params
        )

    def wait_statement_ready(self, statement_id, timeout=60):

        start = time.time()

        while True:

            data = self.get_statement(statement_id)

            statements = data.get("Data", {}).get("Statement", [])

            if not statements:
                time.sleep(2)
                continue

            status = statements[0]["status"]

            if status == "Ready":
                return statements[0]

            if time.time() - start > timeout:
                raise TimeoutError("Statement timeout")

            time.sleep(3)

    def get_transactions(self, statement_id):

        statement = self.wait_statement_ready(statement_id)

        return statement.get("Transaction", [])