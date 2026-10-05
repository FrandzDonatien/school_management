import customtkinter as ctk

from app.constants import C, FONT
from app.services import auth_service
from app.services.settings_service import get_settings
from app.ui.components.buttons import button
from app.ui.components.card import label
from app.ui.components.icons import icon, logo_ctk
from app.ui.components.inputs import entry


class LoginFrame(ctk.CTkFrame):
    def __init__(self, master, on_success):
        super().__init__(master, fg_color="white", corner_radius=0)
        self.on_success = on_success
        self.columnconfigure(0, weight=1, uniform="x")
        self.columnconfigure(1, weight=1, uniform="x")
        self.rowconfigure(0, weight=1)
        S = get_settings()

        left = ctk.CTkFrame(self, fg_color=C["sidebar"], corner_radius=0)
        left.grid(row=0, column=0, sticky="nsew")
        inner = ctk.CTkFrame(left, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")
        img = logo_ctk(110)
        if img:
            ctk.CTkLabel(inner, image=img, text="").pack(pady=(0, 10))
        else:
            ctk.CTkLabel(inner, text="", image=icon("cap", "#FFFFFF", 56), width=96, height=96, corner_radius=24,
                         fg_color=C["primary"]).pack()
        label(inner, S["ecole_nom"], 28, True, "white", wraplength=380, justify="center").pack(pady=(14, 4))
        label(inner, "Plateforme de gestion scolaire", 14, color="#8A99AF").pack()
        label(inner, "Élèves • Enseignants • Classes • Matières\nNotes • Bulletins • Emploi du temps", 12,
              color="#8A99AF", justify="center").pack(pady=24)

        right = ctk.CTkFrame(self, fg_color="white", corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")
        form = ctk.CTkFrame(right, fg_color="transparent", width=360)
        form.place(relx=0.5, rely=0.5, anchor="center")
        label(form, "Connexion", 28, True).pack(anchor="w")
        label(form, "Connectez-vous pour accéder à votre espace", 13, color=C["muted"]).pack(anchor="w", pady=(2, 24))
        label(form, "Nom d'utilisateur", 12, True).pack(anchor="w", pady=(0, 4))
        self.user = entry(form, "admin", width=360)
        self.user.pack()
        label(form, "Mot de passe", 12, True).pack(anchor="w", pady=(14, 4))
        self.pw = entry(form, "••••••••", width=360, show="•")
        self.pw.pack()
        self.show_var = ctk.BooleanVar()
        ctk.CTkCheckBox(form, text="Afficher le mot de passe", variable=self.show_var, font=(FONT, 12),
                        text_color=C["muted"], fg_color=C["primary"],
                        command=lambda: self.pw.configure(show="" if self.show_var.get() else "•")).pack(anchor="w", pady=12)
        self.err = label(form, "", 12, color=C["danger"])
        self.err.pack(anchor="w")
        button(form, "Se connecter", self.login, width=360).pack(pady=(8, 0))
        label(form, "Par défaut : admin / admin123", 11, color=C["muted"]).pack(pady=14)
        self.user.bind("<Return>", lambda e: self.login())
        self.pw.bind("<Return>", lambda e: self.login())

    def login(self):
        u, p = self.user.get().strip(), self.pw.get()
        if auth_service.authenticate(u, p):
            self.on_success(u)
        else:
            self.err.configure(text="Identifiants incorrects.")
