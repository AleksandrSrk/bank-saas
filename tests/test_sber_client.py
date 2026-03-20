from app.integrations.banks.sber.client import SberClient

client = SberClient()

data = client.get_operations(
    "40702810516750004863",  # sandbox счет
    "2026-03-18"
)

print(data)