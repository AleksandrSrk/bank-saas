"""
Алерты директору в Telegram (через токен bank_bot, напрямую в Bot API).

Троттлинг в памяти процесса: один и тот же ключ не чаще раза в THROTTLE.
После рестарта контейнера счётчик сбрасывается — это ок, лишний алерт лучше пропущенного.
"""
import threading
from datetime import datetime, timedelta

import requests

from app.config.settings import settings

THROTTLE = timedelta(hours=3)

_last_sent: dict[str, datetime] = {}
_lock = threading.Lock()


def send_alert(key: str, text: str) -> bool:
    """Шлёт алерт, если по этому key не слали последние THROTTLE. Никогда не кидает исключений."""
    chat_id = settings.ALERT_TELEGRAM_CHAT_ID
    if not chat_id or not settings.TELEGRAM_BOT_TOKEN:
        print(f"⚠️ ALERT (no chat configured) [{key}]: {text}")
        return False

    now = datetime.utcnow()
    with _lock:
        last = _last_sent.get(key)
        if last and now - last < THROTTLE:
            return False
        _last_sent[key] = now

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": f"🚨 bank-saas\n{text}"},
            timeout=15,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        # Не логируем URL — в нём токен бота.
        print(f"⚠️ ALERT send failed [{key}]: {type(e).__name__}")
        return False


def reset_throttle() -> None:
    """Для тестов."""
    with _lock:
        _last_sent.clear()
