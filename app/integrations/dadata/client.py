from dadata import Dadata
from app.config.settings import settings


class DadataClient:

    def __init__(self):

        self.client = Dadata(
            settings.DADATA_API_KEY,
            settings.DADATA_SECRET_KEY
        )

    def find_company_by_inn(self, inn: str):

        result = self.client.find_by_id("party", inn)

        if not result:
            return None

        company = result[0]

        return {
            "name": company["value"],
            "inn": company["data"]["inn"],
            "kpp": company["data"].get("kpp"),
            "ogrn": company["data"].get("ogrn"),
        }