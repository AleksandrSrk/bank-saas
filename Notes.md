# Запуск докера
docker exec -it bank_postgres psql -U bank_user -d bank_saas

# Запуск свагера
uvicorn app.main:app --reload

# Дерево проекта
tree /F /A | findstr /V "__pycache__ venv .venv" > PROJECT_STRUCTURE.txt

# Перед коммитом делают: Если файл пустой: удаляют его Если нет — значит забыли миграцию.
alembic revision --autogenerate -m "check"
alembic revision --autogenerate -m "check_schema"

# Если они совпадают — всё обновлено.
alembic current
alembic heads 

# Перед применением миграции всегда делай: 
alembic revision --autogenerate -m "..." 
Если Alembic пишет что-то кроме: Detected added table Detected added column значит нужно проверить.

# Запуск бота тлг 
python -m bot.telegram_bot

# Запуск мануал синк
python tests/manual_sync.py

