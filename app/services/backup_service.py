"""Sauvegardes de la base SQLite dans data/backups."""
import datetime
import os

from app.config import BACKUP_DIR, BACKUP_KEEP
from app.database.connection import conn


def create_backup(keep=BACKUP_KEEP):
    """Copie cohérente de la base (API backup de SQLite) puis purge des plus anciennes. -> chemin."""
    import sqlite3
    os.makedirs(BACKUP_DIR, exist_ok=True)
    path = os.path.join(BACKUP_DIR, f"ecole_{datetime.datetime.now():%Y%m%d_%H%M%S}.db")
    dest = sqlite3.connect(path)
    try:
        conn.commit()
        conn.backup(dest)
    finally:
        dest.close()
    files = sorted(f for f in os.listdir(BACKUP_DIR) if f.startswith("ecole_") and f.endswith(".db"))
    for old in files[:-keep] if keep else []:
        os.remove(os.path.join(BACKUP_DIR, old))
    return path


def list_backups():
    if not os.path.isdir(BACKUP_DIR):
        return []
    return sorted((f for f in os.listdir(BACKUP_DIR) if f.endswith(".db")), reverse=True)
