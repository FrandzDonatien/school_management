from app.database.connection import conn, execute, query


# -- affectations (enseignant -> classe/matière/heures)
def assignments_view(year):
    return query("""SELECT a.id, c.nom, s.nom, COALESCE(TRIM(t.nom||' '||t.prenom), 'Non attribué'), a.hours
                    FROM assignments a JOIN classes c ON c.id=a.class_id JOIN subjects s ON s.id=a.subject_id
                    LEFT JOIN teachers t ON t.id=a.teacher_id WHERE a.annee_id=? AND a.hours>0
                    ORDER BY c.nom, s.nom""", (year,))


def assignments_map(year):
    return {(a["class_id"], a["subject_id"]): a for a in query(
        """SELECT a.class_id, a.subject_id, a.teacher_id, a.hours, TRIM(t.nom||' '||t.prenom) AS tname
           FROM assignments a LEFT JOIN teachers t ON t.id=a.teacher_id WHERE a.annee_id=?""", (year,))}


def assignment_rows(year, class_ids):
    marks = ",".join("?" * len(class_ids))
    return query(f"""SELECT class_id, subject_id, teacher_id, hours FROM assignments
                     WHERE annee_id=? AND hours>0 AND class_id IN ({marks})""", (year, *class_ids))


def teacher_totals(year):
    return {r["teacher_id"]: r["h"] for r in query(
        "SELECT teacher_id, SUM(hours) AS h FROM assignments WHERE annee_id=? AND teacher_id IS NOT NULL "
        "GROUP BY teacher_id", (year,))}


def is_taken_by_other(class_id, subject_id, teacher_id):
    return bool(query("SELECT 1 FROM assignments WHERE class_id=? AND subject_id=? AND hours>0 "
                      "AND teacher_id IS NOT NULL AND teacher_id<>?", (class_id, subject_id, teacher_id)))


def save_assignments(year, teacher_id, data):
    """data : {(class_id, subject_id): heures}. 0 h = retrait de l'affectation de cet enseignant."""
    for (cid, sid), h in data.items():
        if h:
            conn.execute("""INSERT INTO assignments(annee_id,class_id,subject_id,teacher_id,hours) VALUES(?,?,?,?,?)
                            ON CONFLICT(class_id,subject_id) DO UPDATE SET teacher_id=excluded.teacher_id,
                            hours=excluded.hours""", (year, cid, sid, teacher_id, h))
        else:
            conn.execute("DELETE FROM assignments WHERE class_id=? AND subject_id=? AND teacher_id=?",
                         (cid, sid, teacher_id))
    conn.commit()


def hours_needed(year):
    return query("SELECT COALESCE(SUM(hours),0) FROM assignments WHERE annee_id=?", (year,))[0][0]


def teacher_name(class_id, subject_id):
    r = query("""SELECT TRIM(t.nom||' '||t.prenom) AS n FROM assignments a JOIN teachers t ON t.id=a.teacher_id
                 WHERE a.class_id=? AND a.subject_id=?""", (class_id, subject_id))
    if r:
        return r[0]["n"]
    r = query("""SELECT TRIM(t.nom||' '||t.prenom) AS n FROM schedule sc JOIN teachers t ON t.id=sc.teacher_id
                 WHERE sc.class_id=? AND sc.subject_id=? LIMIT 1""", (class_id, subject_id))
    return r[0]["n"] if r else ""


def load_rows(default_hours, year):
    return query("""SELECT t.id, TRIM(t.nom||' '||t.prenom) AS n,
                    COALESCE((SELECT group_concat(COALESCE(NULLIF(s.code,''), s.nom), ', ') FROM teacher_subjects ts
                              JOIN subjects s ON s.id=ts.subject_id WHERE ts.teacher_id=t.id), '') AS subs,
                    CAST(COALESCE(t.heures_sem, ?) AS INTEGER) AS target,
                    COALESCE((SELECT SUM(hours) FROM assignments WHERE teacher_id=t.id AND annee_id=?),0) AS need,
                    (SELECT COUNT(*) FROM schedule WHERE teacher_id=t.id AND annee_id=?) AS placed
                    FROM teachers t WHERE t.annee_id=? ORDER BY t.nom""", (default_hours, year, year, year))


# -- emploi du temps
def placed_count(year):
    return query("SELECT COUNT(*) FROM schedule WHERE annee_id=?", (year,))[0][0]


def count_in(year, class_ids):
    marks = ",".join("?" * len(class_ids))
    return query(f"SELECT COUNT(*) FROM schedule WHERE annee_id=? AND class_id IN ({marks})", (year, *class_ids))[0][0]


def fixed_slots(year, excluded_class_ids):
    """Créneaux déjà occupés par les enseignants dans les classes qu'on ne régénère pas."""
    marks = ",".join("?" * len(excluded_class_ids))
    return [(r["teacher_id"], r["day"], r["slot"]) for r in query(
        f"""SELECT teacher_id, day, slot FROM schedule WHERE annee_id=? AND teacher_id IS NOT NULL
            AND class_id NOT IN ({marks})""", (year, *excluded_class_ids))]


def cells(mode, ident, year):
    col = "sc.class_id" if mode == "c" else "sc.teacher_id"
    return query(f"""SELECT sc.day, sc.slot, sc.class_id AS cid, c.nom AS cname, s.id AS sid, s.nom AS sname,
                     s.code AS scode, TRIM(t.nom||' '||t.prenom) AS tname
                     FROM schedule sc JOIN classes c ON c.id=sc.class_id
                     LEFT JOIN subjects s ON s.id=sc.subject_id LEFT JOIN teachers t ON t.id=sc.teacher_id
                     WHERE {col}=? AND sc.annee_id=?""", (ident, year))


def replace_schedule(year, class_ids, rows):
    """rows : [(annee, teacher_id, class_id, subject_id, day, slot)]."""
    marks = ",".join("?" * len(class_ids))
    conn.execute(f"DELETE FROM schedule WHERE annee_id=? AND class_id IN ({marks})", (year, *class_ids))
    conn.executemany("INSERT INTO schedule(annee_id,teacher_id,class_id,subject_id,day,slot) VALUES(?,?,?,?,?,?)", rows)
    conn.commit()


def clear(year, class_ids):
    marks = ",".join("?" * len(class_ids))
    execute(f"DELETE FROM schedule WHERE annee_id=? AND class_id IN ({marks})", (year, *class_ids))


def clear_all():
    execute("DELETE FROM schedule")


def any_schedule():
    return bool(query("SELECT 1 FROM schedule LIMIT 1"))
