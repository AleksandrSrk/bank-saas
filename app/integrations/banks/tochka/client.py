import time
import requests

from app.config.settings import settings
from app.services.bank_connection_service import BankConnectionService


class TochkaClient:

    def __init__(self, db):

        self.db = db

        self.client_id = settings.TOCHKA_CLIENT_ID
        self.client_secret = settings.TOCHKA_CLIENT_SECRET

        self.as_url = settings.TOCHKA_AS_URL
        self.rs_url = settings.TOCHKA_RS_URL

        connection = BankConnectionService.get_connection(db, "tochka")

        self.connection = connection
        self.access_token = connection.access_token
        self.refresh_token = connection.refresh_token

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

        if response.status_code == 401:
            self.refresh_access_token()

            response = requests.request(
                method,
                url,
                headers=self._headers(),
                **kwargs
            )

        response.raise_for_status()

        return response.json()

    def refresh_access_token(self):

        url = f"{self.as_url}/connect/token"

        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }

        response = requests.post(url, data=data)

        response.raise_for_status()

        token_data = response.json()

        self.access_token = token_data["access_token"]
        self.refresh_token = token_data["refresh_token"]

        BankConnectionService.update_tokens(
            self.db,
            self.connection,
            token_data["access_token"],
            token_data["refresh_token"],
            token_data["expires_in"]
        )

        return token_data

    def get_accounts(self):

        url = f"{self.rs_url}/open-banking/v1.0/accounts"

        return self._request("GET", url)

    def create_statement(self, account_id, start_date, end_date):

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

        data = self._request("POST", url, json=payload)

        return data["Data"]["Statement"]["statementId"]

    def get_statement(self, statement_id):

        url = f"{self.rs_url}/open-banking/v1.0/statements"

        params = {
            "statementId": statement_id
        }

        return self._request("GET", url, params=params)

    def wait_statement_ready(self, statement_id, timeout=60):

        start_time = time.time()

        while True:

            data = self.get_statement(statement_id)

            status = data["Data"]["Statement"][0]["status"]

            if status == "Ready":
                return data

            if time.time() - start_time > timeout:
                raise TimeoutError("Statement generation timeout")

            time.sleep(3)

    def get_transactions(self, statement_id):

        data = self.wait_statement_ready(statement_id)

        return data["Data"]["Statement"][0]["Transaction"]