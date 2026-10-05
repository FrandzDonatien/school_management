"""Connexion SQLite unique + helpers de requêtes."""
import os
import shutil
import sqlite3

from app.config import DATA_DIR, DB_PATH, LEGACY_DB_PATH

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
# Reprise automatique de l'ancienne base (version monofichier : ecole.db à la racine)
if not os.path.exists(DB_PATH) and os.path.dirname(DB_PATH) == DATA_DIR and os.path.exists(LEGACY_DB_PATH):
    shutil.move(LEGACY_DB_PATH, DB_PATH)

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA foreign_keys = ON")


def query(sql, params=()):
    return conn.execute(sql, params).fetchall()


def execute(sql, params=()):
    cur = conn.execute(sql, params)
    conn.commit()
    return cur.lastrowid
