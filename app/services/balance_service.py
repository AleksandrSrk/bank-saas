from __future__ import annotations

from datetime import date, datetime
import time
from typing import Any

from sqlalchemy.orm import Session

from app.integrations.banks.sber.client import SberClient
from app.integrations.banks.tochka.client import TochkaClient
from app.models.bank_connection import BankConnection


class BalanceService:
    _cache_value: dict[str, Any] | None = None
    _cache_until_monotonic: float = 0.0

    @staticmethod
    def get_balances_cached(db: Session, ttl_seconds: int = 60) -> dict[str, Any]:
        now_m = time.monotonic()
        if BalanceService._cache_value is not None and now_m < BalanceService._cache_until_monotonic:
            return BalanceService._cache_value

        value = BalanceService.get_balances(db)
        BalanceService._cache_value = value
        BalanceService._cache_until_monotonic = now_m + ttl_seconds
        return value

    @staticmethod
    def _extract_sber_balances(summary: dict) -> dict:
        """
        Best-effort extraction of balances from Sber summary response.
        Different scopes/versions can return different shapes, so we keep it defensive.
        """
        out: dict = {}
        if not isinstance(summary, dict):
            return out

        # Common-ish keys that may appear in summary responses
        for key in (
            "openingBalance",
            "closingBalance",
            "startBalance",
            "endBalance",
            "incomingTurnover",
            "outgoingTurnover",
            "creditTurnover",
            "debitTurnover",
            "currency",
        ):
            if key in summary:
                out[key] = summary.get(key)

        # Some APIs nest in Data/Statement-like objects; try a couple of paths
        for path in (("data",), ("Data",), ("Data", "Summary"), ("summary",)):
            cur = summary
            ok = True
            for p in path:
                if isinstance(cur, dict) and p in cur:
                    cur = cur[p]
                else:
                    ok = False
                    break
            if ok and isinstance(cur, dict):
                for key in (
                    "openingBalance",
                    "closingBalance",
                    "startBalance",
                    "endBalance",
                    "incomingTurnover",
                    "outgoingTurnover",
                    "currency",
                ):
                    if key in cur and key not in out:
                        out[key] = cur.get(key)

        return out

    @staticmethod
    def get_balances(db: Session) -> dict[str, Any]:
        now_utc = datetime.utcnow().isoformat() + "Z"
        today = date.today().strftime("%Y-%m-%d")

        result: dict[str, Any] = {
            "requested_at_utc": now_utc,
            "date": today,
            "tochka": None,
            "sber": None,
        }

        connections = {c.bank_name: c for c in db.query(BankConnection).all()}

        # ---- Tochka ----
        if "tochka" in connections:
            try:
                client = TochkaClient(db)
                accounts_resp = client.get_accounts()
                accounts = accounts_resp.get("Data", {}).get("Account", [])

                # Prefer balances list endpoint for "current" balances.
                balances_map: dict[str, Any] = {}
                try:
                    balances_resp = client.get_balances_list()
                    items = (
                        (balances_resp.get("Data") or {}).get("Balance")
                        or (balances_resp.get("data") or {}).get("balance")
                        or balances_resp.get("Balance")
                        or balances_resp.get("balances")
                        or []
                    )
                    if isinstance(items, dict):
                        items = [items]
                    if isinstance(items, list):
                        for b in items:
                            if not isinstance(b, dict):
                                continue
                            acc_id = b.get("accountId") or b.get("account_id")
                            if acc_id:
                                balances_map[str(acc_id)] = b
                except Exception:
                    # If the endpoint isn't available / returns unexpected shape, fallback to statements.
                    balances_map = {}

                items = []
                for acc in accounts:
                    account_id = acc.get("accountId")
                    if not account_id:
                        continue
                    # Skip non-RUB accounts for faster/cleaner output (user asked to hide KZT).
                    currency = acc.get("currency")
                    if currency and currency != "RUB":
                        continue

                    account_number = account_id.split("/")[0]
                    current = balances_map.get(str(account_id))
                    if current:
                        # best-effort parse current balance fields
                        amt_obj = (
                            current.get("Amount")
                            or current.get("amount")
                            or current.get("balanceAmount")
                            or current.get("balance")
                        )
                        if isinstance(amt_obj, dict):
                            amount = amt_obj.get("amount") or amt_obj.get("value") or amt_obj.get("Amount")
                            cur = amt_obj.get("currency") or amt_obj.get("currencyName") or currency
                        else:
                            amount = amt_obj
                            cur = currency

                        bank_ts = current.get("dateTime") or current.get("asOfDateTime") or current.get("timestamp")
                        items.append(
                            {
                                "account_number": account_number,
                                "currency": cur or currency,
                                "current_balance": amount,
                                "bank_timestamp": bank_ts,
                                "source": "balances",
                            }
                        )
                        continue

                    # fallback: statement-based balances for the day
                    bal = client.get_balance(account_number)
                    items.append(
                        {
                            "account_number": account_number,
                            "currency": currency,
                            "current_balance": bal.get("end_balance"),
                            "start_balance": bal.get("start_balance"),
                            "bank_timestamp": bal.get("bank_timestamp"),
                            "statement_id": bal.get("statementId"),
                            "source": "statement",
                        }
                    )
                result["tochka"] = {"accounts": items}
            except Exception as e:
                result["tochka"] = {"error": str(e)}

        # ---- Sber ----
        if "sber" in connections:
            try:
                # In this project, Sber accounts list is bootstrap-based.
                from app.config.settings import settings

                account_number = settings.SBER_BOOTSTRAP_ACCOUNT
                if not account_number:
                    result["sber"] = {"error": "SBER_BOOTSTRAP_ACCOUNT not set"}
                else:
                    client = SberClient()
                    summary = client.get_summary(account_number=account_number, date=today)
                    data = summary.get("data") or {}

                    extracted = BalanceService._extract_sber_balances(data)
                    result["sber"] = {
                        "account_number": account_number,
                        "bank_timestamp": summary.get("server_date"),
                        "balances": extracted,
                        "raw_summary": data,
                    }
            except Exception as e:
                result["sber"] = {"error": str(e)}

        return result

