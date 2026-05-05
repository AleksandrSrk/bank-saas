import os
import requests

class SberClient:

    def __init__(self):
        self.base_url = "https://fintech.sberbank.ru:9443"

        # клиентский сертификат
        self.cert = (
            "certs/cert.pem",
            "certs/key.pem"
        )

        # цепочка доверенных сертификатов (у тебя это sber_chain.pem)
        self.verify = False

        self.headers = {
            "Authorization": f"Bearer {os.getenv('SBER_ACCESS_TOKEN')}"
        }

    def get_summary(self, account_number: str, date: str):
        """
        Returns statement summary for given day (contains balances/turnovers).
        """
        url = f"{self.base_url}/fintech/api/v2/statement/summary"

        params = {
            "accountNumber": account_number,
            "statementDate": date,
        }

        response = requests.get(
            url,
            params=params,
            headers=self.headers,
            cert=self.cert,
            verify=self.verify,
            timeout=30,
        )

        response.raise_for_status()

        return {
            "data": response.json(),
            # Bank/server time as seen by HTTP layer (useful for “real response” proof)
            "server_date": response.headers.get("Date"),
        }

    def get_operations(self, account_number: str, date: str, page: int = 1):

        url = f"{self.base_url}/fintech/api/v2/statement/transactions"

        params = {
            "accountNumber": account_number,
            "statementDate": date,
            "page": page
        }

        response = requests.get(
            url,
            params=params,
            headers=self.headers,
            cert=self.cert,
            verify=self.verify,
            timeout=30
        )

        # IMPORTANT: do not log tokens/headers/body/response here (docker logs are sensitive).

        response.raise_for_status()

        return response.json()