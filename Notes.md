docker exec -it bank_postgres psql -U bank_user -d bank_saas
uvicorn app.main:app --reload
tree /F /A | findstr /V "__pycache__ venv .venv" > PROJECT_STRUCTURE.txt