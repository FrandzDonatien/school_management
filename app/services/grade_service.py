from collections import defaultdict

from app.calculations.grades import student_result
from app.calculations.rankings import rank_categories, rank_students, rank_subjects
from app.calculations.statistics import class_stats
from app.constants import PERIODES
from app.database.queries import cur_year
from app.repositories import class_repository, class_subject_repository, grade_repository, student_repository


def compute_class(cid, per):
    """-> (résultats {student_id: {...}}, matières de la classe, statistiques de la classe)."""
    cl = class_repository.get(cid)
    y = cl.annee_id if cl else cur_year()
    studs = student_repository.ids_by_class(cid)
    subs = class_subject_repository.for_class(cid, y)       # matières et coefficients propres à la classe
    by_student = defaultdict(dict)
    for g in grade_repository.for_class(cid, per):
        by_student[g["student_id"]][g["subject_id"]] = g
    res = {st["id"]: student_result(subs, by_student.get(st["id"], {})) for st in studs}
    rank_subjects(res, subs)
    rank_categories(res)
    rank_students(res)
    return res, subs, class_stats(res, len(studs))


def _mean(values):
    v = [x for x in values if x is not None]
    return sum(v) / len(v) if v else None


def compute_recap(cid, per, current=None):
    """Récapitulatif des périodes précédentes + moyenne annuelle (uniquement à la dernière période).

    `current` : résultats déjà calculés de la période `per` (évite de les recalculer).
    -> (prev, annual)
       prev   : [(periode, res)] pour les périodes avant `per`
       annual : {student_id: {"moy", "rang", "subjects": {subject_id: moyenne annuelle}}} ou None
    """
    idx = PERIODES.index(per)
    prev = [(p, compute_class(cid, p)[0]) for p in PERIODES[:idx]]
    if idx < len(PERIODES) - 1:
        return prev, None

    if current is None:
        current = compute_class(cid, per)[0]
    all_res = [r for _, r in prev] + [current]

    annual = {}
    for sid in current:
        sub_ids = {k for r in all_res if sid in r for k in r[sid]["subjects"]}
        subjects = {k: _mean(r[sid]["subjects"][k]["mg"] for r in all_res
                             if sid in r and k in r[sid]["subjects"]) for k in sub_ids}
        annual[sid] = {"moy": _mean(r[sid]["moy"] for r in all_res if sid in r),
                       "subjects": subjects, "rang": None}

    ordered = sorted((s for s in annual if annual[s]["moy"] is not None), key=lambda s: -annual[s]["moy"])
    for pos, sid in enumerate(ordered, 1):                    # rang avec ex æquo
        if pos > 1 and annual[sid]["moy"] == annual[ordered[pos - 2]]["moy"]:
            annual[sid]["rang"] = annual[ordered[pos - 2]]["rang"]
        else:
            annual[sid]["rang"] = pos
    return prev, annual


def save_grades(subject_id, periode, data):
    grade_repository.save_many(subject_id, periode, data)


def get_discipline(student_id, periode):
    return grade_repository.get_discipline(student_id, periode)


def save_discipline(student_id, periode, values):
    grade_repository.save_discipline(student_id, periode, values)