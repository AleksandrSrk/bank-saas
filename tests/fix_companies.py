from app.db.database import SessionLocal
from app.services.company_service import ensure_companies_from_operations

db = SessionLocal()

ensure_companies_from_operations(db)