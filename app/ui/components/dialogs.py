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

class PdfPreviewDialog(ctk.CTkToplevel):
    """Aperçu d'un PDF dans l'application, avant son enregistrement (rendu : pypdfium2 ou PyMuPDF).

    on_save() est appelée par le bouton d'enregistrement ; elle doit renvoyer True si tout s'est bien passé
    (l'aperçu se ferme alors)."""
    ZOOMS = [0.7, 0.85, 1.0, 1.15, 1.3, 1.5, 1.75]
    A4_WIDTH = 595            # largeur d'une page A4 en points : zoom 1,0 = 595 px à l'écran

    def __init__(self, master, pdf_bytes, title, on_save, save_text="Enregistrer et ouvrir"):
        from app.utils.pdf_preview import PdfPages
        pages = PdfPages(pdf_bytes)  # lève ImportError (name='pypdfium2') si aucun moteur de rendu n'est installé
        super().__init__(master)
        self.doc = pages
        self.n, self.i, self.zi, self.on_save = len(pages), 0, 3, on_save
        self.photo = None
        self.title(f"Aperçu — {title}")
        self.geometry("900x880")
        self.minsize(700, 560)
        self.configure(fg_color="#E8EDF3")

        bar = ctk.CTkFrame(self, fg_color="white", corner_radius=0, height=60)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        self.prev_b = button(bar, "", lambda: self.step(-1), "light", ic="chev-l", width=44)
        self.prev_b.pack(side="left", padx=(16, 4), pady=10)
        self.page_lbl = label(bar, "", 12, True)
        self.page_lbl.pack(side="left", padx=8)
        self.next_b = button(bar, "", lambda: self.step(1), "light", ic="chev-r", width=44)
        self.next_b.pack(side="left", padx=(4, 18))
        button(bar, "−", lambda: self.zoom(-1), "light", width=40).pack(side="left", padx=2)
        button(bar, "+", lambda: self.zoom(1), "light", width=40).pack(side="left", padx=2)
        button(bar, save_text, self.save, ic="save").pack(side="right", padx=(8, 16), pady=10)
        button(bar, "Fermer", self.close, "light", ic="x").pack(side="right", pady=10)

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="#CBD5E1", corner_radius=0)
        self.scroll.pack(fill="both", expand=True)
        self.img_lbl = ctk.CTkLabel(self.scroll, text="")
        self.img_lbl.pack(pady=14)
        self.show()
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Left>", lambda e: self.step(-1))
        self.bind("<Right>", lambda e: self.step(1))
        self.transient(master.winfo_toplevel())
        self.after(150, self.grab_set)

    def show(self):
        z, sharp = self.ZOOMS[self.zi], 1.5          # rendu 1,5x plus fin que l'affichage pour rester net
        img = self.doc.render(self.i, round(self.A4_WIDTH * z * sharp))
        self.photo = ctk.CTkImage(light_image=img, size=(round(img.width / sharp), round(img.height / sharp)))
        self.img_lbl.configure(image=self.photo)
        self.page_lbl.configure(text=f"Page {self.i + 1} / {self.n}")
        self.prev_b.configure(state="normal" if self.i > 0 else "disabled")
        self.next_b.configure(state="normal" if self.i < self.n - 1 else "disabled")
        try:
            self.scroll._parent_canvas.yview_moveto(0)
        except Exception:
            pass

    def step(self, d):
        j = max(0, min(self.n - 1, self.i + d))
        if j != self.i:
            self.i = j
            self.show()

    def zoom(self, d):
        j = max(0, min(len(self.ZOOMS) - 1, self.zi + d))
        if j != self.zi:
            self.zi = j
            self.show()

    def save(self):
        if self.on_save():
            self.close()

    def close(self):
        try:
            self.doc.close()
        finally:
            self.destroy()