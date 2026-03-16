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

        users = db.query(User).all()

        result = {}

        for user in users:

            manager_name = user.name or "Менеджер"

            companies = (
                db.query(
                    TrackedCompany.id,
                    Company.name,
                    Company.inn
                )
                .join(Company, Company.id == TrackedCompany.company_id)
                .filter(
                    TrackedCompany.manager_id == user.id,
                    TrackedCompany.active == True
                )
                .all()
            )

            result[manager_name] = []

            for tracked_id, name, inn in companies:

                result[manager_name].append({
                    "tracked_id": str(tracked_id),
                    "name": name if name else "Без названия",
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
    
    def revoke_access(self, db: Session, tracked_id: str):

        tracked = db.query(TrackedCompany).filter(
            TrackedCompany.id == tracked_id
        ).first()

        if tracked:
            tracked.active = False