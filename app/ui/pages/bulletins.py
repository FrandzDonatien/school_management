import customtkinter as ctk
from tkinter import messagebox

from app.constants import C, PERIODES
from app.database.queries import cur_year
from app.repositories import class_repository, student_repository
from app.services import bulletin_service, grade_service
from app.ui.components.buttons import button
from app.ui.components.card import card, label
from app.ui.components.data_table import DataTable
from app.ui.components.dialogs import PdfPreviewDialog, blocked
from app.ui.components.inputs import entry, labeled_combo
from app.utils.formatting import fmt, mention

_PIP = {"PIL": "pillow", "pypdfium2": "pypdfium2", "reportlab": "reportlab"}

BASE_COLS = [("Discipline", 150), ("Interro", 58), ("Devoir", 58), ("Moy. Cl.", 64), ("Compo", 58),
             ("Moy. Gén.", 66), ("Coef", 44), ("Note déf.", 68), ("Rang", 46), ("Appréciation", 96)]


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

        self.body = card(self)
        self.body.grid(row=1, column=0, sticky="nsew", padx=(0, 16))
        self.body.rowconfigure(1, weight=1)
        self.body.columnconfigure(0, weight=1)
        label(self.body, "Aperçu des résultats", 16, True).grid(row=0, column=0, sticky="w", padx=22, pady=(20, 10))
        self.dt, self.dt_per = None, None
        self.build_table(PERIODES[0])

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
        self.ann_lbl = label(sc, "", 13, True, C["primary"])
        self.ann_lbl.pack(anchor="w", padx=14, pady=(8, 0))
        label(sc, "Discipline (apparaît sur le bulletin)", 12, True).pack(anchor="w", padx=14, pady=(16, 0))
        self.dis = {}
        for k, t in [("absences", "Absences"), ("sanctions", "Sanctions"), ("merites", "Mérites"), ("exclusions", "Exclusions")]:
            label(sc, t, 11, color=C["muted"]).pack(anchor="w", padx=14, pady=(6, 1))
            self.dis[k] = entry(sc)
            self.dis[k].pack(fill="x", padx=14)
        button(sc, "Bulletin de l'élève", lambda: self.generate(False), ic="file").pack(fill="x", padx=14, pady=(18, 6))
        button(sc, "Bulletins de toute la classe", lambda: self.generate(True), "light", ic="layers").pack(fill="x", padx=14)
        button(sc, "Vérifier un numéro de bulletin", self.verify_code, "light", ic="lock").pack(
            fill="x", padx=14, pady=(18, 6))

    def build_table(self, per):
        """(Re)crée le tableau : colonnes de récap des trimestres précédents, + moyenne annuelle au dernier."""
        if self.dt is not None and self.dt_per == per:
            return
        if self.dt is not None:
            self.dt.destroy()
        idx = PERIODES.index(per)
        cols = list(BASE_COLS)
        cols += [(f"Moy. T{i + 1}", 64) for i in range(idx)]
        if idx == len(PERIODES) - 1:
            cols.append(("Moy. Ann.", 70))
        self.dt = DataTable(self.body, cols, search=False, paginate=False, with_id=False)
        self.dt.grid(row=1, column=0, sticky="nsew", padx=22, pady=(0, 20))
        self.dt_per = per

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
        self.build_table(per)
        self.dt.set_rows([])
        for e in self.dis.values():
            e.delete(0, "end")
        self.moy_lbl.configure(text="--")
        self.rank_lbl.configure(text="Rang : —")
        self.ment_lbl.configure(text="Mention : —")
        self.ann_lbl.configure(text="")
        if not sid:
            return
        res, subs, stats = grade_service.compute_class(cid, per)
        prev, annual = grade_service.compute_recap(cid, per, current=res)
        r = res[sid]
        rows = []
        for sub in subs:
            x = r["subjects"].get(sub["id"])
            base = ((sub["nom"], fmt(x["interro"]), fmt(x["devoir"]), fmt(x["mc"]), fmt(x["compo"]), fmt(x["mg"]),
                     f"{x['coef']:g}", fmt(x["nd"]), x["rang"], mention(x["mg"])) if x
                    else (sub["nom"], "", "", "", "", "", f"{sub['coefficient']:g}", "", "", ""))
            extra = []
            for _, pres in prev:                                   # moyennes des trimestres précédents
                px = pres.get(sid, {}).get("subjects", {}).get(sub["id"])
                extra.append(fmt(px["mg"]) if px else "")
            if annual:                                             # moyenne annuelle par discipline
                extra.append(fmt(annual[sid]["subjects"].get(sub["id"])))
            rows.append(base + tuple(extra))
        self.dt.set_rows(rows)
        self.moy_lbl.configure(text=fmt(r["moy"]) or "--")
        if r["rang"]:
            self.rank_lbl.configure(text=f"Rang : {r['rang']} / {stats['effectif']}")
        self.ment_lbl.configure(text=f"Mention : {mention(r['moy']) or '—'}")
        if annual and annual[sid]["moy"] is not None:
            rang = annual[sid]["rang"]
            self.ann_lbl.configure(text=f"Moy. annuelle : {fmt(annual[sid]['moy'])}"
                                        + (f"  (rang {rang} / {stats['effectif']})" if rang else ""))
        d = grade_service.get_discipline(sid, per)
        if d:
            for k, e in self.dis.items():
                e.insert(0, d[k] or "")

    def save_discipline(self):
        sid, per, _ = self.current()
        grade_service.save_discipline(sid, per, {k: e.get().strip() for k, e in self.dis.items()})

    def generate(self, whole_class):
        """Ouvre l'aperçu du (des) bulletin(s) ; le PDF n'est enregistré qu'après confirmation dans l'aperçu."""
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
            save_text = f"Enregistrer les {len(ids)} bulletins"
        else:
            ids, name = [sid], f"Bulletin_{self.student_cb.get()}_{per}"
            save_text = "Enregistrer et ouvrir"
        try:
            pdf = bulletin_service.preview(ids, cid, per, name)
            PdfPreviewDialog(self, pdf, name, on_save=lambda: self.save_pdf(ids, cid, per, name),
                             save_text=save_text)
        except ImportError as ex:
            pkg = _PIP.get(ex.name, ex.name or "reportlab pillow pypdfium2")
            messagebox.showerror("Bulletin", f"Un module est requis :  pip install {pkg}")
        except Exception as ex:
            messagebox.showerror("Bulletin", f"Échec de la préparation du bulletin :\n{ex}")

    def save_pdf(self, ids, cid, per, name):
        """Appelée par le bouton d'enregistrement de l'aperçu : attribue les numéros, écrit et ouvre le PDF."""
        try:
            bulletin_service.generate(ids, cid, per, name)
        except Exception as ex:
            messagebox.showerror("Bulletin", f"Échec de l'enregistrement du bulletin :\n{ex}")
            return False
        return True

    def verify_code(self):
        """Contrôle d'authenticité : le numéro imprimé sur le bulletin doit exister en base."""
        code = ctk.CTkInputDialog(text="Saisissez le numéro imprimé sur le bulletin (BUL-XXXX-XXXX-XXXX) :",
                                  title="Vérifier un bulletin").get_input()
        if not code:
            return
        info = bulletin_service.verify(code)
        if not info:
            messagebox.showwarning("Vérification", "Numéro inconnu : aucun bulletin portant ce numéro n'a été édité "
                                                   "par cette application (ou le numéro est mal saisi).\n\n"
                                                   "Le document est peut-être falsifié.")
            return
        moy = "—" if info["moyenne"] is None else f"{info['moyenne']:.2f}"
        rang = f"{info['rang']} / {info['effectif']}" if info["rang"] else "—"
        messagebox.showinfo("Bulletin enregistré",
                            f"Numéro : {info['code']}\n"
                            f"Élève : {info['eleve']}\nClasse : {info['classe']}\n"
                            f"Période : {info['periode']}  ({info['annee']})\n"
                            f"Moyenne : {moy}    Rang : {rang}\n\n"
                            f"Émis le : {info['created_at']}\nDernière édition : {info['updated_at']} "
                            f"({info['prints']} édition(s))\n\n"
                            "Comparez ces informations avec celles du document papier.")