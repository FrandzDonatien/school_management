import os
from datetime import datetime
from tkinter import messagebox

import customtkinter as ctk

from app.config import EXCEL_DIR, ensure_dirs
from app.constants import C, PERIODES
from app.database.connection import query
from app.database.queries import cur_year
from app.services import stats_service as svc
from app.ui.components.buttons import button
from app.ui.components.card import RankList, StatCard, card, label
from app.ui.components.charts import Chart
from app.ui.components.data_table import BADGES, DataTable
from app.ui.components.inputs import combo

ALL = "Toutes"
SB = dict(scrollbar_button_color=C["muted"], scrollbar_button_hover_color=C["primary"])


def _cols(headers, first=170, other=88):
    """Largeurs relatives (DataTable répartit l'espace disponible proportionnellement)."""
    return [(headers[0], first)] + [(h, other) for h in headers[1:]]


def _fmt_rows(rows):
    """Affiche les décimaux avec 2 chiffres (12.5 -> 12.50)."""
    return [tuple(f"{v:.2f}" if isinstance(v, float) else v for v in r) for r in rows]


def _decision_badge(text):
    return BADGES["success"] if str(text) == "Admis" else BADGES["error"]


def _block(parent, title, sub, columns, page_size=8, search=False, paginate=True,
           height=8, badge_cols=(), pady=(0, 0), **pack):
    """Carte avec en-tête (titre + sous-titre), filet de séparation et DataTable."""
    c = card(parent)
    c.pack(**({"fill": "both", "expand": True, "pady": pady} | pack))
    label(c, title, 15, True).pack(anchor="w", padx=20, pady=(16, 0))
    label(c, sub or " ", 11, color=C["muted"]).pack(anchor="w", padx=20, pady=(0, 10))
    ctk.CTkFrame(c, height=1, fg_color=C["border"]).pack(fill="x")
    t = DataTable(c, columns, page_size=page_size, search=search, paginate=paginate, with_id=False,
                  height=height, badge_cols=badge_cols, badge_fn=_decision_badge)
    t.pack(fill="both", expand=True, padx=20, pady=(14, 18))
    return t


class StatsPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=C["bg"])
        self.data = None
        self.class_map = {}
        self.filter_label = ""

        # ---- barre de filtres (dans une carte)
        bar_card = card(self)
        bar_card.pack(fill="x", pady=(0, 14))
        bar = ctk.CTkFrame(bar_card, fg_color="transparent")
        bar.pack(fill="x", padx=16, pady=10)
        label(bar, "Période", 11, True, C["muted"]).pack(side="left", padx=(0, 8))
        self.cb_per = combo(bar, [ALL] + PERIODES, command=lambda _: self.refresh(), width=160)
        self.cb_per.pack(side="left", padx=(0, 18))
        label(bar, "Classe", 11, True, C["muted"]).pack(side="left", padx=(0, 8))
        self.cb_cls = combo(bar, [ALL], command=lambda _: self.refresh(), width=180)
        self.cb_cls.pack(side="left")
        button(bar, "Exporter en Excel", self.export, "primary", ic="download", width=170).pack(side="right")

        # ---- onglets (texte blanc sur l'onglet actif)
        self.tv = tv = ctk.CTkTabview(self, fg_color="transparent", corner_radius=10,
                                      segmented_button_fg_color=C["card"],
                                      segmented_button_selected_color=C["primary"],
                                      segmented_button_selected_hover_color=C["primary"],
                                      segmented_button_unselected_color=C["card"],
                                      segmented_button_unselected_hover_color=C["primary_light"],
                                      text_color=C["text"],
                                      command=self._paint_tabs)
        tv.pack(fill="both", expand=True)
        t_ov, t_mat, t_sex, t_prof, t_cls, t_rank = [
            tv.add(n) for n in ("Vue d'ensemble", "Matières", "Sexe", "Professeurs", "Classes", "Classement")]
        self._paint_tabs()

        # ===== Vue d'ensemble (cadre défilant : aucun DataTable à l'intérieur)
        sc = ctk.CTkScrollableFrame(t_ov, fg_color="transparent", **SB)
        sc.pack(fill="both", expand=True)
        sc.columnconfigure((0, 1, 2, 3), weight=1, uniform="a")
        self.cards = {}
        defs = [("eleves", "Élèves évalués", "cap", C["primary"], C["primary_light"]),
                ("reussite", "Taux de réussite", "check", C["success"], C["success_light"]),
                ("moyenne", "Moyenne générale", "chart", C["warning"], C["warning_light"]),
                ("echecs", "Élèves en échec", "alert", C["danger"], "#FDE8EB"),
                ("best", "Meilleure moyenne", "chart", C["success"], C["success_light"]),
                ("worst", "Plus faible moyenne", "alert", C["danger"], "#FDE8EB"),
                ("taux_g", "Réussite garçons", "check", C["primary"], C["primary_light"]),
                ("taux_f", "Réussite filles", "check", C["warning"], C["warning_light"])]
        for i, (k, t, ic, col, lt) in enumerate(defs):
            s = StatCard(sc, t, ic, col, lt)
            s.grid(row=i // 4, column=i % 4, sticky="ew",
                   padx=(0 if i % 4 == 0 else 8, 0 if i % 4 == 3 else 8), pady=(0, 16))
            self.cards[k] = s
        self.ch_subj = Chart(sc, "Moyenne par matière", "hbar")
        self.ch_subj.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=(0, 8), pady=(0, 16))
        self.ch_pass = Chart(sc, "Réussite / Échec", "donut", center="élèves")
        self.ch_pass.grid(row=2, column=2, sticky="nsew", padx=8, pady=(0, 16))
        self.ch_cls = Chart(sc, "Taux de réussite par classe (%)", "bar")
        self.ch_cls.grid(row=2, column=3, sticky="nsew", padx=(8, 0), pady=(0, 16))
        self.top = RankList(sc, "Meilleurs élèves", "Les 5 plus hautes moyennes", "success")
        self.top.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=(0, 8), pady=(0, 16))
        self.low = RankList(sc, "Élèves à accompagner", "Les 5 plus faibles moyennes", "danger")
        self.low.grid(row=3, column=2, columnspan=2, sticky="nsew", padx=(8, 0), pady=(0, 16))

        # ===== Matières
        self.dt_mat = _block(
            t_mat, "Statistiques par matière",
            "Moy. classe max/min = meilleure/plus faible moyenne parmi les classes  •  "
            "Tranches : nombre d'élèves par intervalle de notes (0 à 20)",
            _cols(svc.H_MAT, 190, 92), page_size=8, search=True)

        # ===== Sexe : deux cartes côte à côte (pas de défilement imbriqué)
        t_sex.columnconfigure(0, weight=3, uniform="s")
        t_sex.columnconfigure(1, weight=2, uniform="s")
        t_sex.rowconfigure(0, weight=1)
        left = ctk.CTkFrame(t_sex, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        right = ctk.CTkFrame(t_sex, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self.dt_sexe = _block(left, "Résultats par sexe", "Admis = moyenne générale ≥ 10",
                              _cols(svc.H_SEXE, 110, 80), paginate=False, height=3)
        self.dt_msx = _block(right, "Moyenne par matière et par sexe", "Effectif et moyenne par matière",
                             _cols(svc.H_MAT_SEXE, 130, 90), page_size=6, height=6)

        # ===== Professeurs
        self.dt_prof = _block(
            t_prof, "Statistiques par professeur",
            "Réussite % = part des notes ≥ 10 dans les matières/classes du professeur",
            [("Professeur", 190), ("Matières", 220), ("Classes", 180), ("Élèves", 80),
             ("Moyenne", 90), ("Note min", 90), ("Note max", 90), ("Réussite %", 100)],
            page_size=8, search=True)

        # ===== Classes
        self.dt_cls = _block(t_cls, "Taux de réussite par classe et par sexe",
                             "G = Garçons  •  F = Filles  •  T = Total  •  Admis = moyenne générale ≥ 10",
                             _cols(svc.H_CLASSES, 150, 80), page_size=8)

        # ===== Classement
        self.dt_rank = _block(
            t_rank, "Classement par classe (du 1er au dernier)", "Les ex aequo partagent le même rang",
            [("Classe", 110), ("Rang", 70), ("Matricule", 120), ("Nom", 160),
             ("Prénoms", 170), ("Sexe", 60), ("Moyenne", 90), ("Décision", 90)],
            page_size=8, search=True, badge_cols=("Décision",))

    def _paint_tabs(self):
        """Texte blanc sur l'onglet sélectionné (fond bleu), texte normal sur les autres."""
        cur = self.tv.get()
        for name, btn in self.tv._segmented_button._buttons_dict.items():
            btn.configure(text_color="white" if name == cur else C["text"])

    def _reload_classes(self, y):
        rows = query("SELECT id, nom FROM classes WHERE annee_id=? ORDER BY nom", (y,))
        self.class_map = {r["nom"]: r["id"] for r in rows}
        keep = self.cb_cls.get()
        self.cb_cls.configure(values=[ALL] + list(self.class_map))
        self.cb_cls.set(keep if keep in self.class_map else ALL)

    def refresh(self):
        y = cur_year()
        self._reload_classes(y)
        per = self.cb_per.get()
        per = None if per in ("", ALL) else per
        cid = self.class_map.get(self.cb_cls.get())
        self.filter_label = f"{per or 'Toutes périodes'} / {self.cb_cls.get() or ALL}"
        self.data = d = svc.compute(svc.fetch_grades(y, per, cid), svc.fetch_teachers())
        s = d["summary"]
        n = s["eleves"]
        pct_echec = round(100 * s["echecs"] / n, 1) if n else 0

        c = self.cards
        c["eleves"].set(str(n), "cette sélection", f"{s['admis']} admis", "success")
        c["reussite"].set(f"{s['reussite']} %", "des élèves ≥ 10",
                          f"{s['admis']}/{n}", "success" if s["reussite"] >= 50 else "danger")
        c["moyenne"].set(f"{s['moyenne']:.2f}", "moyenne de l'ensemble", "/ 20",
                         "success" if s["moyenne"] >= 10 else "danger")
        c["echecs"].set(str(s["echecs"]), "moyenne < 10", f"{pct_echec} %", "danger")
        c["best"].set(f"{s['max']:.2f}", "meilleur résultat", "Top", "success")
        c["worst"].set(f"{s['min']:.2f}", "résultat le plus faible", "Bas", "danger")
        c["taux_g"].set(f"{s['taux_M']} %", "des garçons admis", "Garçons", "primary")
        c["taux_f"].set(f"{s['taux_F']} %", "des filles admises", "Filles", "warning")

        self.ch_subj.set([(x["matiere"], x["moyenne"]) for x in d["matieres"]])
        self.ch_pass.set([("Admis", s["admis"]), ("Échecs", s["echecs"])])
        self.ch_cls.set([(x["classe"], x["T"][2]) for x in d["classes"]])

        rk = d["ranking"]
        item = lambda x: (f"{x['nom']} {x['prenom']}".strip(), x["classe"], x["moyenne"])
        self.top.set([item(x) for x in sorted(rk, key=lambda x: -x["moyenne"])[:5]])
        self.low.set([item(x) for x in sorted(rk, key=lambda x: x["moyenne"])[:5]])

        self.dt_mat.set_rows(_fmt_rows(svc.rows_matieres(d)))
        self.dt_sexe.set_rows(_fmt_rows(svc.rows_sexes(d)))
        self.dt_msx.set_rows(_fmt_rows(svc.rows_matieres_sexe(d)))
        self.dt_prof.set_rows(_fmt_rows(svc.rows_profs(d)))
        self.dt_cls.set_rows(_fmt_rows(svc.rows_classes(d)))
        self.dt_rank.set_rows(_fmt_rows(svc.rows_ranking(d)))

    def export(self):
        if not self.data or not self.data["matieres"]:
            messagebox.showinfo("Statistiques", "Aucune donnée à exporter pour ce filtre.")
            return
        ensure_dirs()
        path = os.path.join(EXCEL_DIR, f"statistiques_{datetime.now():%Y%m%d_%H%M%S}.xlsx")
        try:
            svc.export_excel(self.data, path, self.filter_label)
        except ImportError:
            messagebox.showerror("Export", "Le module openpyxl est requis :\npip install openpyxl")
            return
        except PermissionError:
            messagebox.showerror("Export", "Impossible d'écrire le fichier. Fermez-le dans Excel et réessayez.")
            return
        messagebox.showinfo("Export réussi", f"Fichier créé :\n{path}")
        try:
            os.startfile(os.path.dirname(path))  # Windows
        except Exception:
            pass