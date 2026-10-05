"""Enseignants : une ou plusieurs matières, objectif horaire hebdomadaire."""
import customtkinter as ctk

from app.constants import C, FONT
from app.database.queries import cur_year, year_extra
from app.repositories import subject_repository, teacher_repository
from app.services.settings_service import default_hours
from app.ui.components.card import label
from app.ui.components.data_table import CrudPage


class TeachersPage(CrudPage):
    def __init__(self, master):
        fields = [
            dict(key="nom", label="Nom", type="entry", required=True),
            dict(key="prenom", label="Prénoms", type="entry"),
            dict(key="heures_sem", label="Heures / semaine (vide = valeur des paramètres)", type="number",
                 optional=True, placeholder="Ex : 21"),
            dict(key="email", label="Email", type="entry"),
            dict(key="telephone", label="Téléphone", type="entry"),
        ]
        cols = [("Nom", 120), ("Prénoms", 110), ("Matières", 150), ("H. attribuées", 95),
                ("Objectif h/sem.", 105), ("Email", 150), ("Téléphone", 100)]
        self.sub_vars = {}
        super().__init__(master, "Liste des enseignants", "teachers", fields, teacher_repository.LIST_SQL, cols,
                         list_params=lambda: (default_hours(), cur_year()), insert_extra=year_extra)
        label(self.body, "Matières enseignées (une ou plusieurs)", 12, color=C["muted"]).pack(
            anchor="w", padx=14, pady=(14, 4))
        self.sub_frame = ctk.CTkFrame(self.body, fg_color=C["soft"], border_width=1, border_color=C["border"],
                                      corner_radius=8)
        self.sub_frame.pack(fill="x", padx=14, pady=(0, 10))

    def build_subject_boxes(self):
        for w in self.sub_frame.winfo_children():
            w.destroy()
        self.sub_vars = {}
        subs = subject_repository.by_year(cur_year())
        if not subs:
            label(self.sub_frame, "Créez d'abord des matières.", 11, color=C["muted"]).pack(padx=10, pady=8)
        for s in subs:
            v = ctk.BooleanVar(value=False)
            ctk.CTkCheckBox(self.sub_frame, text=s["nom"] + (f"  ({s['code']})" if s["code"] else ""),
                            variable=v, fg_color=C["primary"], text_color=C["text"],
                            font=(FONT, 12)).pack(anchor="w", padx=10, pady=4)
            self.sub_vars[s["id"]] = v

    def refresh(self):
        self.build_subject_boxes()
        super().refresh()

    def clear(self):
        super().clear()
        for v in self.sub_vars.values():
            v.set(False)

    def on_select(self, _=None):
        super().on_select(_)
        if self.selected_id:
            ids = teacher_repository.subject_ids(self.selected_id)
            for sid, v in self.sub_vars.items():
                v.set(sid in ids)

    def after_save(self, tid):
        teacher_repository.set_subjects(tid, [s for s, v in self.sub_vars.items() if v.get()])
