"""Connexion SQLite unique + helpers de requêtes."""

import os
import shutil
import sqlite3
import sys
from pathlib import Path

from app.config import DATA_DIR, DB_PATH, LEGACY_DB_PATH


def resource_path(relative_path):
    """Localise une ressource en développement ou après compilation."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_dir = Path(sys._MEIPASS)
    else:
        base_dir = Path(__file__).resolve().parents[2]

    return base_dir / relative_path


# Créer les dossiers nécessaires
os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)

# Base initiale incluse dans l'exécutable
bundled_db = resource_path("data/ecole.db")

# Initialiser la base de travail uniquement si elle n'existe pas
if not os.path.isfile(DB_PATH):
    if os.path.isfile(LEGACY_DB_PATH):
        # Migrer l'ancienne base sans la supprimer
        shutil.copy2(LEGACY_DB_PATH, DB_PATH)

    elif os.path.isfile(bundled_db):
        # Copier la base initiale embarquée par PyInstaller
        shutil.copy2(bundled_db, DB_PATH)

    else:
        raise FileNotFoundError(
            "Base de données SQLite introuvable.\n"
            f"Base embarquée recherchée : {bundled_db}\n"
            f"Base de travail attendue : {DB_PATH}"
        )

# Connexion à la base de travail permanente
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA foreign_keys = ON")


def query(sql, params=()):
    return conn.execute(sql, params).fetchall()


def execute(sql, params=()):
    cur = conn.execute(sql, params)
    conn.commit()
    return cur.lastrowid