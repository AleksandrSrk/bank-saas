from datetime import datetime
from app.integrations.tochka.client import TochkaClient
from app.config.settings import settings


def main():

    client = TochkaClient(settings.TOCHKA_ACCESS_TOKEN)

    accounts = client.get_accounts()

    print("ACCOUNTS:")
    print(accounts)

    statements = client.get_statements(
        "40702810020000066887/044525104",
        datetime(2026, 2, 1),
        datetime(2026, 3, 6)
    )

    print("STATEMENTS:")
    print(statements)


if __name__ == "__main__":
    main()