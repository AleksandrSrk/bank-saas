from sqlalchemy.orm import Session

from app.models.tracked_company import TrackedCompany
from app.models.company import Company
from app.models.user import User


class TrackedCompanyRepository:

    def get_manager_companies(self, db: Session, manager_id):

        return (
            db.query(
                TrackedCompany,
                Company.name,
                Company.inn
            )
            .join(Company, Company.id == TrackedCompany.company_id)
            .filter(
                TrackedCompany.manager_id == manager_id,
                TrackedCompany.active == True
            )
            .all()
        )


    def get_all_tracked_grouped(self, db: Session):

        rows = (
            db.query(
                User.name,
                TrackedCompany.id,
                Company.name,
                Company.inn
            )
            .join(TrackedCompany, TrackedCompany.manager_id == User.id)
            .join(Company, Company.id == TrackedCompany.company_id)
            .filter(TrackedCompany.active == True)
            .all()
        )

        result = {}

        for manager_name, tracked_id, company_name, inn in rows:

            if manager_name not in result:
                result[manager_name] = []

            result[manager_name].append({
                "tracked_id": str(tracked_id),
                "name": company_name if company_name else "Без названия",
                "inn": inn
            })

        return result


    def is_company_tracked(self, db: Session, manager_id, company_id):

        existing = (
            db.query(TrackedCompany)
            .filter(
                TrackedCompany.manager_id == manager_id,
                TrackedCompany.company_id == company_id,
                TrackedCompany.active == True
            )
            .first()
        )

        return existing is not None