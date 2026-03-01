from fastapi import FastAPI
from sqlalchemy import text
from app.db.database import engine
app = FastAPI()


@app.get("/")
def healthcheck():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        return {"db_check": result.scalar()}