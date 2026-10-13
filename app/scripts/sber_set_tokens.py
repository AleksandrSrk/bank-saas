"""
Залить пару токенов Сбера в bank_connections (после генерации ключей на портале).

Токены читаются из stdin, чтобы не светились в истории shell и в `ps`:

  # JSON-ответ Сбера ({"access_token": ..., "refresh_token": ...}):
  docker exec -i bank_backend python -m app.scripts.sber_set_tokens < tokens.json

  # или две строки: access, затем refresh:
  printf '%s\n%s\n' "$ACCESS" "$REFRESH" | docker exec -i bank_backend python -m app.scripts.sber_set_tokens

expires_at сбрасывается, поэтому на ближайшем запросе сервис сразу сделает refresh —
так заодно проверим, что пара живая.
"""
import json
import sys

from app.services.sber_token_service import SberTokenService


def parse(raw: str) -> tuple[str, str]:
    raw = raw.strip()
    if raw.startswith("{"):
        data = json.loads(raw)
        return data.get("access_token", ""), data.get("refresh_token", "")
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if len(lines) != 2:
        raise ValueError("Ожидаю JSON или ровно две строки: access, refresh")
    return lines[0], lines[1]


def main() -> None:
    access, refresh = parse(sys.stdin.read())
    SberTokenService.set_tokens(access, refresh)
    print(f"OK: sber tokens saved (access {access[:4]}..., refresh {refresh[:4]}...), refresh on next request")


if __name__ == "__main__":
    main()
