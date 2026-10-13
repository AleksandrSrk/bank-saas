import requests

from app.config.settings import settings
from app.services.alert_service import send_alert
from app.services.sber_token_service import SberTokenService


class SberClient:
    """
    Sber API (fintech.sberbank.ru:9443): mTLS + Bearer.
    Токен берётся из SberTokenService (БД + авто-refresh), при 401 — один refresh и повтор.
    """

    def __init__(self):
        self.base_url = settings.SBER_API_URL

        # клиентский сертификат (mTLS)
        self.cert = (settings.SBER_CERT_FILE, settings.SBER_KEY_FILE)

        # цепочка доверенных сертификатов Сбера (с портала: «Цепочка доверенных TLS-сертификатов»)
        self.verify = settings.SBER_CA_BUNDLE

    def _get(self, path: str, params: dict) -> requests.Response:
        url = f"{self.base_url}{path}"
        token = SberTokenService.get_access_token()

        response = self._send(url, params, token)

        if response.status_code == 401:
            token = SberTokenService.get_access_token(force_refresh=True, rejected_token=token)
            response = self._send(url, params, token)
            if response.status_code == 401:
                send_alert(
                    "sber_401_after_refresh",
                    f"Сбер: 401 даже после refresh токена ({path}). Проверь ключи на портале.",
                )

        # IMPORTANT: do not log tokens/headers/body/response here (docker logs are sensitive).
        response.raise_for_status()
        return response

    def _send(self, url: str, params: dict, token: str) -> requests.Response:
        return requests.get(
            url,
            params=params,
            headers={"Authorization": f"Bearer {token}"},
            cert=self.cert,
            verify=self.verify,
            timeout=30,
        )

    def get_summary(self, account_number: str, date: str):
        """
        Returns statement summary for given day (contains balances/turnovers).
        """
        response = self._get(
            "/fintech/api/v2/statement/summary",
            {"accountNumber": account_number, "statementDate": date},
        )
        return {
            "data": response.json(),
            # Bank/server time as seen by HTTP layer (useful for “real response” proof)
            "server_date": response.headers.get("Date"),
        }

    def get_operations(self, account_number: str, date: str, page: int = 1):
        response = self._get(
            "/fintech/api/v2/statement/transactions",
            {"accountNumber": account_number, "statementDate": date, "page": page},
        )
        return response.json()
