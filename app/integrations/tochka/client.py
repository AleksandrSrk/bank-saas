import requests
from datetime import datetime


class TochkaClient:

    def __init__(self, access_token: str, consent_id: str):

        self.base_url = "https://enter.tochka.com/uapi"

        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "X-Consent-ID": consent_id
        }

    def get_accounts(self):

        url = f"{self.base_url}/open-banking/v1.0/accounts"

        response = requests.get(url, headers=self.headers)

        response.raise_for_status()

        return response.json()

    def get_balances(self):

        url = f"{self.base_url}/open-banking/v1.0/balances"

        response = requests.get(url, headers=self.headers)

        response.raise_for_status()

        return response.json()

    def get_statements(self, account_id: str, from_date: datetime, to_date: datetime):

        url = f"{self.base_url}/open-banking/v1.0/statements"

        params = {
            "accountId": account_id,
            "fromDateTime": from_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "toDateTime": to_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        response = requests.get(url, headers=self.headers, params=params)

        response.raise_for_status()

        return response.json()