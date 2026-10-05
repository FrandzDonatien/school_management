from app.database.queries import cur_year
from app.repositories import class_repository, student_repository, subject_repository
from app.services import bulletin_service, grade_service


def test_bulletin_html():
    y = cur_year()
    cid = class_repository.create("Bull A", "B", y)
    sid = student_repository.create(dict(nom="Kossi", prenom="Yao", sexe="Masculin", statut="Nouveau",
                                         date_naissance="", classe_id=cid, tuteur="", telephone=""), y)
    sub = subject_repository.by_year(y)[0]
    grade_service.save_grades(sub["id"], "Trimestre 2", {sid: (12, 14, 16)})
    doc = bulletin_service.build_document([sid], cid, "Trimestre 2")
    assert "KOSSI Yao" in doc and "TRIMESTRE 2" in doc and "$" not in doc.split("</style>")[1]
    assert doc.count("class=\"page\"") == 1
