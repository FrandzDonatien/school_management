from app.calculations.grades import calc_mg
from app.database.queries import cur_year
from app.repositories import class_repository, student_repository, subject_repository
from app.services import grade_service
from app.utils.validation import parse_note


def test_calc_mg():
    assert calc_mg(10, 14, 16) == (12, 14)
    assert calc_mg(None, None, 8) == (None, 8)
    assert calc_mg(None, None, None) == (None, None)


def test_parse_note():
    assert parse_note("12,5") == (True, 12.5)
    assert parse_note("21")[0] is False and parse_note("abc")[0] is False
    assert parse_note("") == (True, None)


def test_ranking():
    y = cur_year()
    cid = class_repository.create("Notes A", "N", y)
    sub = subject_repository.by_year(y)[0]
    ids = []
    for n in ("AAA", "BBB", "CCC"):
        ids.append(student_repository.create(dict(nom=n, prenom="x", sexe="", statut="Nouveau", date_naissance="",
                                                  classe_id=cid, tuteur="", telephone=""), y))
    grade_service.save_grades(sub["id"], "Trimestre 1", {ids[0]: (10, 10, 10), ids[1]: (16, 16, 16), ids[2]: (None, None, None)})
    res, subs, stats = grade_service.compute_class(cid, "Trimestre 1")
    assert res[ids[1]]["rang"] == 1 and res[ids[0]]["rang"] == 2 and res[ids[2]]["rang"] is None
    assert stats["effectif"] == 3 and stats["max"] == 16 and stats["min"] == 10
