"""
Токены Сбера: хранение в bank_connections + авто-refresh.

Особенности Сбера (developers.sber.ru, OAuth):
- access_token живёт 60 минут;
- refresh одноразовый: каждый refresh выдаёт НОВУЮ пару access+refresh,
  старый refresh остаётся резервным ещё 2 часа. Поэтому новую пару сохраняем сразу;
- для refresh нужен client_secret (живёт 40 дней) и клиентский mTLS-сертификат.

Работа идёт в СВОЕЙ сессии БД (не в сессии синка), чтобы commit/rollback токенов
не задевал недописанные батчи операций.
Refresh делается под SELECT ... FOR UPDATE по строке подключения, чтобы шедулер
и API (балансы) не отрефрешили одним refresh_token дважды.
"""
from datetime import datetime, timedelta

import requests

from app.config.settings import settings
from app.db.database import SessionLocal
from app.models.bank_connection import BankConnection
from app.services.alert_service import send_alert

BANK_NAME = "sber"
REFRESH_MARGIN = timedelta(minutes=5)


class SberAuthError(Exception):
    pass


class SberTokenService:

    # подменяется в тестах
    session_factory = SessionLocal

    @staticmethod
    def _now() -> datetime:
        return datetime.utcnow()

    @staticmethod
    def _lock_connection(db) -> BankConnection | None:
        return (
            db.query(BankConnection)
            .filter(BankConnection.bank_name == BANK_NAME)
            .with_for_update()
            .first()
        )

    @classmethod
    def _needs_refresh(cls, conn: BankConnection) -> bool:
        if not conn.expires_at:
            return True
        return conn.expires_at - REFRESH_MARGIN <= cls._now()

    @classmethod
    def get_access_token(cls, force_refresh: bool = False, rejected_token: str | None = None) -> str:
        """
        Живой access_token Сбера. Рефрешит заранее (за REFRESH_MARGIN до истечения).
        force_refresh=True — после 401: рефрешим, если токен в БД всё ещё тот, что отвергли
        (иначе его уже обновил другой процесс, пока мы ждали лок).
        """
        db = cls.session_factory()
        try:
            conn = cls._lock_connection(db)
            if not conn or not conn.refresh_token:
                msg = (
                    "Сбер: в bank_connections нет refresh_token. "
                    "Залей токены: docker exec -i bank_backend python -m app.scripts.sber_set_tokens < tokens.json"
                )
                send_alert("sber_no_refresh", msg)
                raise SberAuthError(msg)

            if force_refresh:
                must_refresh = rejected_token is None or conn.access_token == rejected_token
            else:
                must_refresh = cls._needs_refresh(conn)

            if must_refresh:
                old_token = conn.access_token
                old_alive = conn.expires_at is not None and conn.expires_at > cls._now()
                try:
                    cls._refresh(conn)
                except SberAuthError:
                    # плановый refresh не удался, но старый токен ещё жив — работаем на нём
                    if not force_refresh and old_alive:
                        db.rollback()
                        return old_token
                    raise

            token = conn.access_token
            db.commit()
            return token
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @classmethod
    def set_tokens(cls, access_token: str, refresh_token: str) -> None:
        """
        Ручная заливка пары (после генерации ключей на портале).
        expires_at=None -> на ближайшем запросе сразу будет refresh, заодно проверим, что пара живая.
        """
        if not access_token or not refresh_token:
            raise ValueError("access_token и refresh_token обязательны")
        db = cls.session_factory()
        try:
            conn = cls._lock_connection(db)
            if not conn:
                raise SberAuthError("Нет строки sber в bank_connections")
            conn.access_token = access_token.strip()
            conn.refresh_token = refresh_token.strip()
            conn.expires_at = None
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _safe_error(resp) -> str:
        """Текст ошибки от Сбера без риска засветить токены (в ошибках их нет, но режем на всякий)."""
        try:
            data = resp.json()
            parts = [str(data.get("error") or ""), str(data.get("error_description") or "")]
            text = " | ".join(p for p in parts if p)
            if text:
                return text[:200]
        except Exception:
            pass
        return (resp.text or "").strip()[:200]

    @classmethod
    def _refresh(cls, conn: BankConnection) -> None:
        if not settings.SBER_CLIENT_ID or not settings.SBER_CLIENT_SECRET:
            msg = "Сбер: не заданы SBER_CLIENT_ID / SBER_CLIENT_SECRET в .env"
            send_alert("sber_config", msg)
            raise SberAuthError(msg)

        try:
            resp = requests.post(
                settings.SBER_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": conn.refresh_token,
                    "client_id": settings.SBER_CLIENT_ID,
                    "client_secret": settings.SBER_CLIENT_SECRET,
                },
                headers={"Accept": "application/json"},
                cert=(settings.SBER_CERT_FILE, settings.SBER_KEY_FILE),
                verify=settings.SBER_CA_BUNDLE,
                timeout=30,
            )
        except requests.RequestException as e:
            # Сбер просит: если ответа не было — повторить тем же refresh в течение часа.
            # Следующий цикл синка (5 мин) так и сделает: refresh_token в БД не тронут.
            msg = f"Сбер: refresh не дошёл до банка ({type(e).__name__}), повторю на следующем цикле"
            # разовый сетевой глюк, пока старый токен ещё жив, — не повод будить директора
            token_still_alive = conn.expires_at is not None and conn.expires_at > cls._now()
            if not token_still_alive:
                send_alert("sber_refresh_network", msg)
            raise SberAuthError(msg) from e

        if resp.status_code != 200:
            err = cls._safe_error(resp)
            low = err.lower()
            hint = ""
            if "invalid_client" in low or "secret" in low:
                hint = ("\nПохоже, протух client_secret (живёт 40 дней): перевыпусти на портале "
                        "и обнови SBER_CLIENT_SECRET в .env, потом docker compose up -d backend.")
            elif "invalid_grant" in low:
                hint = ("\nrefresh_token недействителен: сгенерь ключи на портале и залей "
                        "через app.scripts.sber_set_tokens.")
            msg = f"Сбер: refresh отклонён ({resp.status_code}): {err}{hint}"
            send_alert("sber_refresh_failed", msg)
            raise SberAuthError(msg)

        data = resp.json()
        access = data.get("access_token")
        if not access:
            msg = "Сбер: в ответе refresh нет access_token"
            send_alert("sber_refresh_failed", msg)
            raise SberAuthError(msg)

        conn.access_token = access
        # refresh одноразовый — обязательно сохраняем новый
        if data.get("refresh_token"):
            conn.refresh_token = data["refresh_token"]
        conn.expires_at = cls._now() + timedelta(seconds=int(data.get("expires_in") or 3600))
        print(f"🔄 [sber] token refreshed, expires_at={conn.expires_at:%Y-%m-%d %H:%M} UTC")
