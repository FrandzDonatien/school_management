from app.database.connection import conn, query
from app.models.teacher import Teacher
from app.utils.formatting import person

LIST_SQL = """SELECT t.id, t.nom, t.prenom,
                 COALESCE((SELECT group_concat(COALESCE(NULLIF(s.code,''), s.nom), ', ') FROM teacher_subjects ts
                           JOIN subjects s ON s.id=ts.subject_id WHERE ts.teacher_id=t.id), ''),
                 COALESCE((SELECT SUM(hours) FROM assignments WHERE teacher_id=t.id), 0),
                 CAST(COALESCE(t.heures_sem, ?) AS INTEGER), t.email, t.telephone
                 FROM teachers t WHERE t.annee_id=? ORDER BY t.nom"""


def get(tid):
    r = query("SELECT * FROM teachers WHERE id=?", (tid,))
    return Teacher.from_row(r[0]) if r else None


def options(year):
    return {person(r["nom"], r["prenom"]): r["id"] for r in query(
        "SELECT id,nom,prenom FROM teachers WHERE annee_id=? ORDER BY nom", (year,))}


def names(year):
    return {r["id"]: person(r["nom"], r["prenom"]) for r in query(
        "SELECT id,nom,prenom FROM teachers WHERE annee_id=?", (year,))}


def count(year):
    return query("SELECT COUNT(*) FROM teachers WHERE annee_id=?", (year,))[0][0]


def target_hours(tid):
    """Valeur de la fiche (None si non renseignée)."""
    r = query("SELECT heures_sem FROM teachers WHERE id=?", (tid,))
    return r[0]["heures_sem"] if r else None


def targets(year, default):
    return {r["id"]: (int(r["heures_sem"]) if r["heures_sem"] else default) for r in query(
        "SELECT id, heures_sem FROM teachers WHERE annee_id=?", (year,))}


def subjects_of(tid):
    return query("""SELECT s.id, s.nom, s.code FROM teacher_subjects ts JOIN subjects s ON s.id=ts.subject_id
                    WHERE ts.teacher_id=? ORDER BY s.nom""", (tid,))


def subject_ids(tid):
    return {r[0] for r in query("SELECT subject_id FROM teacher_subjects WHERE teacher_id=?", (tid,))}


def set_subjects(tid, subject_ids_):
    conn.execute("DELETE FROM teacher_subjects WHERE teacher_id=?", (tid,))
    conn.executemany("INSERT INTO teacher_subjects(teacher_id,subject_id) VALUES(?,?)",
                     [(tid, s) for s in subject_ids_])
    # une matière décochée retire les affectations correspondantes
    conn.execute("""DELETE FROM assignments WHERE teacher_id=? AND subject_id NOT IN
                    (SELECT subject_id FROM teacher_subjects WHERE teacher_id=?)""", (tid, tid))
    conn.commit()


def hours_per_teacher(year, limit=8):
    return query("SELECT TRIM(t.nom||' '||t.prenom), SUM(a.hours) FROM assignments a JOIN teachers t ON t.id=a.teacher_id "
                 "WHERE a.annee_id=? GROUP BY t.id ORDER BY 2 DESC LIMIT ?", (year, limit))
