"""Emploi du temps : affectation des cours, génération automatique, calendrier, exports."""
import datetime
import threading

import customtkinter as ctk
from tkinter import filedialog, messagebox

from app.constants import C, DAYS, FONT, PALETTE, PLAN, SLOTS
from app.database.queries import cur_year
from app.database.seed import load_example_data
from app.repositories import class_repository, schedule_repository, teacher_repository
from app.services import export_service, schedule_service
from app.services.schedule_service import ScheduleError
from app.services.settings_service import default_hours, free_params
from app.services.teacher_service import teacher_target
from app.ui.components.buttons import button
from app.ui.components.card import card, label
from app.ui.components.data_table import DataTable
from app.ui.components.dialogs import ExportDialog, ProgressDialog, blocked
from app.ui.components.inputs import combo, entry
from app.utils.formatting import ordinal

LEFT_W = 400
WRAP = LEFT_W - 100


def load_example(page):
    if blocked():
        return
    if not messagebox.askyesno("Exemple de l'établissement",
                               "Ajouter à l'année affichée les matières, enseignants, classes, titulaires et "
                               "affectations issus de vos documents ?\n(Les éléments existants ne sont pas dupliqués.)\n"
                               "Certains enseignants peuvent dépasser l'objectif horaire : ajustez leur fiche."):
        return
    load_example_data(cur_year())
    page.refresh()
    messagebox.showinfo("Exemple chargé", "Données chargées. Vous pouvez générer l'emploi du temps.")


