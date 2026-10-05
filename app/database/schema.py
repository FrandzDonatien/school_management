"""Définition du schéma SQLite."""
from app.database.connection import conn

DDL_CATEGORIES = """CREATE TABLE IF NOT EXISTS categories(
    id INTEGER PRIMARY KEY, nom TEXT NOT NULL UNIQUE, titre TEXT DEFAULT '', ordre INTEGER NOT NULL DEFAULT 0)"""
DDL_SUBJECTS = """CREATE TABLE {name}(
    id INTEGER PRIMARY KEY, nom TEXT NOT NULL, coefficient REAL NOT NULL DEFAULT 1, code TEXT DEFAULT '',
    categorie_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    annee_id INTEGER REFERENCES years(id) ON DELETE CASCADE, UNIQUE(annee_id, nom))"""
DDL_CLASSES = """CREATE TABLE {name}(
    id INTEGER PRIMARY KEY, nom TEXT NOT NULL, niveau TEXT, prof_titulaire TEXT DEFAULT '',
    titulaire_id INTEGER REFERENCES teachers(id) ON DELETE SET NULL,
    annee_id INTEGER REFERENCES years(id) ON DELETE CASCADE, UNIQUE(annee_id, nom))"""
DDL_SCHEDULE = """CREATE TABLE {name}(
    id INTEGER PRIMARY KEY, annee_id INTEGER REFERENCES years(id) ON DELETE CASCADE,
    teacher_id INTEGER REFERENCES teachers(id) ON DELETE CASCADE,
    class_id INTEGER REFERENCES classes(id) ON DELETE CASCADE, day INTEGER, slot INTEGER,
    subject_id INTEGER REFERENCES subjects(id) ON DELETE CASCADE,
    UNIQUE(annee_id, teacher_id, day, slot), UNIQUE(class_id, day, slot))"""
DDL_ASSIGN = """CREATE TABLE IF NOT EXISTS assignments(
    id INTEGER PRIMARY KEY, annee_id INTEGER REFERENCES years(id) ON DELETE CASCADE,
    class_id INTEGER REFERENCES classes(id) ON DELETE CASCADE,
    subject_id INTEGER REFERENCES subjects(id) ON DELETE CASCADE,
    teacher_id INTEGER REFERENCES teachers(id) ON DELETE SET NULL,
    hours INTEGER NOT NULL DEFAULT 0, UNIQUE(class_id, subject_id))"""
DDL_TEACHER_SUBJECTS = """CREATE TABLE IF NOT EXISTS teacher_subjects(
        teacher_id INTEGER REFERENCES teachers(id) ON DELETE CASCADE,
        subject_id INTEGER REFERENCES subjects(id) ON DELETE CASCADE,
        PRIMARY KEY(teacher_id, subject_id))"""
DDL_GRADES = """CREATE TABLE IF NOT EXISTS grades(
        id INTEGER PRIMARY KEY, student_id INTEGER REFERENCES students(id) ON DELETE CASCADE,
        subject_id INTEGER REFERENCES subjects(id) ON DELETE CASCADE, periode TEXT,
        interro REAL, devoir REAL, compo REAL, UNIQUE(student_id, subject_id, periode))"""


def create_tables():
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT);
    CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
    CREATE TABLE IF NOT EXISTS years(id INTEGER PRIMARY KEY, libelle TEXT UNIQUE NOT NULL);
    CREATE TABLE IF NOT EXISTS students(
        id INTEGER PRIMARY KEY, matricule TEXT DEFAULT '', nom TEXT NOT NULL, prenom TEXT NOT NULL,
        sexe TEXT, date_naissance TEXT, classe_id INTEGER REFERENCES classes(id) ON DELETE SET NULL,
        tuteur TEXT, telephone TEXT);
    CREATE TABLE IF NOT EXISTS teachers(
        id INTEGER PRIMARY KEY, nom TEXT NOT NULL, prenom TEXT NOT NULL DEFAULT '', email TEXT, telephone TEXT,
        matiere_id INTEGER);
    CREATE TABLE IF NOT EXISTS discipline(
        student_id INTEGER REFERENCES students(id) ON DELETE CASCADE, periode TEXT,
        absences TEXT, sanctions TEXT, merites TEXT, exclusions TEXT, PRIMARY KEY(student_id, periode));
    """)
    conn.execute(DDL_CATEGORIES)
    conn.execute(DDL_SUBJECTS.format(name="IF NOT EXISTS subjects"))
    conn.execute(DDL_CLASSES.format(name="IF NOT EXISTS classes"))
    conn.execute(DDL_SCHEDULE.format(name="IF NOT EXISTS schedule"))
    conn.execute(DDL_ASSIGN)
    conn.commit()