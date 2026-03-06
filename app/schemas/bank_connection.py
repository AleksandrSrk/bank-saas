from pydantic import BaseModel
from uuid import UUID


class BankConnectionCreate(BaseModel):

    company_id: UUID
    bank_name: str
    access_token: str
    refresh_token: str | None = None
    expires_in: int | None = None