class SchedulePage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=C["bg"])
        self.columnconfigure(0, minsize=LEFT_W)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.teachers, self.cls_map, self.views, self.cells, self.scope_map = {}, {}, {}, {}, {}
        self.plan_sig = None
        self.rows = {}

        left = card(self)
        # sticky="nsew" : le panneau remplit toute la colonne (largeur = LEFT_W via minsize),
        # même si card() ignore le paramètre width.
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        left.grid_propagate(False)
        sc = ctk.CTkScrollableFrame(left, fg_color="transparent")
        sc.pack(fill="both", expand=True, padx=6, pady=6)
        label(sc, "1. Affectation des cours", 16, True).pack(anchor="w", padx=14, pady=(10, 2))
        label(sc, "Choisissez l'enseignant puis saisissez ses heures dans chaque classe. La matière enseignée "
                  "est déduite de sa fiche.", 11, color=C["muted"], justify="left", wraplength=WRAP).pack(
            anchor="w", padx=14, pady=(0, 6))
        label(sc, "Enseignant", 12, color=C["muted"]).pack(anchor="w", padx=14, pady=(6, 2))
        self.t_cb = combo(sc, [""], command=lambda _=None: self.load_teacher())
        self.t_cb.pack(fill="x", padx=14)
        self.t_info = label(sc, "", 11, color=C["muted"], justify="left", wraplength=WRAP)
        self.t_info.pack(anchor="w", padx=14, pady=(6, 2))
        self.box = ctk.CTkFrame(sc, fg_color=C["soft"], border_width=1, border_color=C["border"], corner_radius=8)
        self.box.pack(fill="x", padx=14, pady=(4, 4))
        self.total = label(sc, "", 12, True, C["primary"])
        self.total.pack(anchor="w", padx=14, pady=(2, 6))
        button(sc, "Enregistrer l'affectation", self.save_assign, ic="save").pack(fill="x", padx=14, pady=(0, 6))
        ctk.CTkFrame(sc, height=1, fg_color=C["border"]).pack(fill="x", padx=14, pady=14)

        label(sc, "2. Génération automatique", 16, True).pack(anchor="w", padx=14, pady=(0, 6))
        label(sc, "Portée", 12, color=C["muted"]).pack(anchor="w", padx=14, pady=(4, 2))
        self.scope_cb = combo(sc, ["Toutes les classes"])
        self.scope_cb.pack(fill="x", padx=14)
        button(sc, "Générer l'emploi du temps", self.generate, ic="zap").pack(fill="x", padx=14, pady=(14, 6))
        button(sc, "Vider (selon la portée)", self.clear_schedule, "danger", ic="trash").pack(fill="x", padx=14, pady=6)
        button(sc, "Charger l'exemple de l'établissement", lambda: load_example(self), "light",
               ic="layers").pack(fill="x", padx=14, pady=6)
        self.status = label(sc, "", 12, True, C["primary"], justify="left")
        self.status.pack(anchor="w", padx=14, pady=(10, 4))
        self.rules = label(sc, "", 11, color=C["muted"], justify="left", wraplength=WRAP)
        self.rules.pack(anchor="w", padx=14, pady=4)

        right = card(self)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)
        head = ctk.CTkFrame(right, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=22, pady=(18, 8))
        label(head, "Emploi du temps", 16, True).pack(side="left")
        self.tabs = ctk.CTkSegmentedButton(head, values=["Calendrier", "Affectations", "Charges"],
                                           command=self.switch, selected_color=C["primary"],
                                           selected_hover_color=C["primary_dark"], unselected_color="#EEF2F7",
                                           fg_color="#EEF2F7", text_color=C["text"], font=(FONT, 12, "bold"))
        self.tabs.set("Calendrier")
        self.tabs.pack(side="left", padx=18)
        button(head, "Exporter", self.export, "light", ic="download", width=120).pack(side="right", padx=(8, 0))
        self.view_cb = combo(head, [""], command=lambda _=None: self.render_calendar(), width=240)
        self.view_cb.pack(side="right")

        self.cal = ctk.CTkFrame(right, fg_color="transparent")
        self.cal.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 16))

        self.aff = ctk.CTkFrame(right, fg_color="transparent")
        self.aff.rowconfigure(0, weight=1)
        self.aff.columnconfigure(0, weight=1)
        self.aff_dt = DataTable(self.aff, [("Classe", 110), ("Matière", 170), ("Enseignant", 190),
                                           ("Heures / sem.", 110)])
        self.aff_dt.grid(row=0, column=0, sticky="nsew")

        self.rec = ctk.CTkFrame(right, fg_color="transparent")
        self.rec.rowconfigure(0, weight=1)
        self.rec.columnconfigure(0, weight=1)
        self.load_dt = DataTable(self.rec, [("Enseignant", 160), ("Matières", 130), ("Objectif", 80),
                                            ("Attribuées", 90), ("Placées", 80), ("État", 130)])
        self.load_dt.grid(row=0, column=0, sticky="nsew")

    # -- affectation des cours (enseignant -> classes, heures)
    def hours_of(self, e):
        raw = e.get().strip()
        if not raw:
            return 0
        return int(raw) if raw.isdigit() else None

    def load_teacher(self):
        for w in self.box.winfo_children():
            w.destroy()
        self.rows = {}
        self.total.configure(text="")
        tid = self.teachers.get(self.t_cb.get())
        if not tid:
            self.t_info.configure(text="Aucun enseignant : créez-en dans la page « Enseignants ».")
            return
        subs = teacher_repository.subjects_of(tid)
        if not subs:
            self.t_info.configure(text="Aucune matière attribuée à cet enseignant : cochez-en dans sa fiche "
                                       "(page « Enseignants »).")
            return
        self.t_info.configure(text="Matières : " + ", ".join(s["code"] or s["nom"] for s in subs) +
                                   f"\nObjectif : {teacher_target(tid)} h / semaine")
        classes = class_repository.by_year(cur_year())
        ex = schedule_repository.assignments_map(cur_year())
        self.box.columnconfigure(0, weight=1)
        r = 0
        for cl in classes:
            for s in subs:
                a = ex.get((cl["id"], s["id"]))
                other = a and a["hours"] and a["teacher_id"] not in (None, tid)
                txt = f"{cl['nom']}  ·  {s['code'] or s['nom']}"
                if other:
                    txt += f"\n(actuellement : {a['tname']})"
                label(self.box, txt, 12, justify="left").grid(row=r, column=0, sticky="w", padx=10, pady=4)
                e = entry(self.box, "0", width=60)
                e.grid(row=r, column=1, padx=10, pady=4)
                if a and a["teacher_id"] == tid and a["hours"]:
                    e.insert(0, str(a["hours"]))
                e.bind("<KeyRelease>", lambda _e: self.update_total())
                self.rows[(cl["id"], s["id"])] = e
                r += 1
        self.update_total()

    def update_total(self):
        tid = self.teachers.get(self.t_cb.get())
        if not tid or not self.rows:
            return
        tgt = teacher_target(tid)
        tot = sum(h for h in (self.hours_of(e) for e in self.rows.values()) if h)
        col = C["success"] if tot == tgt else C["danger"] if tot > tgt else "#B45309"
        self.total.configure(text=f"Total : {tot} h / {tgt} h par semaine", text_color=col)

    def save_assign(self):
        if blocked():
            return
        tid = self.teachers.get(self.t_cb.get())
        if not tid or not self.rows:
            messagebox.showinfo("Affectation", "Sélectionnez un enseignant ayant au moins une matière.")
            return
        data = {}
        for key, e in self.rows.items():
            h = self.hours_of(e)
            if h is None or h > 20:
                messagebox.showwarning("Affectation", "Les heures doivent être des entiers compris entre 0 et 20.")
                return
            data[key] = h
        tgt, tot = schedule_service.assignment_totals(tid, data)
        if tot > tgt:
            messagebox.showwarning("Charge dépassée", f"Total de {tot} h alors que l'objectif est de {tgt} h par "
                                                      "semaine. Réduisez les heures (ou modifiez l'objectif dans "
                                                      "la fiche de l'enseignant).")
            return
        taken = schedule_service.taken_assignments(tid, data)
        if taken and not messagebox.askyesno("Cours déjà attribués", f"{len(taken)} cours sont déjà attribués à un "
                                                                      "autre enseignant. Les reprendre ?"):
            return
        schedule_service.save_assignment(tid, data)
        self.refresh()
        msg = "Affectation enregistrée."
        if tot < tgt:
            msg += f"\nIl manque {tgt - tot} h pour atteindre l'objectif de {tgt} h."
        messagebox.showinfo("Affectation", msg + "\nRégénérez l'emploi du temps pour la prendre en compte.")

    def render_aff(self):
        self.aff_dt.set_rows(schedule_repository.assignments_view(cur_year()))

    # -- calendrier
    def rebuild_calendar(self):
        for w in self.cal.winfo_children():
            w.destroy()
        self.cells = {}
        self.build_calendar()
        self.plan_sig = tuple(PLAN)

    def build_calendar(self):
        cal = self.cal
        for r in range(40):
            cal.rowconfigure(r, weight=0, uniform="", minsize=0)
        cal.columnconfigure(0, minsize=92)
        for c in range(1, len(DAYS) + 1):
            cal.columnconfigure(c, weight=1, uniform="day")
        today = datetime.date.today().weekday()
        for d, name in enumerate(DAYS):
            hl = d == today
            ctk.CTkLabel(cal, text=name, font=(FONT, 12, "bold"), height=34, corner_radius=8,
                         text_color="white" if hl else C["text"],
                         fg_color=C["primary"] if hl else "#F1F5F9").grid(row=0, column=1 + d, padx=3, pady=3, sticky="ew")
        r, si = 1, 0
        for kind, lab, s, e in PLAN:
            if kind == "slot":
                cal.rowconfigure(r, weight=1, uniform="slot")
                label(cal, f"{ordinal(si)}\n{s}-{e}", 10, True, C["muted"]).grid(row=r, column=0, padx=4)
                for d in range(len(DAYS)):
                    f = ctk.CTkFrame(cal, fg_color=C["soft"], corner_radius=10, height=44, border_width=1,
                                     border_color=C["border"])
                    f.grid(row=r, column=1 + d, padx=3, pady=3, sticky="nsew")
                    f.pack_propagate(False)
                    l1 = ctk.CTkLabel(f, text="", font=(FONT, 11, "bold"), anchor="w")
                    l2 = ctk.CTkLabel(f, text="", font=(FONT, 10), anchor="w")
                    l1.pack(fill="x", padx=10, pady=(5, 0))
                    l2.pack(fill="x", padx=10)
                    self.cells[(d, si)] = (f, l1, l2)
                si += 1
            else:
                ctk.CTkLabel(cal, text=f"{lab}  ·  {s} – {e}", font=(FONT, 10, "bold"), height=22, corner_radius=6,
                             text_color=C["muted"], fg_color="#EEF2F7").grid(row=r, column=0, columnspan=len(DAYS) + 1,
                                                                             sticky="ew", padx=3, pady=2)
            r += 1

    def switch(self, value):
        for w in (self.cal, self.aff, self.rec):
            w.grid_remove()
        if value == "Calendrier":
            self.cal.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 16))
        elif value == "Affectations":
            self.aff.grid(row=1, column=0, sticky="nsew", padx=22, pady=(0, 16))
            self.render_aff()
        else:
            self.rec.grid(row=1, column=0, sticky="nsew", padx=22, pady=(0, 16))
            self.render_loads()

    def refresh(self):
        if self.plan_sig != tuple(PLAN):
            self.rebuild_calendar()
        y = cur_year()
        self.teachers = teacher_repository.options(y)
        classes = class_repository.by_year(y)
        self.cls_map = {r["nom"]: r["id"] for r in classes}
        self.scope_map = {"Toutes les classes": None}
        self.scope_map.update({f"Classe : {r['nom']}": r["id"] for r in classes})
        self.scope_cb.configure(values=list(self.scope_map))
        if self.scope_cb.get() not in self.scope_map:
            self.scope_cb.set("Toutes les classes")
        self.t_cb.configure(values=list(self.teachers) or [""])
        if self.t_cb.get() not in self.teachers:
            self.t_cb.set(next(iter(self.teachers), ""))
        self.load_teacher()
        self.views = {f"Classe : {r['nom']}": ("c", r["id"]) for r in classes}
        self.views.update({f"Enseignant : {n}": ("t", i) for n, i in self.teachers.items()})
        self.view_cb.configure(values=list(self.views) or [""])
        if self.view_cb.get() not in self.views:
            self.view_cb.set(next(iter(self.views), ""))
        f, m = free_params()
        forme = f"enchaînées (une plage de {f} h)" if m.startswith("Ench") else "réparties (1 h sur plusieurs jours)"
        self.rules.configure(text=(
            "• Aucun chevauchement : un enseignant n'est jamais dans deux classes au même moment.\n"
            f"• Volume par défaut : {default_hours()} h/semaine par enseignant (paramétrable).\n"
            f"• Heures libres tolérées : {f} h/semaine, {forme}.\n"
            "• Les cours d'un enseignant sont répartis sur différents créneaux, pas seulement la 1re heure.\n"
            "• Une portée « Classe » conserve les autres classes en place."))
        self.render_calendar()
        self.render_aff()
        self.render_loads()
        self.update_status()

    def update_status(self):
        need, placed = schedule_service.status()
        self.status.configure(text=f"Cours à placer : {need}\nCours placés : {placed}",
                              text_color=C["success"] if need and need == placed else C["primary"])

    def render_calendar(self):
        for f, l1, l2 in self.cells.values():
            f.configure(fg_color=C["soft"], border_color=C["border"])
            l1.configure(text="")
            l2.configure(text="")
        v = self.views.get(self.view_cb.get())
        if not v:
            return
        mode = v[0]
        for (d, s), x in schedule_service.cell_data(*v).items():
            cell = self.cells.get((d, s))
            if not cell:
                continue
            f, l1, l2 = cell
            bg, fg = PALETTE[x["key"] % len(PALETTE)]
            f.configure(fg_color=bg, border_color=bg)
            if mode == "c":
                l1.configure(text=x["subj"], text_color=fg)
                l2.configure(text=x["teacher"], text_color=fg)
            else:
                l1.configure(text=x["cls"], text_color=fg)
                l2.configure(text=x["subj"], text_color=fg)

    def render_loads(self):
        self.load_dt.set_rows(schedule_service.load_table())

    # -- génération
    def scope_ids(self):
        sel = self.scope_map.get(self.scope_cb.get())
        return list(self.cls_map.values()) if sel is None else [sel]

    def generate(self):
        if blocked():
            return
        cids = self.scope_ids()
        if not cids:
            messagebox.showwarning("Génération", "Créez d'abord des classes.")
            return
        try:
            prep = schedule_service.prepare_generation(cids, self.cls_map)
        except ScheduleError as ex:
            (messagebox.showwarning if ex.level == "warning" else messagebox.showerror)(ex.title, ex.message)
            return
        diff = prep["diff"]
        if diff and not messagebox.askyesno(
                "Volume horaire", "Ces enseignants n'ont pas exactement leur volume hebdomadaire :\n\n" +
                                  "\n".join(diff[:12]) + ("\n…" if len(diff) > 12 else "") +
                                  "\n\nGénérer quand même ?"):
            return
        if prep["existing"] and not messagebox.askyesno(
                "Remplacer l'emploi du temps", "L'emploi du temps existant de cette portée sera remplacé.\nContinuer ?"):
            return

        solver = schedule_service.make_solver(prep)
        state, result = dict(hard="…", steps=0), {}

        def work():
            try:
                result["grid"], result["info"] = solver.solve(30.0, 6.0, lambda h, s: state.update(hard=h, steps=s))
            except Exception as ex:
                result["err"] = ex
            result["done"] = True

        dlg = ProgressDialog(self, "Génération", "Génération de l'emploi du temps…",
                             "Recherche d'une organisation sans conflit",
                             lambda: setattr(solver, "stop", True))
        threading.Thread(target=work, daemon=True).start()

        def poll():
            if not result.get("done"):
                dlg.set_info(f"Conflits restants : {state['hard']}   •   essais : {state['steps']:,}".replace(",", " "))
                self.after(200, poll)
                return
            dlg.close()
            self.finish_generation(result, cids)

        self.after(200, poll)

    def finish_generation(self, result, cids):
        if "err" in result:
            messagebox.showerror("Génération", f"Erreur pendant la génération :\n{result['err']}")
            return
        grid = result.get("grid")
        if grid is None:
            info = result.get("info") or {}
            messagebox.showerror("Génération impossible",
                                 f"Aucune organisation sans conflit trouvée (conflits restants : {info.get('hard', '?')}).\n"
                                 "Vérifiez les volumes horaires des enseignants et des classes.")
            return
        n = schedule_service.save_generated(grid, cids)
        self.tabs.set("Calendrier")
        self.switch("Calendrier")
        self.refresh()
        messagebox.showinfo("Emploi du temps généré", f"{n} cours placés pour {len(grid)} classe(s), sans aucun chevauchement.")

    def clear_schedule(self):
        if blocked():
            return
        cids = self.scope_ids()
        if not cids:
            return
        if messagebox.askyesno("Vider", "Supprimer l'emploi du temps de la portée sélectionnée ?"):
            schedule_service.clear(cids)
            self.refresh()

    # -- export
    def export(self):
        if not self.cls_map and not self.teachers:
            messagebox.showinfo("Export", "Aucun emploi du temps à exporter.")
            return
        v = self.views.get(self.view_cb.get())
        scope = "general"
        cname = tname = ""
        if v:
            if v[0] == "t":
                scope, tname = "enseignant", self.view_cb.get().replace("Enseignant : ", "", 1)
            else:
                scope, cname = "classe", self.view_cb.get().replace("Classe : ", "", 1)
        ExportDialog(self, self.cls_map, self.teachers, scope, cname, tname, self.do_export)

    def do_export(self, scope, cid, tid, fmt_):
        tables, base = export_service.build_tables(scope, cid, tid, self.cls_map, self.teachers)
        if not tables:
            messagebox.showinfo("Export", "Rien à exporter.")
            return
        ext = ".xlsx" if fmt_ == "xlsx" else ".html"
        path = filedialog.asksaveasfilename(
            defaultextension=ext, initialfile=base + ext,
            filetypes=[("Excel", "*.xlsx")] if fmt_ == "xlsx" else [("Page web imprimable (PDF)", "*.html")])
        if not path:
            return
        try:
            export_service.write_file(path, tables, fmt_)
        except ImportError:
            messagebox.showerror("Export", "Le module openpyxl est requis :  pip install openpyxl\n"
                                           "(ou exportez au format PDF / page imprimable).")
            return
        except Exception as ex:
            messagebox.showerror("Export", f"Échec de l'export :\n{ex}")
            return
        messagebox.showinfo("Export", "Export terminé avec succès.")