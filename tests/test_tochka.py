from datetime import datetime

from app.integrations.tochka.client import TochkaClient
from app.config.settings import settings


def main():

    client = TochkaClient(
        settings.TOCHKA_ACCESS_TOKEN,
        settings.TOCHKA_CONSENT_ID
    )

    accounts = client.get_accounts()

    print("\nACCOUNTS:")
    print(accounts)

    # проверка что счета вообще есть
    if not accounts.get("Data", {}).get("Account"):
        print("No accounts found")
        return

    account_id = accounts["Data"]["Account"][0]["AccountId"]

    statements = client.get_statements(
        account_id,
        datetime(2026, 2, 1),
        datetime(2026, 3, 6)
    )

    print("\nSTATEMENTS:")
    print(statements)


if __name__ == "__main__":
    main()