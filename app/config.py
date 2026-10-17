"""Chemins et paramètres techniques de l'application."""
import os
import sys

APP_NAME = "EduManager"
APP_VERSION = "5.0"

if getattr(sys, "frozen", False):
    # Ressources embarquées (lecture seule), dans le dossier temporaire
    BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    # Données persistantes : à côté de l'exe
    USER_DIR = os.path.dirname(sys.executable)
    # Alternative (AppData) :
    # USER_DIR = os.path.join(os.environ["LOCALAPPDATA"], APP_NAME)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    USER_DIR = BASE_DIR

# Données utilisateur (persistantes)
DATA_DIR = os.path.join(USER_DIR, "data")
# EDUMANAGER_DB permet de rediriger la base (utilisé par les tests)
DB_PATH = os.environ.get("EDUMANAGER_DB") or os.path.join(DATA_DIR, "ecole.db")
LEGACY_DB_PATH = os.path.join(USER_DIR, "ecole.db")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
BACKUP_KEEP = 10
SIGNATURES_DIR = os.path.join(USER_DIR, "signatures")
EXPORTS_DIR = os.path.join(USER_DIR, "exports")
BULLETINS_DIR = os.path.join(EXPORTS_DIR, "bulletins")
SCHEDULE_DIR = os.path.join(EXPORTS_DIR, "emplois_du_temps")
EXCEL_DIR = os.path.join(EXPORTS_DIR, "excel")

# Ressources embarquées (lecture seule)
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
ICONS_DIR = os.path.join(ASSETS_DIR, "icons")
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")
TEMPLATES_DIR = os.path.join(BASE_DIR, "app", "reports", "templates")


def ensure_dirs():
    for d in (DATA_DIR, BACKUP_DIR, SIGNATURES_DIR,
              EXPORTS_DIR, BULLETINS_DIR, SCHEDULE_DIR, EXCEL_DIR):
        os.makedirs(d, exist_ok=True)