from tkinter import filedialog, messagebox

from app.constants import C
from app.database.queries import cur_year
from app.repositories import class_repository, student_repository
from app.services import student_service
from app.ui.components.card import label
from app.ui.components.data_table import CrudPage
from app.ui.components.dialogs import blocked
from app.ui.components.inputs import combo
from app.utils.formatting import new_matricule

ALL = "Toutes les classes"


def import_students(page):
    """Importe un fichier Excel/CSV dans la classe sélectionnée en haut de la liste."""
    if blocked():
        return
    cid = page.require_class("importer des élèves")
    if cid is None:
        return
    cname = page.class_cb.get()
    path = filedialog.askopenfilename(title=f"Importer des élèves dans {cname}",
                                      filetypes=[("Excel / CSV", "*.xlsx *.xlsm *.csv")])
    if not path:
        return
    try:
        r = student_service.import_students(path, cid)
    except ImportError:
        messagebox.showerror("Import", "Le module openpyxl est requis pour lire les fichiers Excel.\n"
                                       "Installez-le avec :  pip install openpyxl")
        return
    except student_service.StudentImportError as ex:
        messagebox.showerror("Import", str(ex))
        return
    except Exception as ex:
        messagebox.showerror("Import", f"Lecture du fichier impossible :\n{ex}")
        return
    messagebox.showinfo("Import terminé", f"{r['added']} élève(s) importé(s) dans « {cname} »\n"
                                          f"{r['skipped']} ligne(s) ignorée(s) (doublons ou incomplètes)")
    page.refresh()


def save_template(page=None):
    path = filedialog.asksaveasfilename(defaultextension=".xlsx", initialfile="modele_import_eleves.xlsx",
                                        filetypes=[("Excel", "*.xlsx")])
    if not path:
        return
    try:
        student_service.save_template(path)
    except ImportError:
        messagebox.showerror("Modèle", "Installez openpyxl :  pip install openpyxl")
        return
    messagebox.showinfo("Modèle", "Modèle enregistré. Remplissez-le, choisissez la classe dans la liste "
                                  "puis utilisez « Importer Excel ».")


class StudentsPage(CrudPage):
    """Élèves : la classe se choisit en haut de la liste et s'applique à l'enregistrement et à l'import."""

    def __init__(self, master):
        fields = [
            dict(key="nom", label="Nom", type="entry", required=True),
            dict(key="prenom", label="Prénoms", type="entry", required=True),
            dict(key="sexe", label="Sexe", type="combo", values=["Masculin", "Féminin"]),
            dict(key="statut", label="Statut", type="combo", values=["Nouveau", "Redoublant"]),
            dict(key="date_naissance", label="Date de naissance", type="entry", placeholder="JJ/MM/AAAA"),
            dict(key="tuteur", label="Tuteur / Parent", type="entry"),
            dict(key="telephone", label="Téléphone", type="entry"),
        ]
        cols = [("Matricule", 100), ("Nom", 110), ("Prénoms", 120), ("Sexe", 80), ("Statut", 85),
                ("Naissance", 90), ("Classe", 70), ("Tuteur", 120), ("Téléphone", 100)]
        self.classes = {}
        super().__init__(master, "Liste des élèves", "students", fields, student_repository.LIST_SQL, cols,
                         after_insert=lambda sid: student_repository.set_matricule(sid, new_matricule(sid)),
                         list_params=self.list_params, insert_extra=self.insert_extra,
                         actions=[("Importer Excel", import_students, "primary", "upload"),
                                  ("Modèle Excel", save_template, "light", "download")])
        label(self.head, "Classe", 12, color=C["muted"]).pack(side="left", padx=(24, 6))
        self.class_cb = combo(self.head, [ALL], command=lambda _=None: self.refresh(), width=200)
        self.class_cb.set(ALL)
        self.class_cb.pack(side="left")

    def selected_class_id(self):
        return self.classes.get(self.class_cb.get())  # None = « Toutes les classes »

    def require_class(self, action):
        cid = self.selected_class_id()
        if cid is None:
            messagebox.showwarning("Classe requise", f"Sélectionnez d'abord une classe (en haut de la liste) "
                                                     f"pour {action}.")
        return cid

    def list_params(self):
        cid = self.selected_class_id()
        return cur_year(), cid, cid

    def insert_extra(self):
        return {"annee_id": cur_year(), "classe_id": self.selected_class_id()}

    def refresh(self):
        self.classes = class_repository.options(cur_year())
        self.class_cb.configure(values=[ALL] + list(self.classes))
        if self.class_cb.get() not in self.classes:
            self.class_cb.set(ALL)
        super().refresh()

    def save(self):
        if blocked():
            return
        if not self.selected_id and self.require_class("enregistrer un élève") is None:
            return
        super().save()


def students_page(master):
    return StudentsPage(master)