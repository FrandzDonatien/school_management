from app.database.queries import cur_year
from app.repositories import class_repository, student_repository
from app.services import student_service
from app.utils.formatting import new_matricule


def test_create_student_and_matricule():
    y = cur_year()
    cid = class_repository.create("Test A", "Test", y)
    sid = student_repository.create(dict(nom="KOFFI", prenom="Ama", sexe="Féminin", statut="Nouveau",
                                         date_naissance="01/01/2012", classe_id=cid, tuteur="", telephone=""), y)
    student_repository.set_matricule(sid, new_matricule(sid))
    st = student_repository.get(sid)
    assert st.full_name == "KOFFI Ama" and st.matricule.startswith("EL")


def test_import_csv_into_selected_class(tmp_path):
    y = cur_year()
    cid = class_repository.create("Import 1", "Import", y)
    f = tmp_path / "eleves.csv"
    # une colonne « Classe » éventuellement présente est ignorée : la classe choisie fait foi
    f.write_text("Nom;Prénoms;Sexe;Classe\nDOE;John;M;Autre\nDOE;John;M;Autre\n;;;\n", encoding="utf-8")
    r = student_service.import_students(str(f), cid)
    assert r == dict(added=1, skipped=2)
    rows = student_repository.names_by_class(cid)
    assert [(x["nom"], x["prenom"]) for x in rows] == [("DOE", "John")]