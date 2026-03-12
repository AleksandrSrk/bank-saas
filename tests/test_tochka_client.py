from app.integrations.banks.tochka.client import TochkaClient
from app.config.settings import settings


client = TochkaClient()

accounts = client.get_accounts()

account_id = settings.TOCHKA_ACCOUNT_ID

statement_id = client.create_statement(
    account_id,
    "2023-01-01",
    "2026-12-31"
)

transactions = client.get_transactions(statement_id)

print(len(transactions))