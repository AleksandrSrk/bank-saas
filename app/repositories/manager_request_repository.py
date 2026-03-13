import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.manager_request import ManagerRequest
from app.models.tracked_company import TrackedCompany
from app.models.company import Company


class ManagerRequestRepository:

    def create_request(self, db: Session, manager_id, inn: str) -> ManagerRequest:

        request = ManagerRequest(
            id=uuid.uuid4(),
            manager_id=manager_id,
            inn=inn,
            status="pending"
        )

        db.add(request)
        db.flush()

        return request


    def get_pending_requests(self, db: Session):

        return (
            db.query(ManagerRequest)
            .filter(ManagerRequest.status == "pending")
            .all()
        )


    def get_by_id(self, db: Session, request_id):

        return (
            db.query(ManagerRequest)
            .filter(ManagerRequest.id == request_id)
            .first()
        )


    def approve_request(self, db: Session, request: ManagerRequest, director_id):

        request.status = "approved"
        request.approved_by = director_id
        request.approved_at = datetime.utcnow()

        company = (
            db.query(Company)
            .filter(Company.inn == request.inn)
            .first()
        )

        company_name = None

        if company:

            company_name = company.name

            existing = (
                db.query(TrackedCompany)
                .filter(
                    TrackedCompany.manager_id == request.manager_id,
                    TrackedCompany.company_id == company.id
                )
                .first()
            )

            if not existing:
                tracked_company = TrackedCompany(
                    manager_id=request.manager_id,
                    company_id=company.id
                )

                db.add(tracked_company)

        db.flush()

        return request, company_name


    def reject_request(self, db: Session, request: ManagerRequest, director_id):

        request.status = "rejected"
        request.approved_by = director_id
        request.approved_at = datetime.utcnow()

        db.flush()

        return request