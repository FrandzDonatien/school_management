"""Migrations depuis les anciennes versions + point d'entrée init_db()."""
from app.constants import DAYS, DEFAULT_CODES, SLOTS
from app.database.connection import conn, execute, query
from app.database.queries import active_year
from app.database.schema import (DDL_CLASSES, DDL_GRADES, DDL_SCHEDULE, DDL_SUBJECTS, DDL_TEACHER_SUBJECTS,
                                 create_tables)
from app.database.seed import seed_defaults
from app.services.settings_service import default_settings, load_plan, set_setting
from app.utils.formatting import abbr


def add_col(table, col, ddl):
    if col not in [r["name"] for r in query(f"PRAGMA table_info({table})")]:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
        conn.commit()


def table_sql(name):
    r = query("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return r[0]["sql"] if r else ""


def rebuild(table, ddl, cols):
    """Reconstruit une table (changement de contraintes) en conservant les données."""
    conn.commit()
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.executescript(
        f"BEGIN; {ddl.format(name=table + '_new')}; "
        f"INSERT INTO {table}_new({cols}) SELECT {cols} FROM {table}; "
        f"DROP TABLE {table}; ALTER TABLE {table}_new RENAME TO {table}; COMMIT;")
    conn.execute("PRAGMA foreign_keys = ON")


def run_migrations():
    add_col("subjects", "categorie_id", "INTEGER REFERENCES categories(id) ON DELETE SET NULL")
    add_col("students", "statut", "TEXT DEFAULT 'Nouveau'")
    add_col("students", "annee_id", "INTEGER")
    add_col("teachers", "jour_repos", "TEXT DEFAULT 'Automatique'")  # conservé en base, n'est plus utilisé
    add_col("teachers", "annee_id", "INTEGER")
    add_col("classes", "prof_titulaire", "TEXT DEFAULT ''")
    add_col("classes", "titulaire_id", "INTEGER REFERENCES teachers(id) ON DELETE SET NULL")
    if "annee_id" not in table_sql("classes"):
        rebuild("classes", DDL_CLASSES, "id,nom,niveau,prof_titulaire")
    if "annee_id" not in table_sql("subjects"):
        rebuild("subjects", DDL_SUBJECTS, "id,nom,coefficient")
    if "annee_id" not in table_sql("schedule"):
        rebuild("schedule", DDL_SCHEDULE, "id,teacher_id,class_id,day,slot")
    add_col("schedule", "subject_id", "INTEGER REFERENCES subjects(id) ON DELETE CASCADE")
    add_col("subjects", "code", "TEXT DEFAULT ''")
    add_col("teachers", "heures_sem", "REAL")
    conn.execute(DDL_TEACHER_SUBJECTS)
    if query("PRAGMA table_info(grades)") and "interro" not in [r["name"] for r in query("PRAGMA table_info(grades)")]:
        conn.execute("DROP TABLE grades")  # ancien format (une seule note)
    conn.execute(DDL_GRADES)
    conn.commit()

    # Années scolaires
    if not query("SELECT 1 FROM years"):
        old = query("SELECT value FROM settings WHERE key='annee'")
        lab = old[0]["value"] if old and old[0]["value"] else default_settings()["annee"]
        yid = execute("INSERT INTO years(libelle) VALUES(?)", (lab,))
        set_setting("annee_id", str(yid))
    yid = active_year()
    for t in ("classes", "students", "teachers", "subjects", "schedule"):
        conn.execute(f"UPDATE {t} SET annee_id=? WHERE annee_id IS NULL", (yid,))
    # Professeur titulaire : ancien champ texte -> liste des enseignants
    conn.execute("""UPDATE classes SET titulaire_id=(SELECT t.id FROM teachers t WHERE t.annee_id=classes.annee_id
                    AND (TRIM(t.nom||' '||t.prenom)=classes.prof_titulaire OR t.nom=classes.prof_titulaire) LIMIT 1)
                    WHERE titulaire_id IS NULL AND COALESCE(prof_titulaire,'')<>''""")
    # Emploi du temps : matière de chaque cours (anciennes versions : matière de l'enseignant)
    conn.execute("""UPDATE schedule SET subject_id=(SELECT matiere_id FROM teachers WHERE id=schedule.teacher_id)
                    WHERE subject_id IS NULL""")
    for r in query("SELECT id,nom FROM subjects WHERE COALESCE(code,'')=''"):
        conn.execute("UPDATE subjects SET code=? WHERE id=?",
                     (DEFAULT_CODES.get(r["nom"].lower(), abbr(r["nom"])), r["id"]))
    # Matières des enseignants : reprise des anciennes affectations (une seule fois)
    if not query("SELECT 1 FROM settings WHERE key='ts_migrated'"):
        conn.execute("""INSERT OR IGNORE INTO teacher_subjects(teacher_id,subject_id)
                        SELECT DISTINCT teacher_id, subject_id FROM assignments WHERE teacher_id IS NOT NULL""")
        conn.execute("""INSERT OR IGNORE INTO teacher_subjects(teacher_id,subject_id)
                        SELECT id, matiere_id FROM teachers WHERE matiere_id IN (SELECT id FROM subjects)""")
        set_setting("ts_migrated", "1")
    conn.commit()
    load_plan()
    conn.execute("DELETE FROM schedule WHERE day >= ? OR slot >= ?", (len(DAYS), len(SLOTS)))
    conn.commit()


def init_db():
    """Crée le schéma, applique les migrations puis insère les données par défaut."""
    create_tables()
    run_migrations()
    seed_defaults()
