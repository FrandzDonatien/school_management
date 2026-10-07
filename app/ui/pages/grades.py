"""Saisie des notes (par classe, matière et période)."""
import customtkinter as ctk
from tkinter import filedialog, messagebox

from app.calculations.grades import calc_mg
from app.constants import C, PERIODES
from app.database.queries import cur_year
from app.repositories import class_repository, class_subject_repository, grade_repository, student_repository
from app.services import grade_import_service, grade_service
from app.ui.components.buttons import button
from app.ui.components.card import card, label
from app.ui.components.dialogs import blocked
from app.ui.components.inputs import entry, labeled_combo
from app.utils.files import safe_name
from app.utils.validation import parse_note


class GradesPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=C["bg"])
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.classes, self.subjects, self.rows = {}, {}, {}

        top = card(self)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        top.columnconfigure((0, 1, 2), weight=1, uniform="g")
        self.class_cb = labeled_combo(top, 0, "Classe", lambda _=None: self.on_class())
        self.subject_cb = labeled_combo(top, 1, "Matière", lambda _=None: self.reload())
        self.period_cb = labeled_combo(top, 2, "Période", lambda _=None: self.reload(), PERIODES)
        self.period_cb.set(PERIODES[0])
        button(top, "Enregistrer les notes", self.save, ic="save", width=190).grid(
            row=0, column=3, padx=(6, 6), pady=(36, 16))
        button(top, "Importer depuis Excel", self.import_excel, "light", ic="file", width=190).grid(
            row=0, column=4, padx=(0, 6), pady=(36, 16))
        button(top, "Modèle Excel", self.download_template, "light", ic="download", width=140).grid(
            row=0, column=5, padx=(0, 18), pady=(36, 16))

        body = card(self)
        body.grid(row=1, column=0, sticky="nsew")
        body.rowconfigure(1, weight=1)
        body.columnconfigure(0, weight=1)
        self.title = label(body, "Notes", 16, True)
        self.title.grid(row=0, column=0, sticky="w", padx=22, pady=(20, 4))
        label(body, "Notes sur 20 • Moy. classe = (Interro + Devoir) / 2 • Moy. générale = (Moy. classe + Compo) / 2",
              11, color=C["muted"]).grid(row=0, column=0, sticky="e", padx=22)
        self.frame = ctk.CTkScrollableFrame(body, fg_color="transparent")
        self.frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 14))
        self.frame.columnconfigure(1, weight=1)

    def refresh(self):
        self.classes = class_repository.options(cur_year())
        self.class_cb.configure(values=list(self.classes) or [""])
        if self.class_cb.get() not in self.classes:
            self.class_cb.set(next(iter(self.classes), ""))
        self.on_class()

    def on_class(self):
        """Les matières proposées dépendent de la classe (voir « Matières par classe »)."""
        cid = self.classes.get(self.class_cb.get())
        self.subjects = class_subject_repository.options(cid, cur_year()) if cid else {}
        self.subject_cb.configure(values=list(self.subjects) or [""])
        if self.subject_cb.get() not in self.subjects:
            self.subject_cb.set(next(iter(self.subjects), ""))
        self.reload()

    def reload(self):
        for w in self.frame.winfo_children():
            w.destroy()
        self.rows = {}
        cid, sub, per = self.classes.get(self.class_cb.get()), self.subjects.get(self.subject_cb.get()), self.period_cb.get()
        self.title.configure(text=f"Notes — {self.subject_cb.get()} · {self.class_cb.get()}")
        for j, h in enumerate(["N°", "Élève", "Interrogation", "Devoir", "Composition", "Moy. générale"]):
            label(self.frame, h, 12, True, C["muted"]).grid(row=0, column=j, sticky="w", padx=8, pady=6)
        studs = student_repository.names_by_class(cid)
        if not studs:
            label(self.frame, "Aucun élève dans cette classe.", 12, color=C["muted"]).grid(row=1, column=0, columnspan=6, pady=20)
            return
        ex = grade_repository.for_subject(sub, per)
        for i, s in enumerate(studs, start=1):
            label(self.frame, str(i), 12, color=C["muted"]).grid(row=i, column=0, sticky="w", padx=8)
            label(self.frame, f"{s['nom'].upper()} {s['prenom']}", 12).grid(row=i, column=1, sticky="w", padx=8, pady=3)
            es = []
            for j, key in enumerate(["interro", "devoir", "compo"], start=2):
                e = entry(self.frame, "—", width=110)
                e.grid(row=i, column=j, padx=8, pady=3)
                v = ex[s["id"]][key] if s["id"] in ex else None
                if v is not None:
                    e.insert(0, f"{v:g}")
                e.bind("<KeyRelease>", lambda _e, sid=s["id"]: self.update_row(sid))
                es.append(e)
            lbl = label(self.frame, "", 12, True, C["primary"])
            lbl.grid(row=i, column=5, sticky="w", padx=8)
            self.rows[s["id"]] = (es, lbl)
            self.update_row(s["id"])

    def update_row(self, sid):
        es, lbl = self.rows[sid]
        vals = [parse_note(e.get()) for e in es]
        if not all(ok for ok, _ in vals):
            lbl.configure(text="Invalide", text_color=C["danger"])
            return
        _, mg = calc_mg(*[v for _, v in vals])
        lbl.configure(text="—" if mg is None else f"{mg:.2f}", text_color=C["primary"])

    def save(self):
        if blocked():
            return
        if not self.subjects.get(self.subject_cb.get()):
            messagebox.showinfo("Notes", "Cette classe n'a aucune matière : créez-en dans la page « Matières ».")
            return
        sub, per = self.subjects.get(self.subject_cb.get()), self.period_cb.get()
        data = {}
        for sid, (es, _) in self.rows.items():
            vals = [parse_note(e.get()) for e in es]
            if not all(ok for ok, _ in vals):
                messagebox.showwarning("Note invalide", "Chaque note doit être un nombre compris entre 0 et 20.")
                return
            data[sid] = tuple(v for _, v in vals)
        grade_service.save_grades(sub, per, data)
        messagebox.showinfo("Notes", "Notes enregistrées avec succès.")

    # -- import / modèle Excel
    def current_students(self):
        cid = self.classes.get(self.class_cb.get())
        return student_repository.names_by_class(cid) if cid else []

    def download_template(self):
        studs = self.current_students()
        if not studs:
            messagebox.showinfo("Modèle Excel", "Sélectionnez une classe contenant des élèves.")
            return
        cls, sub, per = self.class_cb.get(), self.subject_cb.get(), self.period_cb.get()
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx", initialfile=safe_name(f"Notes_{cls}_{sub}_{per}") + ".xlsx",
            filetypes=[("Excel", "*.xlsx")])
        if not path:
            return
        try:
            grade_import_service.write_template(path, studs, f"Notes — {sub} · {cls} · {per}")
        except ImportError:
            messagebox.showerror("Modèle Excel", "Le module openpyxl est requis :  pip install openpyxl")
            return
        except Exception as ex:
            messagebox.showerror("Modèle Excel", f"Échec de la création du fichier :\n{ex}")
            return
        messagebox.showinfo("Modèle Excel", "Modèle créé. Remplissez les notes puis importez le fichier.")

    def import_excel(self):
        if blocked():
            return
        if not self.subjects.get(self.subject_cb.get()):
            messagebox.showinfo("Notes", "Cette classe n'a aucune matière : créez-en dans la page « Matières ».")
            return
        if not self.rows:
            messagebox.showinfo("Import", "Sélectionnez une classe contenant des élèves.")
            return
        path = filedialog.askopenfilename(title="Importer les notes depuis Excel",
                                          filetypes=[("Excel", "*.xlsx *.xlsm")])
        if not path:
            return
        try:
            res = grade_import_service.parse_file(path, self.current_students())
        except ImportError:
            messagebox.showerror("Import", "Le module openpyxl est requis :  pip install openpyxl")
            return
        except ValueError as ex:
            messagebox.showerror("Import impossible", str(ex))
            return
        except Exception as ex:
            messagebox.showerror("Import", f"Impossible de lire le fichier :\n{ex}")
            return
        fields = grade_import_service.FIELDS
        for sid, vals in res["grades"].items():
            es, _ = self.rows[sid]
            for key, v in vals.items():
                e = es[fields.index(key)]
                e.delete(0, "end")
                e.insert(0, f"{v:g}")
            self.update_row(sid)

        def preview(items):
            return "\n".join(f"  • {x}" for x in items[:8]) + (f"\n  … (+{len(items) - 8})" if len(items) > 8 else "")

        msg = f"{len(res['grades'])} élève(s) mis à jour sur {res['rows']} ligne(s) lues."
        if res["unmatched"]:
            msg += f"\n\n{len(res['unmatched'])} ligne(s) sans élève correspondant dans cette classe :\n" + preview(res["unmatched"])
        if res["invalid"]:
            msg += f"\n\n{len(res['invalid'])} valeur(s) ignorée(s) (note invalide) :\n" + preview(res["invalid"])
        msg += "\n\nLes notes ne sont pas encore enregistrées : vérifiez-les puis cliquez sur « Enregistrer les notes »."
        (messagebox.showwarning if res["unmatched"] or res["invalid"] else messagebox.showinfo)("Import Excel", msg)