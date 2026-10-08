"""Aperçu du bulletin avant enregistrement : pages rendues à l'écran, navigation élève par élève, zoom."""
import os
from tkinter import filedialog, messagebox

import customtkinter as ctk

from app.config import BULLETINS_DIR
from app.constants import C
from app.reports.preview import PdfPreview
from app.services import bulletin_service
from app.ui.components.buttons import button
from app.ui.components.card import label
from app.utils.files import open_file, safe_name

ZOOMS = [0.8, 1.1, 1.35, 1.55]          # 1.0 = 595 x 842 px
PAGE_W, PAGE_H = 595.0, 842.0


class BulletinPreviewDialog(ctk.CTkToplevel):
    def __init__(self, master, ids, cid, per, name):
        super().__init__(master)
        self.title("Aperçu du bulletin")
        self.geometry("980x920")
        self.minsize(720, 600)
        self.configure(fg_color=C["bg"])
        self.ids, self.cid, self.per, self.name = ids, cid, per, name
        self.index, self.zoom_i, self.pdf, self.names, self.img = 0, 2, None, [], None
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        bar = ctk.CTkFrame(self, fg_color="white", corner_radius=0, height=64)
        bar.grid(row=0, column=0, sticky="ew")
        bar.pack_propagate(False)
        self.prev_b = button(bar, "Précédent", lambda: self.go(-1), "light", width=110)
        self.prev_b.pack(side="left", padx=(20, 6), pady=12)
        self.next_b = button(bar, "Suivant", lambda: self.go(1), "light", width=110)
        self.next_b.pack(side="left", padx=6, pady=12)
        self.pos_lbl = label(bar, "", 13, True)
        self.pos_lbl.pack(side="left", padx=14)
        self.name_lbl = label(bar, "", 12, color=C["muted"])
        self.name_lbl.pack(side="left")
        self.zin = button(bar, "+", lambda: self.zoom(1), "light", width=44)
        self.zin.pack(side="right", padx=(6, 20), pady=12)
        self.zout = button(bar, "−", lambda: self.zoom(-1), "light", width=44)
        self.zout.pack(side="right", padx=6, pady=12)
        label(bar, "Zoom", 12, color=C["muted"]).pack(side="right", padx=(0, 4))

        self.body = ctk.CTkScrollableFrame(self, fg_color="#CBD5E1", corner_radius=0)
        self.body.grid(row=1, column=0, sticky="nsew")
        self.page_lbl = ctk.CTkLabel(self.body, text="Préparation de l'aperçu…", text_color=C["text"])
        self.page_lbl.pack(pady=20)

        foot = ctk.CTkFrame(self, fg_color="white", corner_radius=0, height=70)
        foot.grid(row=2, column=0, sticky="ew")
        foot.pack_propagate(False)
        button(foot, "Fermer", self.destroy, "light", ic="x", width=120).pack(side="right", padx=(8, 20), pady=15)
        self.save_b = button(foot, "Enregistrer le PDF", self.save, ic="save", width=190)
        self.save_b.pack(side="right", pady=15)
        label(foot, "Aperçu : le numéro du bulletin est attribué à l'enregistrement, et le motif\n"
                    "anti-photocopie n'apparaît pas à l'écran.", 11, color=C["muted"], justify="left").pack(
            side="left", padx=20)

        self.bind("<Left>", lambda e: self.go(-1))
        self.bind("<Right>", lambda e: self.go(1))
        self.bind("<Escape>", lambda e: self.destroy())
        self.transient(master.winfo_toplevel())
        self.after(150, self.grab_set)
        self.after(60, self.build)

    def build(self):
        try:
            data, self.names = bulletin_service.build_preview(self.ids, self.cid, self.per)
            self.pdf = PdfPreview(data)
        except ImportError as ex:
            pkg = {"PIL": "pillow", "fitz": "pymupdf"}.get(ex.name, ex.name or "reportlab pillow pymupdf")
            messagebox.showerror("Aperçu", f"Un module est requis :  pip install {pkg}", parent=self)
            self.destroy()
            return
        except Exception as ex:
            messagebox.showerror("Aperçu", f"Impossible de préparer l'aperçu :\n{ex}", parent=self)
            self.destroy()
            return
        self.show()

    def go(self, step):
        if self.pdf and 0 <= self.index + step < self.pdf.count:
            self.index += step
            self.show()

    def zoom(self, step):
        if self.pdf and 0 <= self.zoom_i + step < len(ZOOMS):
            self.zoom_i += step
            self.show()

    def show(self):
        z = ZOOMS[self.zoom_i]
        img = self.pdf.render(self.index, z * 1.5)            # rendu 1,5x plus fin pour rester net à l'écran
        self.img = ctk.CTkImage(light_image=img, size=(int(PAGE_W * z), int(PAGE_H * z)))
        self.page_lbl.configure(image=self.img, text="")
        self.page_lbl.pack_configure(pady=16)
        n = self.pdf.count
        self.pos_lbl.configure(text=f"{self.index + 1} / {n}" if n > 1 else "Bulletin")
        self.name_lbl.configure(text=self.names[self.index] if self.index < len(self.names) else "")
        self.prev_b.configure(state="normal" if self.index > 0 else "disabled")
        self.next_b.configure(state="normal" if self.index < n - 1 else "disabled")
        self.zout.configure(state="normal" if self.zoom_i > 0 else "disabled")
        self.zin.configure(state="normal" if self.zoom_i < len(ZOOMS) - 1 else "disabled")

    def save(self):
        os.makedirs(BULLETINS_DIR, exist_ok=True)
        path = filedialog.asksaveasfilename(parent=self, title="Enregistrer le bulletin", defaultextension=".pdf",
                                            initialdir=BULLETINS_DIR, initialfile=safe_name(self.name) + ".pdf",
                                            filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        try:
            bulletin_service.save(self.ids, self.cid, self.per, path, self.name)
        except PermissionError:
            messagebox.showerror("Enregistrement", "Impossible d'écrire le fichier : fermez-le dans votre lecteur "
                                                   "PDF ou choisissez un autre nom.", parent=self)
            return
        except Exception as ex:
            messagebox.showerror("Enregistrement", f"Échec de l'enregistrement :\n{ex}", parent=self)
            return
        open_file(path)
        self.destroy()