"""Enseignants : une ou plusieurs matières, objectif horaire hebdomadaire, signature (bulletin)."""
import customtkinter as ctk
from tkinter import filedialog, messagebox

from app.constants import C, FONT
from app.database.queries import cur_year, year_extra
from app.repositories import subject_repository, teacher_repository
from app.services.settings_service import default_hours
from app.ui.components.buttons import button
from app.ui.components.card import label
from app.ui.components.data_table import CrudPage
from app.utils import signature


class TeachersPage(CrudPage):
    def __init__(self, master):
        fields = [
            dict(key="nom", label="Nom", type="entry", required=True),
            dict(key="prenom", label="Prénoms", type="entry"),
            dict(key="heures_sem", label="Heures / semaine (vide = valeur des paramètres)", type="number",
                 optional=True, placeholder="Ex : 21"),
            dict(key="email", label="Email", type="entry"),
            dict(key="telephone", label="Téléphone", type="entry"),
        ]
        cols = [("Nom", 120), ("Prénoms", 110), ("Matières", 150), ("H. attribuées", 95),
                ("Objectif h/sem.", 105), ("Email", 150), ("Téléphone", 100)]
        self.sub_vars = {}
        super().__init__(master, "Liste des enseignants", "teachers", fields, teacher_repository.LIST_SQL, cols,
                         list_params=lambda: (default_hours(), cur_year()), insert_extra=year_extra)
        label(self.body, "Matières enseignées (une ou plusieurs)", 12, color=C["muted"]).pack(
            anchor="w", padx=14, pady=(14, 4))
        self.sub_frame = ctk.CTkFrame(self.body, fg_color=C["soft"], border_width=1, border_color=C["border"],
                                      corner_radius=8)
        self.sub_frame.pack(fill="x", padx=14, pady=(0, 10))

        # signature imprimée sur le bulletin (colonne « Appréciations générales »)
        label(self.body, "Signature (imprimée sur le bulletin)", 12, color=C["muted"]).pack(
            anchor="w", padx=14, pady=(8, 4))
        self.sig_frame = ctk.CTkFrame(self.body, fg_color=C["soft"], border_width=1, border_color=C["border"],
                                      corner_radius=8)
        self.sig_frame.pack(fill="x", padx=14, pady=(0, 14))
        self.sig_img = ctk.CTkLabel(self.sig_frame, text="Aucune signature", text_color=C["muted"],
                                    font=(FONT, 11), height=70)
        self.sig_img.pack(fill="x", padx=10, pady=(10, 4))
        row = ctk.CTkFrame(self.sig_frame, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=(0, 10))
        button(row, "Choisir…", self.choose_signature, "light", ic="upload", width=110).pack(side="left")
        button(row, "Retirer", self.remove_signature, "light", ic="x", width=90).pack(side="left", padx=(8, 0))

    # -- matières
    def build_subject_boxes(self):
        for w in self.sub_frame.winfo_children():
            w.destroy()
        self.sub_vars = {}
        subs = subject_repository.by_year(cur_year())
        if not subs:
            label(self.sub_frame, "Créez d'abord des matières.", 11, color=C["muted"]).pack(padx=10, pady=8)
        for s in subs:
            v = ctk.BooleanVar(value=False)
            ctk.CTkCheckBox(self.sub_frame, text=s["nom"] + (f"  ({s['code']})" if s["code"] else ""),
                            variable=v, fg_color=C["primary"], text_color=C["text"],
                            font=(FONT, 12)).pack(anchor="w", padx=10, pady=4)
            self.sub_vars[s["id"]] = v

    # -- signature
    def teacher_names(self):
        """(nom, prénoms) de l'enseignant sélectionné dans la liste, ou None."""
        t = teacher_repository.get(self.selected_id) if self.selected_id else None
        return (t.nom, t.prenom) if t else None

    def show_signature(self):
        names = self.teacher_names()
        path = signature.find(*names) if names else None
        img = None
        if path:
            try:
                from PIL import Image
                with Image.open(path) as im:
                    im = im.convert("RGBA")
                k = min(210 / im.width, 62 / im.height, 1.0)
                size = (max(1, round(im.width * k)), max(1, round(im.height * k)))
                img = ctk.CTkImage(light_image=im, size=size)
            except Exception:
                img = None
        if img:
            self.sig_img.configure(image=img, text="")
        else:
            self.sig_img.configure(image=None, text="Aucune signature" if names else
                                   "Sélectionnez un enseignant")
        self._sig_photo = img  # garde une référence (sinon l'image disparaît)

    def choose_signature(self):
        names = self.teacher_names()
        if not names:
            messagebox.showinfo("Signature", "Sélectionnez d'abord un enseignant dans la liste "
                                             "(enregistrez-le s'il vient d'être créé).")
            return
        path = filedialog.askopenfilename(title="Choisir la signature de l'enseignant",
                                          filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tif *.tiff")])
        if not path:
            return
        try:
            signature.import_image(path, *names)   # détourage automatique : fond transparent, marges rognées
        except Exception as ex:
            messagebox.showerror("Signature", f"Image inutilisable :\n{ex}")
            return
        self.show_signature()

    def remove_signature(self):
        names = self.teacher_names()
        if not names or not signature.find(*names):
            messagebox.showinfo("Signature", "Cet enseignant n'a pas de signature.")
            return
        if messagebox.askyesno("Signature", "Retirer la signature de cet enseignant ?"):
            signature.remove(*names)
            self.show_signature()

    # -- cycle de vie de la page
    def refresh(self):
        self.build_subject_boxes()
        super().refresh()

    def clear(self):
        super().clear()
        for v in self.sub_vars.values():
            v.set(False)
        self.show_signature()

    def on_select(self, _=None):
        super().on_select(_)
        if self.selected_id:
            ids = teacher_repository.subject_ids(self.selected_id)
            for sid, v in self.sub_vars.items():
                v.set(sid in ids)
        self.show_signature()

    def after_save(self, tid):
        teacher_repository.set_subjects(tid, [s for s, v in self.sub_vars.items() if v.get()])