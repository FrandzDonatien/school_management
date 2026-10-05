import sqlite3

import customtkinter as ctk
from tkinter import messagebox

from app.constants import C, FONT
from app.database.queries import active_year, cur_year, get_view_year, set_view_year
from app.repositories import year_repository
from app.services import school_year_service
from app.ui.components.buttons import button
from app.ui.components.card import card, label
from app.ui.components.data_table import DataTable
from app.ui.components.inputs import combo, entry
from app.utils.validation import is_year_label


class YearsPage(ctk.CTkFrame):
    def __init__(self, master, on_change):
        super().__init__(master, fg_color=C["bg"])
        self.on_change = on_change
        self.selected = None
        self.src_map = {}
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        form = card(self, width=350)
        form.grid(row=0, column=0, sticky="ns", padx=(0, 16))
        form.grid_propagate(False)
        sc = ctk.CTkScrollableFrame(form, fg_color="transparent")
        sc.pack(fill="both", expand=True, padx=6, pady=6)
        label(sc, "Gérer les années", 16, True).pack(anchor="w", padx=16, pady=(12, 6))
        label(sc, "Année scolaire *", 12, color=C["muted"]).pack(anchor="w", padx=16, pady=(6, 2))
        self.name = entry(sc, "Ex : 2026-2027")
        self.name.pack(fill="x", padx=16)
        label(sc, "Reprendre les données de l'année", 12, color=C["muted"]).pack(anchor="w", padx=16, pady=(12, 2))
        self.src_cb = combo(sc, [""])
        self.src_cb.pack(fill="x", padx=16)
        self.opts = {}
        for key, txt, val in (("base", "Matières et enseignants", True), ("cls", "Classes (et titulaires)", True),
                              ("asg", "Affectations des cours", True), ("stu", "Élèves (même classe, à modifier)", False)):
            var = ctk.BooleanVar(value=val)
            ctk.CTkCheckBox(sc, text=txt, variable=var, fg_color=C["primary"], text_color=C["text"],
                            font=(FONT, 12)).pack(anchor="w", padx=16, pady=5)
            self.opts[key] = var
        button(sc, "Créer l'année", self.create, ic="plus").pack(fill="x", padx=16, pady=(14, 6))
        button(sc, "Consulter (lecture seule)", self.consult, "light", ic="search").pack(fill="x", padx=16, pady=5)
        button(sc, "Définir comme année active", self.activate, "light", ic="check").pack(fill="x", padx=16, pady=5)
        button(sc, "Renommer", self.rename, "light", ic="pencil").pack(fill="x", padx=16, pady=5)
        button(sc, "Supprimer", self.delete, "danger", ic="trash").pack(fill="x", padx=16, pady=5)
        label(sc, "L'année active est la seule modifiable. Les années antérieures restent consultables à tout moment "
                  "grâce au sélecteur en haut de l'écran.", 11, color=C["muted"], justify="left", wraplength=290).pack(
            anchor="w", padx=16, pady=12)

        right = card(self)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)
        label(right, "Années scolaires", 16, True).grid(row=0, column=0, sticky="w", padx=22, pady=(20, 10))
        self.dt = DataTable(right, [("Année scolaire", 150), ("Statut", 100), ("Classes", 80), ("Élèves", 80),
                                    ("Enseignants", 100)])
        self.dt.grid(row=1, column=0, sticky="nsew", padx=22, pady=(0, 20))
        self.dt.tree.bind("<<TreeviewSelect>>", self.on_select)

    def refresh(self):
        self.selected = None
        act, cur = active_year(), cur_year()
        rows = []
        for r in year_repository.list_all():
            n = lambda t: year_repository.count_in(t, r["id"])
            st = "Active" if r["id"] == act else ("Consultée" if r["id"] == cur else "Archivée")
            rows.append((r["id"], r["libelle"], st, n("classes"), n("students"), n("teachers")))
        self.dt.set_rows(rows)
        self.src_map = {r["libelle"]: r["id"] for r in year_repository.list_all()}
        self.src_cb.configure(values=["Aucune (année vide)"] + list(self.src_map))
        lab = year_repository.label(cur)
        self.src_cb.set(lab if lab else "Aucune (année vide)")

    def on_select(self, _=None):
        sel = self.dt.tree.selection()
        if sel:
            self.selected = int(sel[0])
            self.name.delete(0, "end")
            self.name.insert(0, year_repository.label(self.selected))

    def label_ok(self):
        lab = self.name.get().strip()
        if not is_year_label(lab):
            messagebox.showwarning("Année scolaire", "Format attendu : AAAA-AAAA (ex : 2026-2027).")
            return None
        return lab

    def create(self):
        lab = self.label_ok()
        if not lab:
            return
        src = self.src_map.get(self.src_cb.get())
        base, cls, asg, stu = (self.opts[k].get() for k in ("base", "cls", "asg", "stu"))
        try:
            yid = school_year_service.create_year(lab, src, base, cls, asg, stu)
        except sqlite3.IntegrityError:
            messagebox.showerror("Année scolaire", "Cette année existe déjà.")
            return
        if messagebox.askyesno("Année créée", f"Année {lab} créée.\nLa définir comme année active ?"):
            school_year_service.activate(yid)
            set_view_year(None)
        self.on_change()
        self.refresh()

    def consult(self):
        if not self.selected:
            messagebox.showinfo("Consultation", "Sélectionnez une année dans la liste.")
            return
        set_view_year(None if self.selected == active_year() else self.selected)
        self.on_change()
        self.refresh()

    def activate(self):
        if not self.selected:
            messagebox.showinfo("Année active", "Sélectionnez une année dans la liste.")
            return
        school_year_service.activate(self.selected)
        set_view_year(None)
        self.on_change()
        self.refresh()

    def rename(self):
        if not self.selected:
            messagebox.showinfo("Renommer", "Sélectionnez une année dans la liste.")
            return
        lab = self.label_ok()
        if not lab:
            return
        try:
            year_repository.rename(self.selected, lab)
        except sqlite3.IntegrityError:
            messagebox.showerror("Renommer", "Cette année existe déjà.")
            return
        self.on_change()
        self.refresh()

    def delete(self):
        if not self.selected:
            messagebox.showinfo("Suppression", "Sélectionnez une année dans la liste.")
            return
        if self.selected == active_year():
            messagebox.showwarning("Suppression", "Impossible de supprimer l'année active. "
                                                  "Activez d'abord une autre année.")
            return
        n = year_repository.count_in("students", self.selected)
        if messagebox.askyesno("Confirmation", f"Supprimer cette année avec ses classes, ses {n} élève(s), "
                                               "ses notes, ses enseignants et ses emplois du temps ?\n"
                                               "Cette action est irréversible."):
            y = self.selected
            school_year_service.delete_year(y)
            if get_view_year() == y:
                set_view_year(None)
            self.on_change()
            self.refresh()
