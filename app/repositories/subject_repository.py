from app.database.connection import query

LIST_SQL = """SELECT s.id, s.nom, s.code, COALESCE(c.nom,''), s.coefficient FROM subjects s
              LEFT JOIN categories c ON c.id=s.categorie_id WHERE s.annee_id=?
              ORDER BY COALESCE(c.ordre, 9999), s.nom"""


def by_year(year):
    """Matières triées par catégorie puis par nom (avec categorie, categorie_titre, cat_ordre)."""
    return query("""SELECT s.*, c.nom AS categorie, c.titre AS categorie_titre, COALESCE(c.ordre, 9999) AS cat_ordre
                    FROM subjects s LEFT JOIN categories c ON c.id=s.categorie_id
                    WHERE s.annee_id=? ORDER BY cat_ordre, s.nom""", (year,))


def options(year):
    return {r["nom"]: r["id"] for r in by_year(year)}


def count(year):
    return query("SELECT COUNT(*) FROM subjects WHERE annee_id=?", (year,))[0][0]