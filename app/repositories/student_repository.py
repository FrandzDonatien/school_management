from app.database.connection import conn, execute, query
from app.models.student import Student

# Paramètres : (année, classe, classe) ; classe = None -> toutes les classes
LIST_SQL = """SELECT s.id, s.matricule, s.nom, s.prenom, s.sexe, s.statut, s.date_naissance,
             COALESCE(c.nom,''), s.tuteur, s.telephone FROM students s
             LEFT JOIN classes c ON c.id=s.classe_id WHERE s.annee_id=? AND (? IS NULL OR s.classe_id=?)
             ORDER BY s.nom, s.prenom"""


def get(sid):
    r = query("SELECT * FROM students WHERE id=?", (sid,))
    return Student.from_row(r[0]) if r else None


def ids_by_class(cid):
    return query("SELECT id FROM students WHERE classe_id=? ORDER BY nom,prenom", (cid,))


def names_by_class(cid):
    return query("SELECT id,nom,prenom FROM students WHERE classe_id=? ORDER BY nom,prenom", (cid,))


def count(year):
    return query("SELECT COUNT(*) FROM students WHERE annee_id=?", (year,))[0][0]


def recent(year, limit=50):
    return query("SELECT s.id, s.nom, s.prenom, COALESCE(c.nom,''), s.matricule FROM students s "
                 "LEFT JOIN classes c ON c.id=s.classe_id WHERE s.annee_id=? ORDER BY s.id DESC LIMIT ?",
                 (year, limit))


def count_by_sexe(year):
    return query("SELECT COALESCE(NULLIF(sexe,''),'Non précisé'), COUNT(*) FROM students WHERE annee_id=? "
                 "GROUP BY 1 ORDER BY 1", (year,))


def count_by_statut(year):
    return query("SELECT COALESCE(NULLIF(statut,''),'Nouveau'), COUNT(*) FROM students WHERE annee_id=? "
                 "GROUP BY 1 ORDER BY 1", (year,))


def known_keys(year):
    """Clés (nom, prénom, naissance) des élèves existants, pour éviter les doublons à l'import."""
    return {(r["nom"].lower(), r["prenom"].lower(), r["date_naissance"] or "") for r in query(
        "SELECT nom,prenom,date_naissance FROM students WHERE annee_id=?", (year,))}


def create(v, year, commit=True):
    sid = conn.execute("""INSERT INTO students(nom,prenom,sexe,statut,date_naissance,classe_id,tuteur,telephone,annee_id)
                          VALUES(?,?,?,?,?,?,?,?,?)""",
                       (v["nom"], v["prenom"], v["sexe"], v["statut"], v["date_naissance"], v["classe_id"],
                        v["tuteur"], v["telephone"], year)).lastrowid
    if commit:
        conn.commit()
    return sid


def set_matricule(sid, matricule, commit=True):
    conn.execute("UPDATE students SET matricule=? WHERE id=?", (matricule, sid))
    if commit:
        conn.commit()