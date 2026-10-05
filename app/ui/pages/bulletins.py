import customtkinter as ctk
from tkinter import messagebox

from app.constants import C, PERIODES
from app.database.queries import cur_year
from app.repositories import class_repository, student_repository
from app.services import bulletin_service, grade_service
from app.ui.components.buttons import button
from app.ui.components.card import card, label
from app.ui.components.data_table import DataTable
from app.ui.components.dialogs import blocked
from app.ui.components.inputs import entry, labeled_combo
from app.utils.formatting import fmt, mention


class BulletinPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=C["bg"])
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.classes, self.students = {}, {}

        top = card(self)
        top.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 16))
        top.columnconfigure((0, 1, 2), weight=1, uniform="b")
        self.class_cb = labeled_combo(top, 0, "Classe", lambda _=None: self.on_class())
        self.student_cb = labeled_combo(top, 1, "Élève", lambda _=None: self.load())
        self.period_cb = labeled_combo(top, 2, "Période", lambda _=None: self.load(), PERIODES)
        self.period_cb.set(PERIODES[0])

        body = card(self)
        body.grid(row=1, column=0, sticky="nsew", padx=(0, 16))
        body.rowconfigure(1, weight=1)
        body.columnconfigure(0, weight=1)
        label(body, "Aperçu des résultats", 16, True).grid(row=0, column=0, sticky="w", padx=22, pady=(20, 10))
        self.dt = DataTable(body, [
            ("Discipline", 150), ("Interro", 62), ("Devoir", 62), ("Moy. Cl.", 68), ("Compo", 62),
            ("Moy. Gén.", 70), ("Coef", 48), ("Note déf.", 72), ("Rang", 50), ("Appréciation", 100)],
            search=False, paginate=False, with_id=False)
        self.dt.grid(row=1, column=0, sticky="nsew", padx=22, pady=(0, 20))

        side = card(self, width=310)
        side.grid(row=1, column=1, sticky="ns")
        side.grid_propagate(False)
        sc = ctk.CTkScrollableFrame(side, fg_color="transparent")
        sc.pack(fill="both", expand=True, padx=6, pady=6)
        label(sc, "Résultats", 16, True).pack(anchor="w", padx=14, pady=(10, 0))
        self.moy_lbl = label(sc, "--", 38, True, C["primary"])
        self.moy_lbl.pack(anchor="w", padx=14, pady=(6, 0))
        label(sc, "Moyenne générale / 20", 11, color=C["muted"]).pack(anchor="w", padx=14)
        self.rank_lbl = label(sc, "Rang : —", 13)
        self.rank_lbl.pack(anchor="w", padx=14, pady=(10, 0))
        self.ment_lbl = label(sc, "Mention : —", 13)
        self.ment_lbl.pack(anchor="w", padx=14)
        label(sc, "Discipline (apparaît sur le bulletin)", 12, True).pack(anchor="w", padx=14, pady=(16, 0))
        self.dis = {}
        for k, t in [("absences", "Absences"), ("sanctions", "Sanctions"), ("merites", "Mérites"), ("exclusions", "Exclusions")]:
            label(sc, t, 11, color=C["muted"]).pack(anchor="w", padx=14, pady=(6, 1))
            self.dis[k] = entry(sc)
            self.dis[k].pack(fill="x", padx=14)
        button(sc, "Bulletin de l'élève", lambda: self.generate(False), ic="file").pack(fill="x", padx=14, pady=(18, 6))
        button(sc, "Bulletins de toute la classe", lambda: self.generate(True), "light", ic="layers").pack(fill="x", padx=14)

    def refresh(self):
        self.classes = class_repository.options(cur_year())
        self.class_cb.configure(values=list(self.classes) or [""])
        if self.class_cb.get() not in self.classes:
            self.class_cb.set(next(iter(self.classes), ""))
        self.on_class()

    def on_class(self):
        cid = self.classes.get(self.class_cb.get())
        rows = student_repository.names_by_class(cid)
        self.students = {f"{r['nom'].upper()} {r['prenom']}": r["id"] for r in rows}
        self.student_cb.configure(values=list(self.students) or [""])
        self.student_cb.set(next(iter(self.students), ""))
        self.load()

    def current(self):
        return self.students.get(self.student_cb.get()), self.period_cb.get(), self.classes.get(self.class_cb.get())

    def load(self):
        sid, per, cid = self.current()
        self.dt.set_rows([])
        for e in self.dis.values():
            e.delete(0, "end")
        self.moy_lbl.configure(text="--")
        self.rank_lbl.configure(text="Rang : —")
        self.ment_lbl.configure(text="Mention : —")
        if not sid:
            return
        res, subs, stats = grade_service.compute_class(cid, per)
        r = res[sid]
        rows = []
        for sub in subs:
            x = r["subjects"].get(sub["id"])
            rows.append((sub["nom"], fmt(x["interro"]), fmt(x["devoir"]), fmt(x["mc"]), fmt(x["compo"]), fmt(x["mg"]),
                         f"{x['coef']:g}", fmt(x["nd"]), x["rang"], mention(x["mg"])) if x
                        else (sub["nom"], "", "", "", "", "", f"{sub['coefficient']:g}", "", "", ""))
        self.dt.set_rows(rows)
        self.moy_lbl.configure(text=fmt(r["moy"]) or "--")
        if r["rang"]:
            self.rank_lbl.configure(text=f"Rang : {r['rang']} / {stats['effectif']}")
        self.ment_lbl.configure(text=f"Mention : {mention(r['moy']) or '—'}")
        d = grade_service.get_discipline(sid, per)
        if d:
            for k, e in self.dis.items():
                e.insert(0, d[k] or "")

    def save_discipline(self):
        sid, per, _ = self.current()
        grade_service.save_discipline(sid, per, {k: e.get().strip() for k, e in self.dis.items()})

    def generate(self, whole_class):
        sid, per, cid = self.current()
        if not cid or (not whole_class and not sid):
            messagebox.showwarning("Bulletin", "Sélectionnez une classe et un élève.")
            return
        if sid and not blocked(False):
            self.save_discipline()
        if whole_class:
            ids = [r["id"] for r in student_repository.ids_by_class(cid)]
            if not ids:
                messagebox.showwarning("Bulletin", "Cette classe ne contient aucun élève.")
                return
            name = f"Bulletins_{self.class_cb.get()}_{per}"
        else:
            ids, name = [sid], f"Bulletin_{self.student_cb.get()}_{per}"
        try:
            bulletin_service.generate(ids, cid, per, name)
        except ImportError:
            messagebox.showerror("Bulletin", "Le module reportlab est requis :  pip install reportlab")
        except Exception as ex:
            messagebox.showerror("Bulletin", f"Échec de la génération du bulletin :\n{ex}")