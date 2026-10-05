import customtkinter as ctk

from app.calculations.statistics import mean
from app.constants import C, PERIODES
from app.database.queries import cur_year
from app.repositories import class_repository, student_repository, subject_repository, teacher_repository
from app.services.grade_service import compute_class
from app.ui.components.card import StatCard, card, label
from app.ui.components.charts import Chart
from app.ui.components.data_table import DataTable


class DashboardPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=C["bg"])
        sc = ctk.CTkScrollableFrame(self, fg_color="transparent")
        sc.pack(fill="both", expand=True)
        sc.columnconfigure((0, 1, 2, 3), weight=1, uniform="a")
        self.stats = {}
        for i, (k, t, ic, col, lt) in enumerate([
            ("students", "Élèves inscrits", "cap", C["primary"], C["primary_light"]),
            ("teachers", "Enseignants", "user", C["success"], C["success_light"]),
            ("classes", "Classes", "school", C["warning"], C["warning_light"]),
            ("subjects", "Matières", "book", C["info"], C["info_light"])]):
            s = StatCard(sc, t, ic, col, lt)
            s.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 8, 0 if i == 3 else 8), pady=(0, 16))
            self.stats[k] = s

        self.ch_class = Chart(sc, "Élèves par classe", "bar")
        self.ch_class.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=(0, 8), pady=(0, 16))
        self.ch_sexe = Chart(sc, "Répartition par sexe", "donut", center="élèves")
        self.ch_sexe.grid(row=1, column=2, sticky="nsew", padx=8, pady=(0, 16))
        self.ch_statut = Chart(sc, "Nouveaux / Redoublants", "donut", center="élèves")
        self.ch_statut.grid(row=1, column=3, sticky="nsew", padx=(8, 0), pady=(0, 16))

        self.ch_avg = Chart(sc, "Moyenne générale par trimestre", "line", ymax=20)
        self.ch_avg.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=(0, 8), pady=(0, 16))
        self.ch_hours = Chart(sc, "Charge horaire par enseignant (top 8)", "hbar")
        self.ch_hours.grid(row=2, column=2, columnspan=2, sticky="nsew", padx=(8, 0), pady=(0, 16))

        self.ch_level = Chart(sc, "Élèves par niveau", "donut", center="élèves")
        self.ch_level.grid(row=3, column=0, sticky="nsew", padx=(0, 8))
        recent = card(sc)
        recent.grid(row=3, column=1, columnspan=3, sticky="nsew", padx=(8, 0))
        label(recent, "Derniers élèves inscrits", 15, True).pack(anchor="w", padx=20, pady=(16, 8))
        self.dt = DataTable(recent, [("Nom", 160), ("Prénoms", 160), ("Classe", 100), ("Matricule", 120)],
                            page_size=5, search=False)
        self.dt.pack(fill="both", expand=True, padx=20, pady=(0, 16))

    def refresh(self):
        y = cur_year()
        self.stats["students"].value.configure(text=str(student_repository.count(y)))
        self.stats["teachers"].value.configure(text=str(teacher_repository.count(y)))
        self.stats["classes"].value.configure(text=str(class_repository.count(y)))
        self.stats["subjects"].value.configure(text=str(subject_repository.count(y)))
        self.ch_class.set([(r[0], r[1]) for r in class_repository.students_per_class(y)])
        self.ch_sexe.set([(r[0], r[1]) for r in student_repository.count_by_sexe(y)])
        self.ch_statut.set([(r[0], r[1]) for r in student_repository.count_by_statut(y)])
        self.ch_level.set([(r[0], r[1]) for r in class_repository.students_per_level(y)])
        self.ch_hours.set([(r[0], r[1]) for r in teacher_repository.hours_per_teacher(y)])
        cids = class_repository.ids(y)
        self.ch_avg.set([(per.replace("Trimestre ", "T"),
                          mean([compute_class(cid, per)[2]["avg"] for cid in cids])) for per in PERIODES])
        self.dt.set_rows(student_repository.recent(y))
