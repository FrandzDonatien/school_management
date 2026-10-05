from collections import defaultdict

from app.calculations.grades import student_result
from app.calculations.rankings import rank_categories, rank_students, rank_subjects
from app.calculations.statistics import class_stats
from app.database.queries import cur_year
from app.repositories import class_repository, grade_repository, student_repository, subject_repository


def compute_class(cid, per):
    """-> (résultats {student_id: {...}}, matières, statistiques de la classe)."""
    cl = class_repository.get(cid)
    y = cl.annee_id if cl else cur_year()
    studs = student_repository.ids_by_class(cid)
    subs = subject_repository.by_year(y)
    by_student = defaultdict(dict)
    for g in grade_repository.for_class(cid, per):
        by_student[g["student_id"]][g["subject_id"]] = g
    res = {st["id"]: student_result(subs, by_student.get(st["id"], {})) for st in studs}
    rank_subjects(res, subs)
    rank_categories(res)
    rank_students(res)
    return res, subs, class_stats(res, len(studs))


def save_grades(subject_id, periode, data):
    grade_repository.save_many(subject_id, periode, data)


def get_discipline(student_id, periode):
    return grade_repository.get_discipline(student_id, periode)


def save_discipline(student_id, periode, values):
    grade_repository.save_discipline(student_id, periode, values)