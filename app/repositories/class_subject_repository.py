"""Matières enseignées dans chaque classe, avec un coefficient propre à la classe.

Principe :
  - la page « Matières » reste le catalogue de l'année (nom, abréviation, catégorie, coefficient PAR DÉFAUT) ;
  - une classe SANS configuration utilise toutes les matières du catalogue avec leur coefficient par défaut
    (comportement d'avant : rien à migrer) ;
  - une classe PERSONNALISÉE n'utilise que les matières cochées, chacune avec le coefficient saisi pour elle.

Il utilise la connexion de l'application (app.database.connection) et crée sa table au premier usage.
"""
from app.database.connection import conn, query

_SCHEMA = """CREATE TABLE IF NOT EXISTS class_subjects (
    class_id INTEGER NOT NULL, subject_id INTEGER NOT NULL, coefficient REAL NOT NULL,
    PRIMARY KEY (class_id, subject_id))"""

_CATALOG_SQL = """SELECT s.*, c.nom AS categorie, c.titre AS categorie_titre, COALESCE(c.ordre, 9999) AS cat_ordre
                  FROM subjects s LEFT JOIN categories c ON c.id=s.categorie_id
                  WHERE s.annee_id=? ORDER BY cat_ordre, s.nom"""


_ready = False


def _ensure():
    global _ready
    if not _ready:
        conn.execute(_SCHEMA)
        conn.commit()
        _ready = True


def assignments(class_id):
    """{subject_id: coefficient} de la classe ; vide si la classe n'est pas personnalisée."""
    _ensure()
    return {r["subject_id"]: r["coefficient"]
            for r in query("SELECT subject_id, coefficient FROM class_subjects WHERE class_id=?", (class_id,))}


def is_configured(class_id):
    return bool(assignments(class_id))


def for_class(class_id, year):
    """Matières de la classe, triées par catégorie puis par nom, au même format que subject_repository.by_year
    (le champ « coefficient » est celui de la classe)."""
    coefs = assignments(class_id)
    catalog = [dict(r) for r in query(_CATALOG_SQL, (year,))]
    if not coefs:
        return catalog
    out = []
    for s in catalog:
        if s["id"] in coefs:
            s["coefficient"] = coefs[s["id"]]
            out.append(s)
    return out


def options(class_id, year):
    """{nom de la matière: id} pour les listes déroulantes d'une classe."""
    return {s["nom"]: s["id"] for s in for_class(class_id, year)}


def save(class_id, mapping):
    """Personnalise la classe. mapping : {subject_id: coefficient} (remplace la configuration précédente)."""
    _ensure()
    try:
        conn.execute("DELETE FROM class_subjects WHERE class_id=?", (class_id,))
        conn.executemany("INSERT INTO class_subjects (class_id, subject_id, coefficient) VALUES (?,?,?)",
                         [(class_id, sid, float(c)) for sid, c in mapping.items()])
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def reset(class_id):
    """Revient au comportement par défaut (toutes les matières du catalogue, coefficient par défaut)."""
    _ensure()
    conn.execute("DELETE FROM class_subjects WHERE class_id=?", (class_id,))
    conn.commit()