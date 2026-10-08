"""Chemins et paramètres techniques de l'application."""
import os

APP_NAME = "EduManager"
APP_VERSION = "5.0"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
# EDUMANAGER_DB permet de rediriger la base (utilisé par les tests)
DB_PATH = os.environ.get("EDUMANAGER_DB") or os.path.join(DATA_DIR, "ecole.db")
LEGACY_DB_PATH = os.path.join(BASE_DIR, "ecole.db")  # ancien emplacement (version monofichier)
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
BACKUP_KEEP = 10

ASSETS_DIR = os.path.join(BASE_DIR, "assets")
ICONS_DIR = os.path.join(ASSETS_DIR, "icons")
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")
SIGNATURES_DIR = os.path.join(ASSETS_DIR, "signatures")  # une image par enseignant (signature du bulletin)
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")
BULLETINS_DIR = os.path.join(EXPORTS_DIR, "bulletins")
SCHEDULE_DIR = os.path.join(EXPORTS_DIR, "emplois_du_temps")
EXCEL_DIR = os.path.join(EXPORTS_DIR, "excel")

TEMPLATES_DIR = os.path.join(BASE_DIR, "app", "reports", "templates")


def ensure_dirs():
    for d in (DATA_DIR, BACKUP_DIR, ASSETS_DIR, ICONS_DIR, IMAGES_DIR, BULLETINS_DIR, SCHEDULE_DIR, EXCEL_DIR,SIGNATURES_DIR):
        os.makedirs(d, exist_ok=True)
