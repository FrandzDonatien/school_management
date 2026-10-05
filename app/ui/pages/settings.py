import os
import shutil

import customtkinter as ctk
from tkinter import filedialog, messagebox

from app.calculations.schedule import check_hours
from app.config import ASSETS_DIR
from app.constants import C, R, SLOTS, TIME_KEYS
from app.repositories import schedule_repository
from app.services.settings_service import get_settings, load_plan, set_setting
from app.ui.components.buttons import button
from app.ui.components.card import card, label
from app.ui.components.icons import logo_ctk
from app.ui.components.inputs import combo, entry
from app.utils.dates import parse_time


class SettingsPage(ctk.CTkFrame):
    INFO = [("ecole_nom", "Nom de l'établissement", "Ex : Collège Moderne de la Réussite"),
            ("ministere", "Ministère de tutelle", "Ex : Ministère de l'Éducation Nationale"),
            ("direction", "Direction régionale", "Ex : Direction Régionale de l'Éducation Région des Plateaux-Est"),
            ("inspection", "Inspection / Circonscription", "Ex : IESG ATAKPAMÉ"),
            ("devise", "Devise de l'établissement", "Ex : EXCELLENCE-SAGESSE"),
            ("ville", "Ville", "Ex : Lomé"),
            ("directeur", "Nom du Directeur", "Ex : ADJINDA KOMLAN")]
    TIMES = [("matin_debut", "Début des cours (matin)", "07:00"),
             ("matin_fin", "Fin des cours (matin)", "12:00"),
             ("apres_debut", "Reprise (après-midi)", "15:00"),
             ("apres_fin", "Fin des cours (après-midi)", "17:00"),
             ("pause_debut", "Début de la récréation", "09:45"),
             ("pause_fin", "Fin de la récréation", "10:10"),
             ("duree_cours", "Durée d'un cours (minutes)", "55")]
    GEN = [("heures_hebdo", "Heures par enseignant / semaine", "21"),
           ("heures_libres", "Heures libres tolérées / semaine", "2")]

    def __init__(self, master, on_saved):
        super().__init__(master, fg_color=C["bg"])
        self.on_saved = on_saved
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        body = card(self)
        body.grid(row=0, column=0, sticky="nsew")
        sc = ctk.CTkScrollableFrame(body, fg_color="transparent")
        sc.pack(fill="both", expand=True, padx=10, pady=10)
        sc.columnconfigure(1, weight=1)

        # logo
        lg = ctk.CTkFrame(sc, fg_color=C["soft"], corner_radius=R, border_width=1, border_color=C["border"])
        lg.grid(row=0, column=0, sticky="n", padx=(14, 20), pady=14)
        label(lg, "Logo de l'école", 14, True).pack(padx=24, pady=(18, 8))
        self.logo_box = ctk.CTkFrame(lg, fg_color="transparent", width=160, height=140)
        self.logo_box.pack(padx=24)
        self.logo_box.pack_propagate(False)
        self.logo_lbl = None
        button(lg, "Choisir un logo…", self.choose_logo, ic="upload", width=170).pack(padx=24, pady=(12, 6))
        button(lg, "Retirer", self.remove_logo, "light", ic="x", width=170).pack(padx=24, pady=(0, 20))

        form = ctk.CTkFrame(sc, fg_color="transparent")
        form.grid(row=0, column=1, sticky="nsew", pady=14, padx=(0, 14))
        form.columnconfigure((0, 1), weight=1, uniform="f")
        self.entries = {}
        row = 0
        label(form, "Informations de l'établissement", 16, True).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 6))
        label(form, "Ces informations figurent dans l'en-tête du bulletin ; le nom de l'établissement "
                    "apparaît aussi en filigrane.", 11, color=C["muted"], wraplength=560, justify="left").grid(
            row=row + 1, column=0, columnspan=2, sticky="w", pady=(0, 10))
        row = self.add_fields(form, self.INFO, row + 2)
        label(form, "Horaires des cours", 16, True).grid(row=row, column=0, columnspan=2, sticky="w", pady=(20, 6))
        label(form, "Format : 07:00 ou 07h30. Les créneaux (1re heure, 2e heure…) sont calculés à partir de ces "
                    "valeurs. Modifier les horaires réinitialise les emplois du temps existants.", 11, color=C["muted"],
              wraplength=560, justify="left").grid(row=row + 1, column=0, columnspan=2, sticky="w", pady=(0, 10))
        row = self.add_fields(form, self.TIMES, row + 2)
        label(form, "Charge des enseignants", 16, True).grid(row=row, column=0, columnspan=2, sticky="w", pady=(20, 6))
        label(form, "Volume hebdomadaire par défaut (modifiable dans la fiche de chaque enseignant) et heures libres "
                    "(trous dans sa journée) tolérées par semaine.", 11, color=C["muted"], wraplength=560,
              justify="left").grid(row=row + 1, column=0, columnspan=2, sticky="w", pady=(0, 10))
        row = self.add_fields(form, self.GEN, row + 2)
        mb = ctk.CTkFrame(form, fg_color="transparent")
        mb.grid(row=row, column=0, sticky="ew", padx=(0, 12), pady=6)
        label(mb, "Répartition des heures libres", 12, color=C["muted"]).pack(anchor="w", pady=(0, 2))
        self.mode_cb = combo(mb, ["Enchaînées", "Réparties"])
        self.mode_cb.pack(fill="x")
        row += 1
        self.preview = label(form, "", 11, color=C["primary"], wraplength=560, justify="left")
        self.preview.grid(row=row, column=0, columnspan=2, sticky="w", pady=(8, 0))
        button(form, "Enregistrer les paramètres", self.save, ic="save", width=260).grid(row=row + 1, column=0, sticky="w", pady=24)

    def add_fields(self, form, fields, row):
        for n, (k, lab, ph) in enumerate(fields):
            r, c = divmod(n, 2)
            box = ctk.CTkFrame(form, fg_color="transparent")
            box.grid(row=row + r, column=c, sticky="ew", padx=(0, 12 if c == 0 else 0), pady=6)
            label(box, lab, 12, color=C["muted"]).pack(anchor="w", pady=(0, 2))
            self.entries[k] = entry(box, ph)
            self.entries[k].pack(fill="x")
        return row + (len(fields) + 1) // 2

    def update_preview(self):
        self.preview.configure(text=f"{len(SLOTS)} cours par jour : " + "  ·  ".join(f"{s}-{e}" for s, e in SLOTS))

    def refresh(self):
        S = get_settings()
        for k, e in self.entries.items():
            e.delete(0, "end")
            e.insert(0, S[k])
        self.show_logo()
        self.update_preview()
        self.mode_cb.set(S["mode_libres"] if S["mode_libres"] in ("Enchaînées", "Réparties") else "Enchaînées")

    def show_logo(self):
        if self.logo_lbl:
            self.logo_lbl.destroy()
        img = logo_ctk(130)
        self.logo_lbl = (ctk.CTkLabel(self.logo_box, image=img, text="") if img else
                         label(self.logo_box, "Aucun logo", 12, color=C["muted"]))
        self.logo_lbl.pack(expand=True)

    def choose_logo(self):
        p = filedialog.askopenfilename(title="Choisir le logo", filetypes=[("Images", "*.png *.jpg *.jpeg *.gif *.bmp")])
        if not p:
            return
        os.makedirs(ASSETS_DIR, exist_ok=True)
        dest = os.path.join(ASSETS_DIR, "logo" + os.path.splitext(p)[1].lower())
        shutil.copy2(p, dest)
        set_setting("logo", dest)
        self.show_logo()
        self.on_saved()

    def remove_logo(self):
        set_setting("logo", "")
        self.show_logo()
        self.on_saved()

    def save(self):
        if not self.entries["ecole_nom"].get().strip():
            messagebox.showwarning("Paramètres", "Le nom de l'établissement est obligatoire.")
            return
        labels = {k: lab for k, lab, _ in self.TIMES}
        v = {}
        for k in TIME_KEYS:
            t = parse_time(self.entries[k].get())
            if not t:
                messagebox.showwarning("Horaires", f"Heure invalide pour « {labels[k]} » (ex : 07:00 ou 07h30).")
                return
            v[k] = t
        try:
            v["duree_cours"] = str(int(self.entries["duree_cours"].get().strip()))
        except ValueError:
            messagebox.showwarning("Horaires", "La durée d'un cours doit être un nombre entier de minutes.")
            return
        err = check_hours(v)
        if err:
            messagebox.showwarning("Horaires", err)
            return
        try:
            hh, fl = int(self.entries["heures_hebdo"].get()), int(self.entries["heures_libres"].get())
            if not (1 <= hh <= 60 and 0 <= fl <= 10):
                raise ValueError
        except ValueError:
            messagebox.showwarning("Enseignants", "Heures par semaine : entier de 1 à 60 ; heures libres : entier de 0 à 10.")
            return
        set_setting("mode_libres", self.mode_cb.get())
        S = get_settings()
        if any(S[k] != v[k] for k in v) and schedule_repository.any_schedule():
            if not messagebox.askyesno("Horaires modifiés",
                                       "Modifier les horaires réinitialise tous les emplois du temps existants "
                                       "(toutes les années).\nContinuer ?"):
                return
            schedule_repository.clear_all()
        for k, e in self.entries.items():
            if k not in v:
                set_setting(k, e.get().strip())
        for k, val in v.items():
            set_setting(k, val)
            self.entries[k].delete(0, "end")
            self.entries[k].insert(0, val)
        load_plan()
        self.update_preview()
        self.on_saved()
        messagebox.showinfo("Paramètres", "Paramètres enregistrés. Ils seront utilisés sur les bulletins "
                                          "et les emplois du temps.")
