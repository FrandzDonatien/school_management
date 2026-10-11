import customtkinter as ctk
from tkinter import filedialog, messagebox

from app.constants import C, FONT
from app.database.queries import cur_year
from app.repositories import class_repository, student_repository
from app.services import student_service, student_export
from app.ui.components.buttons import button
from app.ui.components.card import label
from app.ui.components.data_table import CrudPage
from app.ui.components.dialogs import blocked, resource_path
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


# -- export des listes de classe
class ClassListDialog(ctk.CTkToplevel):
    """Choix du contenu (une classe / toutes les classes) et du format (Excel / PDF)."""

    def __init__(self, master, classes, current, on_export):
        super().__init__(master)
        self.title("Exporter les listes de classe")
        self.iconbitmap(str(resource_path("assets/EduManager_fixed.ico")))
        self.geometry("470x400")
        self.resizable(False, False)
        self.configure(fg_color="white")
        self.classes, self.on_export = classes, on_export
        label(self, "Exporter les listes de classe", 18, True).pack(anchor="w", padx=28, pady=(24, 2))
        label(self, "Choisissez les classes à exporter, puis le format.", 12, color=C["muted"]).pack(
            anchor="w", padx=28)
        self.scope = ctk.StringVar(value="classe" if current in classes else "toutes")

        def radio(parent, text, value, var, pady=(10, 2)):
            ctk.CTkRadioButton(parent, text=text, variable=var, value=value, fg_color=C["primary"],
                               font=(FONT, 12), text_color=C["text"]).pack(anchor="w", padx=28, pady=pady)

        radio(self, "Une classe :", "classe", self.scope, (18, 2))
        self.cls_cb = combo(self, list(classes) or [""])
        self.cls_cb.pack(fill="x", padx=(56, 28))
        self.cls_cb.set(current if current in classes else next(iter(classes), ""))
        radio(self, "Toutes les classes (une feuille / page par classe)", "toutes", self.scope)
        label(self, "Format", 12, True).pack(anchor="w", padx=28, pady=(18, 0))
        self.fmt = ctk.StringVar(value="xlsx")
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(anchor="w", padx=28, pady=(4, 0))
        for text, v in (("Excel (.xlsx)", "xlsx"), ("PDF (.pdf)", "pdf")):
            ctk.CTkRadioButton(row, text=text, variable=self.fmt, value=v, fg_color=C["primary"], font=(FONT, 12),
                               text_color=C["text"]).pack(side="left", padx=(0, 20))
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=28, pady=22, side="bottom")
        button(btns, "Annuler", self.destroy, "light", ic="x", width=120).pack(side="right", padx=(8, 0))
        button(btns, "Exporter", self.go, ic="download", width=140).pack(side="right")
        self.transient(master.winfo_toplevel())
        self.after(150, self.grab_set)

    def go(self):
        scope = self.scope.get()
        cid = self.classes.get(self.cls_cb.get())
        if scope == "classe" and not cid:
            messagebox.showwarning("Export", "Sélectionnez une classe.", parent=self)
            return
        fmt = self.fmt.get()
        self.destroy()
        self.on_export(scope, cid, fmt)


def export_class_lists(page):
    if not page.classes:
        messagebox.showinfo("Export", "Aucune classe : créez d'abord des classes.")
        return
    ClassListDialog(page, page.classes, page.class_cb.get(),
                    lambda scope, cid, fmt: do_export_lists(page, scope, cid, fmt))


def do_export_lists(page, scope, cid, fmt):
    tables, base = student_export.build_tables(scope, cid, page.classes)
    if not tables:
        messagebox.showinfo("Export", "Aucun élève à exporter.")
        return
    ext, types = ((".xlsx", [("Classeur Excel", "*.xlsx")]) if fmt == "xlsx"
                  else (".pdf", [("Document PDF", "*.pdf")]))
    path = filedialog.asksaveasfilename(title="Exporter la liste de classe", defaultextension=ext,
                                        initialfile=base + ext, filetypes=types)
    if not path:
        return
    try:
        student_export.write_file(path, tables, fmt)
    except ImportError as ex:
        messagebox.showerror("Dépendance manquante", f"Un module requis est absent : {ex}\n\n"
                                                     "Installez les dépendances avec :\npip install reportlab openpyxl")
        return
    except Exception as ex:
        messagebox.showerror("Échec de l'export", f"Impossible de générer le fichier :\n{ex}")
        return
    messagebox.showinfo("Export terminé", f"Fichier créé avec succès :\n{path}")


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
                                  ("Modèle Excel", save_template, "light", "download"),
                                  ("Exporter la liste", export_class_lists, "light", "download")])
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