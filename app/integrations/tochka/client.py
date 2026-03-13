import requests
from datetime import datetime


class TochkaClient:

    def __init__(self, access_token: str, consent_id: str):

        self.base_url = "https://enter.tochka.com/uapi"

        self.access_token = access_token
        self.consent_id = consent_id

        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "X-Consent-ID": consent_id,
            "Content-Type": "application/json"
        }

    # ------------------------------------------------
    # Счета
    # ------------------------------------------------

    def get_accounts(self):

        url = f"{self.base_url}/open-banking/v1.0/accounts"

        response = requests.get(url, headers=self.headers)

        response.raise_for_status()

        return response.json()

    # ------------------------------------------------
    # Балансы
    # ------------------------------------------------

    def get_balances(self):

        url = f"{self.base_url}/open-banking/v1.0/balances"

        response = requests.get(url, headers=self.headers)

        response.raise_for_status()

        return response.json()

    # ------------------------------------------------
    # 1. Создание выписки
    # ------------------------------------------------

    def create_statement(self, account_id: str, from_date: datetime, to_date: datetime):

        url = f"{self.base_url}/open-banking/v1.0/statements"

        payload = {
            "Data": {
                "Statement": {
                    "accountId": account_id,
                    "startDateTime": from_date.strftime("%Y-%m-%d"),
                    "endDateTime": to_date.strftime("%Y-%m-%d")
                }
            }
        }

        response = requests.post(
            url,
            json=payload,
            headers=self.headers
        )

        response.raise_for_status()

        return response.json()

    # ------------------------------------------------
    # 2. Получение выписки
    # ------------------------------------------------

    def get_statement(self, account_id: str, statement_id: str):

        url = f"{self.base_url}/open-banking/v1.0/accounts/{account_id}/statements/{statement_id}"

        response = requests.get(
            url,
            headers=self.headers
        )

        response.raise_for_status()

        return response.json()