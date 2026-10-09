import sqlite3

import customtkinter as ctk
from tkinter import messagebox

from app.constants import C
from app.database.queries import year_extra, year_params
from app.repositories import category_repository, subject_repository
from app.ui.components.buttons import button
from app.ui.components.card import label
from app.ui.components.data_table import CrudPage, DataTable
from app.ui.components.inputs import entry
from app.ui.pages.class_subjects import open_class_subjects
from pathlib import Path
import sys

def resource_path(relative_path):
    """Retourne le chemin d'une ressource en développement ou après compilation."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parents[3]

    return base_path / relative_path


class CategoriesDialog(ctk.CTkToplevel):
    """Gestion des catégories de matières (ajout, modification, suppression, ordre d'affichage)."""

    def __init__(self, master, on_change):
        super().__init__(master)
        self.title("Catégories de matières")
        self.geometry("560x600")
        self.iconbitmap(str(resource_path("assets/EduManager_fixed.ico")))
        self.resizable(False, False)
        self.configure(fg_color="white")
        self.on_change, self.selected = on_change, None

        label(self, "Catégories de matières", 18, True).pack(anchor="w", padx=24, pady=(20, 2))
        label(self, "Elles regroupent les matières sur le bulletin, dans l'ordre de la liste.", 12,
              color=C["muted"]).pack(anchor="w", padx=24)
        self.dt = DataTable(self,
                            [("Catégorie", 150), ("Titre sur le bulletin", 230), ("Matières", 70)],
                            search=False, paginate=False, height=3)
        self.dt.pack(fill="x", padx=24, pady=(8, 2))
        self.dt.tree.bind("<<TreeviewSelect>>", self.on_select)

        label(self, "Nom (ex : Littéraire)", 12, color=C["muted"]).pack(anchor="w", padx=24,pady=(0, 0))
        self.name_entry = entry(self)
        self.name_entry.pack(fill="x", padx=24, pady=(2, 8))
        label(self, "Titre sur le bulletin (ex : Matières littéraires) — facultatif", 12,
              color=C["muted"]).pack(anchor="w", padx=24)
        self.title_entry = entry(self)
        self.title_entry.pack(fill="x", padx=24, pady=(2, 12))

        r1 = ctk.CTkFrame(self, fg_color="transparent")
        r1.pack(fill="x", padx=24)
        r1.columnconfigure((0, 1, 2), weight=1)
        button(r1, "Ajouter", self.add, ic="plus").grid(row=0, column=0, sticky="ew", padx=(0, 4))
        button(r1, "Modifier", self.update, "light", ic="pencil").grid(row=0, column=1, sticky="ew", padx=4)
        button(r1, "Supprimer", self.remove, "danger", ic="trash").grid(row=0, column=2, sticky="ew", padx=(4, 0))
        r2 = ctk.CTkFrame(self, fg_color="transparent")
        r2.pack(fill="x", padx=24, pady=(8, 0))
        r2.columnconfigure((0, 1, 2), weight=1)
        button(r2, "Monter", lambda: self.move(-1), "light", ic="chev-l").grid(row=0, column=0, sticky="ew", padx=(0, 4))
        button(r2, "Descendre", lambda: self.move(1), "light", ic="chev-r").grid(row=0, column=1, sticky="ew", padx=4)
        button(r2, "Fermer", self.destroy, "light", ic="x").grid(row=0, column=2, sticky="ew", padx=(4, 0))

        self.transient(master.winfo_toplevel())
        self.after(150, self.grab_set)
        self.reload()

    def reload(self, select=None):
        self.dt.set_rows([(r["id"], r["nom"], r["titre"] or "", r["n"]) for r in category_repository.list_all()])
        self.selected = None
        self.name_entry.delete(0, "end")
        self.title_entry.delete(0, "end")
        if select is not None and self.dt.tree.exists(str(select)):
            self.dt.tree.selection_set(str(select))

    def on_select(self, _=None):
        sel = self.dt.tree.selection()
        if not sel:
            return
        self.selected = int(sel[0])
        r = category_repository.get(self.selected)
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, r["nom"])
        self.title_entry.delete(0, "end")
        self.title_entry.insert(0, r["titre"] or "")

    def values(self):
        nom = self.name_entry.get().strip()
        if not nom:
            messagebox.showwarning("Catégorie", "Le nom de la catégorie est obligatoire.", parent=self)
            return None
        return nom, self.title_entry.get().strip()

    def changed(self, select=None):
        self.reload(select)
        self.on_change()

    def add(self):
        v = self.values()
        if not v:
            return
        try:
            cid = category_repository.create(*v)
        except sqlite3.IntegrityError:
            messagebox.showerror("Catégorie", "Cette catégorie existe déjà.", parent=self)
            return
        self.changed(cid)

    def update(self):
        if not self.selected:
            messagebox.showinfo("Catégorie", "Sélectionnez une catégorie dans la liste.", parent=self)
            return
        v = self.values()
        if not v:
            return
        try:
            category_repository.update(self.selected, *v)
        except sqlite3.IntegrityError:
            messagebox.showerror("Catégorie", "Cette catégorie existe déjà.", parent=self)
            return
        self.changed(self.selected)

    def remove(self):
        if not self.selected:
            messagebox.showinfo("Catégorie", "Sélectionnez une catégorie dans la liste.", parent=self)
            return
        if messagebox.askyesno("Confirmation", "Supprimer cette catégorie ?\nSes matières deviendront « sans catégorie ».",
                               parent=self):
            category_repository.delete(self.selected)
            self.changed()

    def move(self, delta):
        if not self.selected:
            messagebox.showinfo("Catégorie", "Sélectionnez une catégorie dans la liste.", parent=self)
            return
        cid = self.selected
        category_repository.move(cid, delta)
        self.changed(cid)


def open_categories(page):
    CategoriesDialog(page, on_change=page.refresh)


def subjects_page(master):
    fields = [
        dict(key="nom", label="Nom de la matière", type="entry", required=True),
        dict(key="code", label="Abréviation", type="entry", placeholder="Ex : MATHS"),
        dict(key="categorie_id", label="Catégorie", type="fk", options=category_repository.options),
        dict(key="coefficient", label="Coefficient par défaut", type="number", required=True, placeholder="Ex : 2"),
    ]
    return CrudPage(master, "Liste des matières", "subjects", fields, subject_repository.LIST_SQL,
                    [("Matière", 220), ("Abréviation", 100), ("Catégorie", 130), ("Coefficient", 90)],
                    list_params=year_params, insert_extra=year_extra,
                    actions=[("Catégories", open_categories, "light", "layers"),
                             ("Matières par classe", open_class_subjects, "light", "school")])