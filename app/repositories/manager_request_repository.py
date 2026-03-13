import uuid
from sqlalchemy.orm import Session

from app.models.manager_request import ManagerRequest
from datetime import datetime

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

        db.commit()

        return request

    def reject_request(self, db: Session, request: ManagerRequest, director_id):
        request.status = "rejected"
        request.approved_by = director_id

        db.commit()

        return request
    
    def approve_request(self, db, request, director_id):

        request.status = "approved"
        request.approved_by = director_id
        request.approved_at = datetime.utcnow()

        db.commit()