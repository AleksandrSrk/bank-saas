from uuid import UUID
from pydantic import BaseModel, ConfigDict


class CompanyBase(BaseModel):
    name: str
    inn: str


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: str | None = None
    inn: str | None = None


class CompanyRead(CompanyBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)