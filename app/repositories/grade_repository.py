from app.database.connection import conn, query


def for_subject(subject_id, periode):
    """{student_id: ligne de note} pour une matière et une période."""
    return {g["student_id"]: g for g in query(
        "SELECT * FROM grades WHERE subject_id=? AND periode=?", (subject_id, periode))}


def for_class(class_id, periode):
    return query("SELECT g.* FROM grades g JOIN students s ON s.id=g.student_id "
                 "WHERE s.classe_id=? AND g.periode=?", (class_id, periode))


def save_many(subject_id, periode, data):
    """data : {student_id: (interro, devoir, compo)} ; une ligne entièrement vide est supprimée."""
    for sid, (i, d, c) in data.items():
        if i is None and d is None and c is None:
            conn.execute("DELETE FROM grades WHERE student_id=? AND subject_id=? AND periode=?",
                         (sid, subject_id, periode))
        else:
            conn.execute("""INSERT INTO grades(student_id,subject_id,periode,interro,devoir,compo) VALUES(?,?,?,?,?,?)
                            ON CONFLICT(student_id,subject_id,periode) DO UPDATE SET
                            interro=excluded.interro, devoir=excluded.devoir, compo=excluded.compo""",
                         (sid, subject_id, periode, i, d, c))
    conn.commit()


# -- discipline (apparaît sur le bulletin)
def get_discipline(student_id, periode):
    r = query("SELECT * FROM discipline WHERE student_id=? AND periode=?", (student_id, periode))
    return r[0] if r else None


def save_discipline(student_id, periode, v):
    conn.execute("""INSERT INTO discipline(student_id,periode,absences,sanctions,merites,exclusions)
                    VALUES(?,?,?,?,?,?) ON CONFLICT(student_id,periode) DO UPDATE SET
                    absences=excluded.absences, sanctions=excluded.sanctions,
                    merites=excluded.merites, exclusions=excluded.exclusions""",
                 (student_id, periode, v["absences"], v["sanctions"], v["merites"], v["exclusions"]))
    conn.commit()
