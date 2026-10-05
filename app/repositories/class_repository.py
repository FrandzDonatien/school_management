from app.database.connection import conn, query
from app.models.class_room import ClassRoom

LIST_SQL = """SELECT c.id, c.nom, c.niveau, COALESCE(TRIM(t.nom||' '||t.prenom), ''), COUNT(s.id) FROM classes c
             LEFT JOIN teachers t ON t.id=c.titulaire_id
             LEFT JOIN students s ON s.classe_id=c.id WHERE c.annee_id=? GROUP BY c.id ORDER BY c.nom"""


def get(cid):
    r = query("SELECT * FROM classes WHERE id=?", (cid,))
    return ClassRoom.from_row(r[0]) if r else None


def by_year(year):
    return query("SELECT id,nom FROM classes WHERE annee_id=? ORDER BY nom", (year,))


def options(year):
    return {r["nom"]: r["id"] for r in by_year(year)}


def ids(year):
    return [r["id"] for r in query("SELECT id FROM classes WHERE annee_id=?", (year,))]


def count(year):
    return query("SELECT COUNT(*) FROM classes WHERE annee_id=?", (year,))[0][0]


def students_per_class(year):
    return query("SELECT c.nom, COUNT(s.id) FROM classes c LEFT JOIN students s ON s.classe_id=c.id "
                 "WHERE c.annee_id=? GROUP BY c.id ORDER BY c.nom", (year,))


def students_per_level(year):
    return query("SELECT COALESCE(NULLIF(c.niveau,''),c.nom), COUNT(s.id) FROM classes c "
                 "LEFT JOIN students s ON s.classe_id=c.id WHERE c.annee_id=? GROUP BY 1 ORDER BY 1", (year,))


def create(nom, niveau, year, commit=True):
    cid = conn.execute("INSERT INTO classes(nom,niveau,annee_id) VALUES(?,?,?)", (nom, niveau, year)).lastrowid
    if commit:
        conn.commit()
    return cid
