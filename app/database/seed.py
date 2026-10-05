"""Données initiales et exemple de l'établissement."""
from app.database.connection import conn, execute, query
from app.database.queries import active_year, cur_year
from app.constants import DEFAULT_ADMIN
from app.utils.security import hash_pw

# Données d'exemple issues des documents de l'établissement (répartition des tâches + emplois du temps)
EX_SUBJECTS = [("MATHS", "Mathématiques", 4), ("FR", "Français", 4), ("ANG", "Anglais", 2),
               ("PCT", "Physique-Chimie", 3), ("SVT", "SVT", 2), ("HG", "Histoire-Géographie", 2),
               ("ECM", "Éducation Civique et Morale", 1), ("EPS", "EPS", 1)]
EX_CLASSES = ["6ème A", "6ème B", "5ème", "4ème A", "4ème B", "3ème"]
EX_TEACHERS = ["AMAKOU", "AMEDODJI", "AOUTA", "BAHON", "ODAH", "SAMIE", "TCHAKOURE", "ADENTA"]
EX_REP = {  # matière -> enseignant de chaque classe (ordre EX_CLASSES)
    "FR": "ADENTA AOUTA BAHON BAHON AOUTA ADENTA".split(),
    "HG": "AOUTA BAHON ADENTA ADENTA BAHON AOUTA".split(),
    "ECM": "BAHON ADENTA AOUTA AOUTA ADENTA BAHON".split(),
    "ANG": ["AMAKOU"] * 6,
    "SVT": ["SAMIE"] * 6,
    "PCT": "AMEDODJI AMEDODJI TCHAKOURE TCHAKOURE SAMIE TCHAKOURE".split(),
    "MATHS": "TCHAKOURE AMEDODJI AMEDODJI AMEDODJI TCHAKOURE AMEDODJI".split(),
    "EPS": ["ODAH"] * 6,
}
_H6 = dict(ANG=4, FR=6, SVT=2, ECM=2, MATHS=4, HG=2, PCT=3, EPS=2)
EX_HOURS = {  # volume horaire hebdomadaire par classe et matière
    "6ème A": _H6, "6ème B": _H6, "5ème": _H6,
    "4ème A": dict(FR=6, SVT=3, ANG=4, HG=2, PCT=5, EPS=2, MATHS=4, ECM=2),
    "4ème B": dict(FR=6, SVT=3, ANG=4, HG=2, PCT=5, EPS=2, MATHS=4, ECM=2),
    "3ème": dict(FR=6, SVT=4, ANG=4, HG=3, PCT=5, EPS=2, MATHS=4, ECM=2),
}
# Catégories de matières par défaut (nom, titre affiché sur le bulletin) et rattachement des matières de l'exemple
DEFAULT_CATEGORIES = [("Littéraire", "Matières littéraires"), ("Scientifique", "Matières scientifiques"),
                      ("Optionnelle", "Matières optionnelles")]
EX_CATEGORY_OF = {"FR": "Littéraire", "ANG": "Littéraire", "HG": "Littéraire", "ECM": "Littéraire",
                  "MATHS": "Scientifique", "PCT": "Scientifique", "SVT": "Scientifique", "EPS": "Optionnelle"}
EX_TITULAIRES = dict(zip(EX_CLASSES, "TCHAKOURE AOUTA BAHON AMEDODJI SAMIE ADENTA".split()))


def assign_default_categories(year=None):
    """Rattache aux catégories par défaut les matières (connues par leur abréviation) sans catégorie."""
    ids = {r["nom"]: r["id"] for r in query("SELECT id,nom FROM categories")}
    for code, cat in EX_CATEGORY_OF.items():
        if cat not in ids:
            continue
        sql, params = "UPDATE subjects SET categorie_id=? WHERE categorie_id IS NULL AND UPPER(code)=?", [ids[cat], code]
        if year:
            sql, params = sql + " AND annee_id=?", params + [year]
        conn.execute(sql, params)
    conn.commit()


def seed_categories():
    if not query("SELECT 1 FROM categories"):
        for i, (nom, titre) in enumerate(DEFAULT_CATEGORIES, 1):
            conn.execute("INSERT INTO categories(nom,titre,ordre) VALUES(?,?,?)", (nom, titre, i))
        conn.commit()
    if not query("SELECT 1 FROM settings WHERE key='cat_migrated'"):  # reprise des anciennes matières (une fois)
        assign_default_categories()
        execute("INSERT INTO settings(key,value) VALUES('cat_migrated','1')")


def seed_defaults():
    """Compte administrateur et matières par défaut (uniquement si les tables sont vides)."""
    if not query("SELECT 1 FROM users"):
        execute("INSERT INTO users(username,password) VALUES(?,?)", (DEFAULT_ADMIN[0], hash_pw(DEFAULT_ADMIN[1])))
    if not query("SELECT 1 FROM subjects"):
        yid = active_year()
        for code, n, c in EX_SUBJECTS:
            execute("INSERT INTO subjects(nom,coefficient,code,annee_id) VALUES(?,?,?,?)", (n, c, code, yid))
    seed_categories()


def load_example_data(y=None):
    """Ajoute à l'année y les matières, enseignants, classes, titulaires et affectations de l'exemple."""
    y = y or cur_year()
    sid, tid, cid = {}, {}, {}
    for code, nom, coef in EX_SUBJECTS:
        r = query("SELECT id,code FROM subjects WHERE annee_id=? AND (UPPER(code)=? OR LOWER(nom)=?)",
                  (y, code, nom.lower()))
        if r:
            sid[code] = r[0]["id"]
        else:
            sid[code] = conn.execute("INSERT INTO subjects(nom,coefficient,code,annee_id) VALUES(?,?,?,?)",
                                     (nom, coef, code, y)).lastrowid
    assign_default_categories(y)
    for nm in EX_TEACHERS:
        r = query("SELECT id FROM teachers WHERE annee_id=? AND UPPER(nom)=?", (y, nm))
        tid[nm] = r[0]["id"] if r else conn.execute(
            "INSERT INTO teachers(nom,prenom,annee_id) VALUES(?,?,?)", (nm, "", y)).lastrowid
    for nm in EX_CLASSES:
        r = query("SELECT id FROM classes WHERE annee_id=? AND nom=?", (y, nm))
        cid[nm] = r[0]["id"] if r else conn.execute(
            "INSERT INTO classes(nom,niveau,annee_id) VALUES(?,?,?)", (nm, nm.split()[0], y)).lastrowid
    for code, tl in EX_REP.items():
        for cname, tname in zip(EX_CLASSES, tl):
            conn.execute("""INSERT INTO assignments(annee_id,class_id,subject_id,teacher_id,hours) VALUES(?,?,?,?,?)
                            ON CONFLICT(class_id,subject_id) DO UPDATE SET teacher_id=excluded.teacher_id,
                            hours=excluded.hours""", (y, cid[cname], sid[code], tid[tname], EX_HOURS[cname].get(code, 0)))
            conn.execute("INSERT OR IGNORE INTO teacher_subjects(teacher_id,subject_id) VALUES(?,?)",
                         (tid[tname], sid[code]))
    for cname, tname in EX_TITULAIRES.items():
        conn.execute("UPDATE classes SET titulaire_id=? WHERE id=?", (tid[tname], cid[cname]))
    conn.commit()