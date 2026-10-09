"""Matières par classe : choisir les matières enseignées dans chaque classe et leur coefficient."""
import customtkinter as ctk
from tkinter import messagebox

from app.constants import C, FONT
from app.database.queries import cur_year
from app.repositories import class_repository, class_subject_repository, subject_repository
from app.ui.components.buttons import button
from app.ui.components.card import label
from app.ui.components.dialogs import blocked
from app.ui.components.inputs import combo, entry
from pathlib import Path
import sys

def resource_path(relative_path):
    """Retourne le chemin d'une ressource en développement ou après compilation."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parents[3]

    return base_path / relative_path

def _coef(text):
    try:
        v = float(text.strip().replace(",", "."))
    except ValueError:
        return None
    return v if 0 < v <= 20 else None


class ClassSubjectsDialog(ctk.CTkToplevel):
    def __init__(self, master, on_change):
        super().__init__(master)
        self.title("Matières par classe")
        self.iconbitmap(str(resource_path("assets/EduManager_fixed.ico")))
        self.geometry("640x720")
        self.resizable(False, False)
        self.configure(fg_color="white")
        self.on_change = on_change
        self.rows, self.names = {}, {}
        self.classes = class_repository.options(cur_year())

        label(self, "Matières par classe", 18, True).pack(anchor="w", padx=24, pady=(20, 2))
        label(self, "Cochez les matières enseignées dans la classe et ajustez leur coefficient si besoin. Une classe "
                    "non personnalisée utilise toutes les matières avec leur coefficient par défaut.", 12,
              color=C["muted"], justify="left", wraplength=590).pack(anchor="w", padx=24)
        label(self, "Classe", 12, color=C["muted"]).pack(anchor="w", padx=24, pady=(12, 2))
        self.class_cb = combo(self, list(self.classes) or [""], command=lambda _=None: self.load())
        self.class_cb.pack(fill="x", padx=24)
        if self.classes:
            self.class_cb.set(next(iter(self.classes)))
        self.info = label(self, "", 12, True, C["primary"], justify="left", wraplength=590)
        self.info.pack(anchor="w", padx=24, pady=(8, 4))

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=24)
        label(head, "Matière", 12, True, C["muted"]).pack(side="left", padx=(36, 0))
        label(head, "Coefficient", 12, True, C["muted"]).pack(side="right", padx=(0, 30))
        self.box = ctk.CTkScrollableFrame(self, fg_color=C["soft"], border_width=1, border_color=C["border"],
                                          corner_radius=8, height=330)
        self.box.pack(fill="x", padx=24, pady=(2, 8))
        self.box.columnconfigure(0, weight=1)

        cp = ctk.CTkFrame(self, fg_color="transparent")
        cp.pack(fill="x", padx=24)
        label(cp, "Copier depuis :", 12, color=C["muted"]).pack(side="left")
        self.copy_cb = combo(cp, [""], width=230)
        self.copy_cb.pack(side="left", padx=8)
        button(cp, "Appliquer", self.copy_from, "light", width=110).pack(side="left")

        bt = ctk.CTkFrame(self, fg_color="transparent")
        bt.pack(fill="x", padx=24, pady=(14, 0))
        bt.columnconfigure((0, 1, 2), weight=1)
        button(bt, "Enregistrer", self.save, ic="save").grid(row=0, column=0, sticky="ew", padx=(0, 4))
        button(bt, "Valeurs par défaut", self.reset, "light", ic="layers").grid(row=0, column=1, sticky="ew", padx=4)
        button(bt, "Fermer", self.destroy, "light", ic="x").grid(row=0, column=2, sticky="ew", padx=(4, 0))

        self.transient(master.winfo_toplevel())
        self.after(150, self.grab_set)
        self.load()

    def current(self):
        return self.classes.get(self.class_cb.get())

    def load(self, source=None):
        """Remplit la liste pour la classe choisie (ou avec la configuration d'une autre classe : `source`)."""
        for w in self.box.winfo_children():
            w.destroy()
        self.rows, self.names = {}, {}
        cid = self.current()
        others = [n for n, i in self.classes.items() if i != cid]
        self.copy_cb.configure(values=others or [""])
        self.copy_cb.set(others[0] if others else "")
        if not cid:
            self.info.configure(text="Aucune classe : créez-en dans la page « Classes ».")
            return
        catalog = subject_repository.by_year(cur_year())
        if not catalog:
            self.info.configure(text="Aucune matière : créez-les d'abord dans la page « Matières ».")
            return
        assigned = class_subject_repository.assignments(source or cid)
        custom = bool(assigned)
        for i, s in enumerate(catalog):
            on = (s["id"] in assigned) if custom else True
            coef = assigned.get(s["id"], s["coefficient"])
            var = ctk.BooleanVar(value=on)
            cat = f"   ({s['categorie']})" if s["categorie"] else ""
            ctk.CTkCheckBox(self.box, text=s["nom"] + cat, variable=var, font=(FONT, 12), fg_color=C["primary"],
                            hover_color=C["primary_dark"]).grid(row=i, column=0, sticky="w", padx=10, pady=4)
            e = entry(self.box, "", width=70)
            e.grid(row=i, column=1, padx=10, pady=4)
            e.insert(0, f"{coef:g}" if coef is not None else "1")
            self.rows[s["id"]] = (var, e)
            self.names[s["id"]] = s["nom"]
        if source:
            self.info.configure(text="Valeurs copiées : cliquez sur « Enregistrer » pour les appliquer à cette classe.")
        elif custom:
            self.info.configure(text=f"Classe personnalisée : {len(assigned)} matière(s).")
        else:
            self.info.configure(text="Classe non personnalisée : toutes les matières, coefficients par défaut.")

    def copy_from(self):
        src = self.classes.get(self.copy_cb.get())
        if src:
            self.load(source=src)

    def save(self):
        if blocked():
            return
        cid = self.current()
        if not cid or not self.rows:
            return
        mapping = {}
        for sid, (var, e) in self.rows.items():
            if not var.get():
                continue
            v = _coef(e.get())
            if v is None:
                messagebox.showwarning("Coefficient", f"Coefficient invalide pour « {self.names[sid]} » "
                                                      "(nombre supérieur à 0 et au plus 20).", parent=self)
                return
            mapping[sid] = v
        if not mapping:
            messagebox.showwarning("Matières", "Cochez au moins une matière.", parent=self)
            return
        default = {s["id"]: s["coefficient"] for s in subject_repository.by_year(cur_year())}
        if set(mapping) == set(default) and all(abs(mapping[k] - (default[k] or 0)) < 1e-9 for k in mapping):
            class_subject_repository.reset(cid)          # identique au catalogue : reste « automatique »
        else:
            class_subject_repository.save(cid, mapping)
        self.on_change()
        self.load()
        messagebox.showinfo("Matières", "Matières de la classe enregistrées.", parent=self)

    def reset(self):
        if blocked():
            return
        cid = self.current()
        if cid and messagebox.askyesno("Valeurs par défaut", "Rétablir toutes les matières avec leur coefficient par "
                                                             "défaut pour cette classe ?", parent=self):
            class_subject_repository.reset(cid)
            self.on_change()
            self.load()


def open_class_subjects(page):
    ClassSubjectsDialog(page, on_change=page.refresh)