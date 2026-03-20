import requests
from datetime import datetime, timedelta

from app.models.bank_connection import BankConnection
from app.config.settings import settings


from requests.auth import HTTPBasicAuth


class BankTokenService:

    @staticmethod
    def ensure_valid_token(db, connection: BankConnection):

        # если нет expires_at — просто используем токен
        if not connection.expires_at:
            return connection.access_token

        # если токен еще жив — возвращаем его
        if connection.expires_at > datetime.utcnow():
            return connection.access_token

        # токен истек — обновляем
        new_token = BankTokenService.refresh_token(connection)

        connection.access_token = new_token["access_token"]
        connection.refresh_token = new_token.get(
            "refresh_token",
            connection.refresh_token
        )

        connection.expires_at = datetime.utcnow() + timedelta(
            seconds=new_token["expires_in"]
        )

        db.commit()

        return connection.access_token

    @staticmethod
    def refresh_token(connection: BankConnection):

        url = settings.TOCHKA_TOKEN_URL

        payload = {
            "grant_type": "refresh_token",
            "refresh_token": connection.refresh_token,
        }

        # response = requests.post(
        #     url,
        #     data=payload,
        #     auth=HTTPBasicAuth(
        #         settings.TOCHKA_CLIENT_ID,
        #         settings.TOCHKA_CLIENT_SECRET
        #     ),
        # )
        response = requests.post(
            url,
            data={
                "grant_type": "refresh_token",
                "refresh_token": connection.refresh_token,
            }
        )

        print("TOCHKA REFRESH RESPONSE:", response.text)
        print("PAYLOAD:", payload)
        print("AUTH:", settings.TOCHKA_CLIENT_ID, settings.TOCHKA_CLIENT_SECRET)
        print("REQUEST HEADERS:", response.request.headers)
        print("REQUEST BODY:", response.request.body)



        response.raise_for_status()

        return response.json()