from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.database import engine
from app.db.dependencies import get_db
from app.api.company_router import router as company_router
from app.api.bank_operation_router import router as bank_operation_router

app = FastAPI()

app.include_router(company_router)
app.include_router(bank_operation_router)

@app.get("/")
def healthcheck():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        return {"db_check": result.scalar()}


@app.get("/db-test")
def db_test(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT 1"))
    return {"result": result.scalar()}