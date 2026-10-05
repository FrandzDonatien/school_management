import customtkinter as ctk

from app.constants import C, FONT
from app.database.connection import query
from app.database.queries import active_year, cur_year, set_view_year
from app.services.settings_service import get_settings
from app.ui.components.buttons import button
from app.ui.components.card import label
from app.ui.components.icons import icon, logo_ctk
from app.ui.components.inputs import combo
from app.ui.pages.bulletins import BulletinPage
from app.ui.pages.classes import classes_page
from app.ui.pages.dashboard import DashboardPage
from app.ui.pages.grades import GradesPage
from app.ui.pages.schedule import SchedulePage
from app.ui.pages.school_years import YearsPage
from app.ui.pages.settings import SettingsPage
from app.ui.pages.students import students_page
from app.ui.pages.subjects import subjects_page
from app.ui.pages.teachers import TeachersPage
from app.utils.dates import date_fr


class MainFrame(ctk.CTkFrame):
    MENU = [("dashboard", "Tableau de bord", "grid"), ("students", "Élèves", "cap"),
            ("teachers", "Enseignants", "user"), ("subjects", "Matières", "book"),
            ("classes", "Classes", "school"),
            ("grades", "Saisie des notes", "pencil"), ("bulletins", "Bulletins de notes", "file"),
            ("schedule", "Emploi du temps", "clock"), ("years", "Années scolaires", "calendar"),
            ("settings", "Paramètres", "gear")]

    def __init__(self, master, username, on_logout):
        super().__init__(master, fg_color=C["bg"], corner_radius=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.current_key = "dashboard"
        self.year_map = {}

        self.side = ctk.CTkFrame(self, fg_color=C["sidebar"], corner_radius=0, width=270)
        self.side.grid(row=0, column=0, sticky="ns")
        self.side.grid_propagate(False)
        self.brand = None
        self.build_brand()
        label(self.side, "MENU", 11, True, "#8A99AF").pack(anchor="w", padx=28, pady=(0, 8))
        self.titles = {k: t for k, t, _ in self.MENU}
        self.btns = {}
        for key, text, ic in self.MENU:
            b = ctk.CTkButton(self.side, text="  " + text, image=icon(ic, C["sidebar_text"], 20), compound="left",
                              anchor="w", height=42, corner_radius=8, fg_color="transparent",
                              hover_color=C["sidebar_hover"], text_color=C["sidebar_text"], font=(FONT, 13),
                              command=lambda k=key: self.show(k))
            b.pack(fill="x", padx=16, pady=2)
            self.btns[key] = b

        right = ctk.CTkFrame(self, fg_color=C["bg"], corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)
        header = ctk.CTkFrame(right, fg_color="white", corner_radius=0, height=76)
        header.grid(row=0, column=0, sticky="ew")
        header.pack_propagate(False)
        tbox = ctk.CTkFrame(header, fg_color="transparent")
        tbox.pack(side="left", padx=28)
        self.title = label(tbox, "", 22, True)
        self.title.pack(anchor="w", pady=(14, 0))
        self.sub = label(tbox, "", 11, color=C["muted"])
        self.sub.pack(anchor="w")
        button(header, "Déconnexion", on_logout, "light", ic="logout", width=130).pack(side="right", padx=(10, 24))
        self.year_cb = combo(header, [""], command=self.on_year_pick, width=190)
        self.year_cb.pack(side="right", padx=(0, 14))
        label(header, "Année scolaire", 11, color=C["muted"]).pack(side="right", padx=(0, 8))
        ub = ctk.CTkFrame(header, fg_color="transparent")
        ub.pack(side="right", padx=(0, 18))
        label(ub, username, 13, True).pack(anchor="e", pady=(16, 0))
        ctk.CTkLabel(header, text=username[:2].upper(), width=42, height=42, corner_radius=21, fg_color=C["primary"],
                     text_color="white", font=(FONT, 13, "bold")).pack(side="right", padx=12)

        self.banner = ctk.CTkFrame(right, fg_color=C["warning_light"], corner_radius=0, height=40)
        self.banner.grid(row=1, column=0, sticky="ew")
        self.banner.pack_propagate(False)
        ctk.CTkLabel(self.banner, text="", image=icon("lock", "#92400E", 18)).pack(side="left", padx=(28, 8))
        self.banner_lbl = label(self.banner, "", 12, True, "#92400E")
        self.banner_lbl.pack(side="left")

        area = ctk.CTkFrame(right, fg_color=C["bg"], corner_radius=0)
        area.grid(row=2, column=0, sticky="nsew", padx=24, pady=24)
        area.columnconfigure(0, weight=1)
        area.rowconfigure(0, weight=1)
        self.pages = {
            "dashboard": DashboardPage(area), "students": students_page(area), "teachers": TeachersPage(area),
            "subjects": subjects_page(area), "classes": classes_page(area),
            "grades": GradesPage(area), "bulletins": BulletinPage(area), "schedule": SchedulePage(area),
            "years": YearsPage(area, self.on_years_changed), "settings": SettingsPage(area, self.build_brand),
        }
        for p in self.pages.values():
            p.grid(row=0, column=0, sticky="nsew")
        self.update_year_box()
        self.show("dashboard")

    def update_year_box(self):
        act, cur = active_year(), cur_year()
        self.year_map = {r["libelle"] + ("  (active)" if r["id"] == act else ""): r["id"]
                         for r in query("SELECT id, libelle FROM years ORDER BY libelle DESC")}
        self.year_cb.configure(values=list(self.year_map) or [""])
        for k, v in self.year_map.items():
            if v == cur:
                self.year_cb.set(k)
        self.update_sub()
        if cur != act:
            lab = query("SELECT libelle FROM years WHERE id=?", (cur,))[0]["libelle"]
            self.banner_lbl.configure(text=f"Consultation de l'année {lab} — lecture seule. Pour la modifier, "
                                           "définissez-la comme année active (page « Années scolaires »).")
            self.banner.grid()
        else:
            self.banner.grid_remove()

    def on_year_pick(self, value):
        y = self.year_map.get(value)
        if y is None:
            return
        set_view_year(None if y == active_year() else y)
        self.update_year_box()
        self.pages[self.current_key].refresh()

    def on_years_changed(self):
        self.update_year_box()

    def update_sub(self):
        self.sub.configure(text=f"{date_fr()}  •  Année scolaire {get_settings()['annee']}")

    def build_brand(self):
        if self.brand:
            self.brand.destroy()
        S = get_settings()
        self.brand = ctk.CTkFrame(self.side, fg_color="transparent")
        self.brand.pack(fill="x", padx=22, pady=(26, 24), before=self.side.winfo_children()[0] if self.side.winfo_children()[0] is not self.brand else None)
        img = logo_ctk(44)
        if img:
            ctk.CTkLabel(self.brand, image=img, text="").pack(side="left")
        else:
            ctk.CTkLabel(self.brand, text="", image=icon("cap", "#FFFFFF", 26), width=44, height=44, corner_radius=12,
                         fg_color=C["primary"]).pack(side="left")
        label(self.brand, S["ecole_nom"], 14, True, "white", wraplength=170, justify="left").pack(side="left", padx=10)

    def show(self, key):
        self.current_key = key
        for k, b in self.btns.items():
            ic = next(i for kk, _, i in self.MENU if kk == k)
            active = k == key
            b.configure(fg_color=C["primary"] if active else "transparent",
                        text_color="white" if active else C["sidebar_text"],
                        hover_color=C["primary_dark"] if active else C["sidebar_hover"],
                        image=icon(ic, "#FFFFFF" if active else C["sidebar_text"], 20))
        self.title.configure(text=self.titles[key])
        self.update_year_box()
        page = self.pages[key]
        page.refresh()
        page.tkraise()
