from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.integrations.banks.sber.client import SberClient
from app.integrations.banks.tochka.client import TochkaClient
from app.models.bank_connection import BankConnection


class BalanceService:
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
                accounts = client.get_accounts().get("Data", {}).get("Account", [])
                items = []
                for acc in accounts:
                    account_id = acc.get("accountId")
                    if not account_id:
                        continue
                    account_number = account_id.split("/")[0]
                    bal = client.get_balance(account_number)
                    items.append(
                        {
                            "account_number": account_number,
                            "currency": acc.get("currency"),
                            "end_balance": bal.get("end_balance"),
                            "start_balance": bal.get("start_balance"),
                            "bank_timestamp": bal.get("bank_timestamp"),
                            "statement_id": bal.get("statementId"),
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

