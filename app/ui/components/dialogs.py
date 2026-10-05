import customtkinter as ctk
from tkinter import messagebox

from app.constants import C, FONT
from app.database.queries import is_read_only
from app.ui.components.buttons import button
from app.ui.components.card import label
from app.ui.components.inputs import combo


def blocked(show=True):
    """True si l'année affichée n'est pas l'année active (lecture seule)."""
    if is_read_only():
        if show:
            messagebox.showinfo("Année en consultation",
                                "Vous consultez une année antérieure : les données sont en lecture seule.\n"
                                "Pour la modifier, définissez-la comme année active (page « Années scolaires »).")
        return True
    return False


class ProgressDialog(ctk.CTkToplevel):
    """Fenêtre d'attente indéterminée avec bouton Annuler."""

    def __init__(self, master, title, heading, detail, on_cancel):
        super().__init__(master)
        self.title(title)
        self.geometry("430x200")
        self.resizable(False, False)
        self.configure(fg_color="white")
        self.transient(master.winfo_toplevel())
        label(self, heading, 16, True).pack(padx=26, pady=(24, 6), anchor="w")
        self.info = label(self, detail, 12, color=C["muted"])
        self.info.pack(padx=26, anchor="w")
        self.bar = ctk.CTkProgressBar(self, mode="indeterminate", progress_color=C["primary"])
        self.bar.pack(fill="x", padx=26, pady=16)
        self.bar.start()
        button(self, "Annuler", on_cancel, "light", ic="x", width=120).pack(pady=(0, 14))
        self.after(150, self.grab_set)

    def set_info(self, text):
        self.info.configure(text=text)

    def close(self):
        self.bar.stop()
        self.destroy()


class ExportDialog(ctk.CTkToplevel):
    def __init__(self, master, classes, teachers, scope, cls_name, teacher_name_, on_export):
        super().__init__(master)
        self.title("Exporter les emplois du temps")
        self.geometry("500x540")
        self.resizable(False, False)
        self.configure(fg_color="white")
        self.classes, self.teachers, self.on_export = classes, teachers, on_export
        label(self, "Exporter les emplois du temps", 18, True).pack(anchor="w", padx=28, pady=(24, 2))
        label(self, "Choisissez le contenu à exporter, puis le format.", 12, color=C["muted"]).pack(anchor="w", padx=28)
        self.scope = ctk.StringVar(value=scope)

        def radio(parent, text, value, var):
            ctk.CTkRadioButton(parent, text=text, variable=var, value=value, fg_color=C["primary"],
                               font=(FONT, 12), text_color=C["text"]).pack(anchor="w", padx=28, pady=(10, 2))

        radio(self, "Emploi du temps général (toutes les classes)", "general", self.scope)
        radio(self, "Une classe :", "classe", self.scope)
        self.cls_cb = combo(self, list(classes) or [""])
        self.cls_cb.pack(fill="x", padx=(56, 28))
        self.cls_cb.set(cls_name if cls_name in classes else next(iter(classes), ""))
        radio(self, "Un enseignant :", "enseignant", self.scope)
        self.t_cb = combo(self, list(teachers) or [""])
        self.t_cb.pack(fill="x", padx=(56, 28))
        self.t_cb.set(teacher_name_ if teacher_name_ in teachers else next(iter(teachers), ""))
        radio(self, "Tous les enseignants (une feuille chacun)", "enseignants", self.scope)
        radio(self, "Toutes les classes (une feuille chacune)", "classes", self.scope)
        label(self, "Format", 12, True).pack(anchor="w", padx=28, pady=(18, 0))
        self.fmt = ctk.StringVar(value="xlsx")
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(anchor="w", padx=28, pady=(4, 0))
        for text, v in (("Excel (.xlsx)", "xlsx"), ("PDF / page imprimable", "html")):
            ctk.CTkRadioButton(row, text=text, variable=self.fmt, value=v, fg_color=C["primary"], font=(FONT, 12),
                               text_color=C["text"]).pack(side="left", padx=(0, 20))
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=28, pady=22, side="bottom")
        button(btns, "Annuler", self.destroy, "light", ic="x", width=120).pack(side="right", padx=(8, 0))
        button(btns, "Exporter", self.go, ic="download", width=140).pack(side="right")
        self.transient(master.winfo_toplevel())
        self.after(150, self.grab_set)

    def go(self):
        scope = self.scope.get()
        cid = self.classes.get(self.cls_cb.get())
        tid = self.teachers.get(self.t_cb.get())
        if (scope == "classe" and not cid) or (scope == "enseignant" and not tid):
            messagebox.showwarning("Export", "Sélectionnez un élément à exporter.", parent=self)
            return
        fmt_ = self.fmt.get()
        self.destroy()
        self.on_export(scope, cid, tid, fmt_)
