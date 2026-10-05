from app.database.connection import conn, execute, query
from app.utils.formatting import new_matricule


def list_all():
    return query("SELECT id, libelle FROM years ORDER BY libelle DESC")


def label(year_id):
    r = query("SELECT libelle FROM years WHERE id=?", (year_id,))
    return r[0]["libelle"] if r else None


def count_in(table, year_id):
    return query(f"SELECT COUNT(*) FROM {table} WHERE annee_id=?", (year_id,))[0][0]


def create(libelle):
    """Lève sqlite3.IntegrityError si l'année existe déjà."""
    return execute("INSERT INTO years(libelle) VALUES(?)", (libelle,))


def rename(year_id, libelle):
    execute("UPDATE years SET libelle=? WHERE id=?", (libelle, year_id))


def delete(year_id):
    for t in ("schedule", "assignments", "students", "classes", "teachers", "subjects"):
        conn.execute(f"DELETE FROM {t} WHERE annee_id=?", (year_id,))
    conn.execute("DELETE FROM years WHERE id=?", (year_id,))
    conn.commit()


def copy_data(src, yid, base, cls, asg, stu):
    """Copie (selon les options) les données de l'année src vers la nouvelle année yid."""
    smap, tmap, cmap = {}, {}, {}
    if base:
        for s in query("SELECT * FROM subjects WHERE annee_id=?", (src,)):
            smap[s["id"]] = conn.execute("INSERT INTO subjects(nom,coefficient,code,categorie_id,annee_id) VALUES(?,?,?,?,?)",
                                         (s["nom"], s["coefficient"], s["code"], s["categorie_id"], yid)).lastrowid
        for t in query("SELECT * FROM teachers WHERE annee_id=?", (src,)):
            tmap[t["id"]] = conn.execute(
                "INSERT INTO teachers(nom,prenom,email,telephone,heures_sem,annee_id) VALUES(?,?,?,?,?,?)",
                (t["nom"], t["prenom"], t["email"], t["telephone"], t["heures_sem"], yid)).lastrowid
        for ts in query("SELECT * FROM teacher_subjects"):
            if ts["teacher_id"] in tmap and ts["subject_id"] in smap:
                conn.execute("INSERT INTO teacher_subjects(teacher_id,subject_id) VALUES(?,?)",
                             (tmap[ts["teacher_id"]], smap[ts["subject_id"]]))
    if cls:
        for c in query("SELECT * FROM classes WHERE annee_id=?", (src,)):
            cmap[c["id"]] = conn.execute(
                "INSERT INTO classes(nom,niveau,prof_titulaire,titulaire_id,annee_id) VALUES(?,?,?,?,?)",
                (c["nom"], c["niveau"], c["prof_titulaire"], tmap.get(c["titulaire_id"]), yid)).lastrowid
    if asg:
        for a in query("SELECT * FROM assignments WHERE annee_id=?", (src,)):
            if a["class_id"] in cmap and a["subject_id"] in smap:
                conn.execute("INSERT INTO assignments(annee_id,class_id,subject_id,teacher_id,hours) VALUES(?,?,?,?,?)",
                             (yid, cmap[a["class_id"]], smap[a["subject_id"]], tmap.get(a["teacher_id"]), a["hours"]))
    if stu:
        for s in query("SELECT * FROM students WHERE annee_id=?", (src,)):
            sid = conn.execute(
                """INSERT INTO students(nom,prenom,sexe,statut,date_naissance,classe_id,tuteur,telephone,annee_id)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (s["nom"], s["prenom"], s["sexe"], s["statut"], s["date_naissance"], cmap.get(s["classe_id"]),
                 s["tuteur"], s["telephone"], yid)).lastrowid
            conn.execute("UPDATE students SET matricule=? WHERE id=?", (new_matricule(sid), sid))
    conn.commit()
