from datetime import datetime, timedelta

import requests
from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.db.dependencies import get_db
from app.services.bank_connection_service import BankConnectionService

router = APIRouter(prefix="/tochka/oauth", tags=["tochka oauth"])


@router.get("/callback")
def tochka_oauth_callback(
    code: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Redirect URL Точки после согласия пользователя на доступ.
    Точка редиректит сюда с ?code=... (authorization_code),
    мы меняем его на access_token/refresh_token и кладём в bank_connections.
    """

    if error:
        return PlainTextResponse(
            f"Точка вернула ошибку: {error} — {error_description or ''}",
            status_code=400,
        )

    if not code:
        return PlainTextResponse("В запросе нет параметра code.", status_code=400)

    if not settings.TOCHKA_REDIRECT_URI:
        return PlainTextResponse(
            "TOCHKA_REDIRECT_URI не задан в .env — без него обмен кода не пройдёт "
            "(должен точно совпадать со значением, зарегистрированным в Точке).",
            status_code=500,
        )

    response = requests.post(
        settings.TOCHKA_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.TOCHKA_REDIRECT_URI,
            "client_id": settings.TOCHKA_CLIENT_ID,
            "client_secret": settings.TOCHKA_CLIENT_SECRET,
        },
    )

    try:
        response.raise_for_status()
    except requests.HTTPError:
        body = (response.text or "").strip()
        return PlainTextResponse(
            f"Ошибка обмена code на токен ({response.status_code}): {body[:800]}",
            status_code=502,
        )

    data = response.json()

    connection = BankConnectionService.get_connection(db, "tochka")

    if not connection:
        return PlainTextResponse(
            "Токен от Точки получен, но в bank_connections нет записи с bank_name='tochka' "
            "— создать её вручную (нужен company_id), автосоздание тут не делаем.",
            status_code=500,
        )

    connection.access_token = data["access_token"]
    connection.refresh_token = data.get("refresh_token", connection.refresh_token)

    expires_in = data.get("expires_in")
    connection.expires_at = (
        datetime.utcnow() + timedelta(seconds=expires_in) if expires_in else None
    )

    db.commit()

    return PlainTextResponse("Готово. Токены Точки обновлены, можно закрывать вкладку.")
