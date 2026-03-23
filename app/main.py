from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.database import engine
from app.db.dependencies import get_db
from app.api.company_router import router as company_router
from app.api.bank_operation_router import router as bank_operation_router
from app.api.import_router import router as import_router
from app.api.bank_connection_router import router as bank_connection_router
from app.api.bank_sync_router import router as bank_sync_router
from app.services.sync_scheduler import start_scheduler

from app.api.telegram_router import router as telegram_router
from app.scripts.seed_roles import seed_roles

app = FastAPI()

app.include_router(company_router)
app.include_router(bank_operation_router)
app.include_router(import_router)
app.include_router(bank_connection_router)
app.include_router(bank_sync_router)

app.include_router(telegram_router)


@app.on_event("startup")
def startup_event():
    seed_roles()
    start_scheduler()
    
@app.get("/")
def healthcheck():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        return {"db_check": result.scalar()}


@app.get("/db-test")
def db_test(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT 1"))
    return {"result": result.scalar()}