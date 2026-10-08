"""Numéros uniques des bulletins (anti-fraude).

Chaque bulletin (élève + période + année) reçoit un numéro aléatoire, impossible à deviner, enregistré dans la
base : réimprimer le même bulletin garde le même numéro, et la saisie du numéro permet de vérifier les
informations officielles (moyenne, rang…) face au document papier.

Ce module ouvre lui-même le fichier de base (config.DB_PATH) et crée sa table au premier usage.
"""
import datetime
import re
import secrets
import sqlite3
from contextlib import closing

from app.config import DB_PATH

_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"        # sans O, 0, I, 1 (lisibilité)
_SCHEMA = """CREATE TABLE IF NOT EXISTS bulletin_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL,
    student_id INTEGER NOT NULL, annee_id INTEGER NOT NULL DEFAULT 0, periode TEXT NOT NULL,
    eleve TEXT, classe TEXT, annee TEXT, moyenne REAL, rang INTEGER, effectif INTEGER,
    created_at TEXT, updated_at TEXT, prints INTEGER NOT NULL DEFAULT 1,
    UNIQUE(student_id, annee_id, periode))"""


def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute(_SCHEMA)
    return conn


def _new_code(conn):
    while True:
        raw = "".join(secrets.choice(_ALPHABET) for _ in range(12))
        code = f"BUL-{raw[:4]}-{raw[4:8]}-{raw[8:]}"
        if not conn.execute("SELECT 1 FROM bulletin_codes WHERE code=?", (code,)).fetchone():
            return code


def issue_batch(records):
    """records : liste de dicts (student_id, annee_id, periode, eleve, classe, annee, moyenne, rang, effectif).
    Retourne la liste des numéros dans le même ordre (créés ou réutilisés)."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    codes = []
    with closing(_connect()) as conn:
        with conn:                                          # une seule transaction
            for r in records:
                key = (r["student_id"], r.get("annee_id") or 0, r["periode"])
                row = conn.execute("SELECT code FROM bulletin_codes WHERE student_id=? AND annee_id=? AND periode=?",
                                   key).fetchone()
                vals = (r.get("eleve"), r.get("classe"), r.get("annee"), r.get("moyenne"), r.get("rang"),
                        r.get("effectif"), now)
                if row:
                    conn.execute("""UPDATE bulletin_codes SET eleve=?, classe=?, annee=?, moyenne=?, rang=?,
                                    effectif=?, updated_at=?, prints=prints+1 WHERE code=?""", vals + (row["code"],))
                    codes.append(row["code"])
                else:
                    code = _new_code(conn)
                    conn.execute("""INSERT INTO bulletin_codes (code, student_id, annee_id, periode, eleve, classe,
                                    annee, moyenne, rang, effectif, created_at, updated_at)
                                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                                 (code, *key, *vals[:6], now, now))
                    codes.append(code)
    return codes

def peek_batch(records):
    """Numéros déjà attribués (None si le bulletin n'a jamais été édité), sans rien modifier en base."""
    out = []
    with closing(_connect()) as conn:
        for r in records:
            row = conn.execute("SELECT code FROM bulletin_codes WHERE student_id=? AND annee_id=? AND periode=?",
                               (r["student_id"], r.get("annee_id") or 0, r["periode"])).fetchone()
            out.append(row["code"] if row else None)
    return out


def normalize(text):
    """« bul 7k3f 9qxm 2pwd » -> « BUL-7K3F-9QXM-2PWD » (None si le format est invalide)."""
    raw = re.sub(r"[^A-Za-z0-9]", "", text or "").upper()
    if raw.startswith("BUL"):
        raw = raw[3:]
    return f"BUL-{raw[:4]}-{raw[4:8]}-{raw[8:]}" if len(raw) == 12 else None


def lookup(text):
    """Informations enregistrées pour un numéro, ou None s'il est inconnu."""
    code = normalize(text)
    if not code:
        return None
    with closing(_connect()) as conn:
        row = conn.execute("SELECT * FROM bulletin_codes WHERE code=?", (code,)).fetchone()
    return dict(row) if row else None