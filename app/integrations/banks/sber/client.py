import requests
import os
from dotenv import load_dotenv


load_dotenv()

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

        # ⚠️ ПОКА оставляем хардкод (потом вынесем в env)
        
        print("TOKEN:", os.getenv("SBER_ACCESS_TOKEN"))

        self.headers = {
            "Authorization": f"Bearer {os.getenv('SBER_ACCESS_TOKEN')}"
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

        print("SBER STATUS:", response.status_code)
        print("SBER RESPONSE:", response.text[:500])

        print("SBER URL:", response.request.url)
        print("SBER METHOD:", response.request.method)
        print("SBER HEADERS:", response.request.headers)
        print("SBER BODY:", response.request.body)
        print("SBER RESPONSE:", response.text)

        response.raise_for_status()

        return response.json()