"""Бэкап Postgres в Google Drive — тот же принцип, что в doxBot (VACUUM
INTO → Drive), но для Postgres используем pg_dump, а не SQLite-механизм.
Свой сервисный аккаунт, своя папка на Диске — изолированы от doxBot."""

import os
import subprocess
import tempfile
from datetime import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "./service_account.json")
BACKUP_FILE_ID = os.getenv("BACKUP_FILE_ID", "")

_service = None


def _get_service():
    global _service
    if _service is None:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        _service = build("drive", "v3", credentials=creds)
    return _service


def backup_database():
    """pg_dump в сжатом бинарном формате (-F c) → поверх уже существующего
    файла в Drive (сервисный аккаунт не может создавать новые файлы — нет
    своей квоты на обычном личном Диске). Старые версии остаются в истории
    версий самого файла."""
    if not BACKUP_FILE_ID:
        print("Backup skipped: BACKUP_FILE_ID не задан")
        return
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        print("Backup skipped: DATABASE_URL не задан")
        return

    tmp_path = os.path.join(tempfile.gettempdir(), "bank_saas_backup.dump")
    try:
        subprocess.run(
            ["pg_dump", database_url, "-F", "c", "-f", tmp_path],
            check=True, capture_output=True, text=True,
        )
        media = MediaFileUpload(tmp_path, mimetype="application/octet-stream")
        _get_service().files().update(
            fileId=BACKUP_FILE_ID, media_body=media, fields="id,name"
        ).execute()
        print(f"Backup OK: {datetime.now().isoformat()}")
    except subprocess.CalledProcessError as e:
        print(f"Backup FAILED (pg_dump): {e.stderr}")
    except Exception as e:
        print(f"Backup FAILED: {e}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
