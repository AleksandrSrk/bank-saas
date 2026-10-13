"""
Юнит-тесты авто-refresh токенов Сбера. Без сети и без БД: requests и сессия замоканы.

Запуск:  venv\\Scripts\\python -m pytest tests/test_sber_token_service.py -v
"""
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
import requests

import app.services.sber_token_service as sts
import app.integrations.banks.sber.client as sber_client_mod
from app.services.sber_token_service import SberTokenService, SberAuthError

NOW = datetime(2026, 10, 13, 12, 0, 0)


class FakeSession:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


class FakeResp:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.headers = {}

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")


@pytest.fixture
def env(monkeypatch):
    """Подменяет БД, время, настройки, алерты и requests.post у токен-сервиса."""
    conn = SimpleNamespace(
        access_token="OLD_ACCESS",
        refresh_token="OLD_REFRESH",
        expires_at=NOW + timedelta(minutes=30),
    )
    session = FakeSession()
    alerts = []
    posts = []
    state = SimpleNamespace(conn=conn, session=session, alerts=alerts, posts=posts, responses=[])

    monkeypatch.setattr(SberTokenService, "session_factory", staticmethod(lambda: session))
    monkeypatch.setattr(SberTokenService, "_lock_connection", staticmethod(lambda db: state.conn))
    monkeypatch.setattr(SberTokenService, "_now", staticmethod(lambda: NOW))
    monkeypatch.setattr(sts.settings, "SBER_CLIENT_ID", "32633")
    monkeypatch.setattr(sts.settings, "SBER_CLIENT_SECRET", "secret")
    monkeypatch.setattr(sts, "send_alert", lambda key, text: alerts.append(key))

    def fake_post(url, **kwargs):
        posts.append(kwargs)
        r = state.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    monkeypatch.setattr(sts.requests, "post", fake_post)
    return state


def ok_token_response(access="NEW_ACCESS", refresh="NEW_REFRESH"):
    return FakeResp(200, {"access_token": access, "refresh_token": refresh, "expires_in": 3600})


# ---------- SberTokenService ----------

def test_valid_token_is_returned_without_refresh(env):
    assert SberTokenService.get_access_token() == "OLD_ACCESS"
    assert env.posts == []
    assert env.session.commits == 1 and env.session.closed


def test_expiring_token_is_refreshed_and_pair_rotated(env):
    env.conn.expires_at = NOW + timedelta(minutes=3)  # меньше REFRESH_MARGIN
    env.responses.append(ok_token_response())

    assert SberTokenService.get_access_token() == "NEW_ACCESS"
    assert env.conn.refresh_token == "NEW_REFRESH"  # refresh одноразовый — новый сохранён
    assert env.conn.expires_at == NOW + timedelta(seconds=3600)
    sent = env.posts[0]
    assert sent["data"]["grant_type"] == "refresh_token"
    assert sent["data"]["refresh_token"] == "OLD_REFRESH"
    assert sent["data"]["client_id"] == "32633"
    assert sent["verify"] == sts.settings.SBER_CA_BUNDLE  # не verify=False
    assert env.session.commits == 1


def test_no_expires_at_forces_refresh(env):
    env.conn.expires_at = None  # так выглядит пара после sber_set_tokens
    env.responses.append(ok_token_response())
    assert SberTokenService.get_access_token() == "NEW_ACCESS"


def test_force_refresh_skipped_if_token_already_rotated_by_other_process(env):
    # нам отказали со старым токеном, а в БД уже лежит другой — повторно не рефрешим
    assert SberTokenService.get_access_token(force_refresh=True, rejected_token="STALE") == "OLD_ACCESS"
    assert env.posts == []


def test_force_refresh_when_rejected_token_is_current(env):
    env.responses.append(ok_token_response())
    assert SberTokenService.get_access_token(force_refresh=True, rejected_token="OLD_ACCESS") == "NEW_ACCESS"


def test_invalid_client_alerts_with_secret_hint_and_keeps_old_pair(env):
    env.conn.expires_at = NOW - timedelta(minutes=1)
    env.responses.append(FakeResp(401, {"error": "invalid_client", "error_description": "bad secret"}))

    with pytest.raises(SberAuthError) as exc:
        SberTokenService.get_access_token()

    assert "client_secret" in str(exc.value)
    assert env.alerts == ["sber_refresh_failed"]
    assert env.conn.refresh_token == "OLD_REFRESH"
    assert env.session.rollbacks >= 1 and env.session.commits == 0


def test_planned_refresh_failure_falls_back_to_still_alive_token(env):
    env.conn.expires_at = NOW + timedelta(minutes=2)  # пора рефрешить, но ещё жив
    env.responses.append(FakeResp(400, {"error": "invalid_grant"}))

    assert SberTokenService.get_access_token() == "OLD_ACCESS"
    assert env.alerts == ["sber_refresh_failed"]  # но директора предупредили


def test_network_error_while_token_alive_does_not_alert(env):
    env.conn.expires_at = NOW + timedelta(minutes=2)
    env.responses.append(requests.ConnectionError("boom"))

    assert SberTokenService.get_access_token() == "OLD_ACCESS"
    assert env.alerts == []


def test_network_error_when_token_dead_alerts(env):
    env.conn.expires_at = NOW - timedelta(minutes=1)
    env.responses.append(requests.ConnectionError("boom"))

    with pytest.raises(SberAuthError):
        SberTokenService.get_access_token()
    assert env.alerts == ["sber_refresh_network"]


def test_missing_refresh_token_alerts(env):
    env.conn.refresh_token = None
    with pytest.raises(SberAuthError):
        SberTokenService.get_access_token()
    assert env.alerts == ["sber_no_refresh"]


def test_set_tokens_resets_expiry(env):
    SberTokenService.set_tokens(" A1 ", "R1\n")
    assert (env.conn.access_token, env.conn.refresh_token, env.conn.expires_at) == ("A1", "R1", None)


# ---------- SberClient: 401 -> refresh -> retry ----------

@pytest.fixture
def client_env(monkeypatch):
    calls = SimpleNamespace(tokens=[], token_requests=[], alerts=[], gets=[])

    def fake_get_access_token(force_refresh=False, rejected_token=None):
        calls.token_requests.append((force_refresh, rejected_token))
        return "T2" if force_refresh else "T1"

    monkeypatch.setattr(sber_client_mod.SberTokenService, "get_access_token", staticmethod(fake_get_access_token))
    monkeypatch.setattr(sber_client_mod, "send_alert", lambda key, text: calls.alerts.append(key))

    def install(responses):
        def fake_get(url, **kwargs):
            calls.gets.append(kwargs)
            calls.tokens.append(kwargs["headers"]["Authorization"])
            return responses.pop(0)
        monkeypatch.setattr(sber_client_mod.requests, "get", fake_get)

    calls.install = install
    return calls


def test_client_retries_once_after_401(client_env):
    client_env.install([FakeResp(401), FakeResp(200, {"transactions": []})])

    assert sber_client_mod.SberClient().get_operations("4070", "2026-10-13") == {"transactions": []}
    assert client_env.tokens == ["Bearer T1", "Bearer T2"]
    assert client_env.token_requests == [(False, None), (True, "T1")]
    assert client_env.gets[0]["verify"] == sts.settings.SBER_CA_BUNDLE
    assert client_env.alerts == []


def test_client_alerts_if_still_401_after_refresh(client_env):
    client_env.install([FakeResp(401), FakeResp(401)])

    with pytest.raises(requests.HTTPError):
        sber_client_mod.SberClient().get_operations("4070", "2026-10-13")
    assert client_env.alerts == ["sber_401_after_refresh"]
