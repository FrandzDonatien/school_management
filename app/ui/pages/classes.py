from app.database.queries import cur_year, year_extra, year_params
from app.repositories import class_repository, teacher_repository
from app.ui.components.data_table import CrudPage


def classes_page(master):
    fields = [
        dict(key="nom", label="Nom de la classe", type="entry", required=True, placeholder="Ex : 6ème A"),
        dict(key="niveau", label="Niveau", type="entry", placeholder="Ex : 6ème"),
        dict(key="titulaire_id", label="Professeur titulaire", type="fk",
             options=lambda: teacher_repository.options(cur_year())),
    ]
    return CrudPage(master, "Liste des classes", "classes", fields, class_repository.LIST_SQL,
                    [("Classe", 150), ("Niveau", 110), ("Prof. titulaire", 200), ("Effectif", 90)],
                    list_params=year_params, insert_extra=year_extra)
