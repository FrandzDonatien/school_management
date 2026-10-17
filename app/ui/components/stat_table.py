import tkinter as tk
from tkinter import ttk

import customtkinter as ctk

from app.constants import C, FONT

_styled = False
SB = dict(width=12, fg_color=C["bg"], button_color=C["muted"], button_hover_color=C["primary"])


def _style():
    global _styled
    if _styled:
        return
    st = ttk.Style()
    st.theme_use("clam")
    st.configure("Stat.Treeview", background=C["card"], fieldbackground=C["card"], foreground=C["text"],
                 rowheight=38, borderwidth=0, font=(FONT, 10))
    st.configure("Stat.Treeview.Heading", background=C["bg"], foreground=C["muted"],
                 font=(FONT, 9, "bold"), relief="flat", borderwidth=0, padding=(8, 10))
    st.map("Stat.Treeview", background=[("selected", C["primary_light"])],
           foreground=[("selected", C["text"])])
    st.map("Stat.Treeview.Heading", background=[("active", C["border"])])
    _styled = True


class StatTable(ctk.CTkFrame):
    """status_col : index d'une colonne « Admis / Échec » colorée en vert / rouge."""

    def __init__(self, master, columns, height=10, search=False, status_col=None):
        super().__init__(master, fg_color="transparent")
        _style()
        self._rows, self._status = [], status_col
        self._q = tk.StringVar()
        if search:
            self._q.trace_add("write", lambda *_: self._render())
            ctk.CTkEntry(self, textvariable=self._q, placeholder_text="🔍  Rechercher…", width=260,
                         height=34, fg_color=C["card"], border_color=C["border"]).pack(anchor="e", pady=(0, 10))

        wrap = ctk.CTkFrame(self, fg_color=C["card"], border_width=1, border_color=C["border"], corner_radius=8)
        wrap.pack(fill="both", expand=True)
        wrap.grid_rowconfigure(0, weight=1)
        wrap.grid_columnconfigure(0, weight=1)

        ids = [str(i) for i in range(len(columns))]
        self.tree = ttk.Treeview(wrap, columns=ids, show="headings", height=height, style="Stat.Treeview")
        for i, (title, w) in enumerate(columns):
            self.tree.heading(ids[i], text=title.upper())
            self.tree.column(ids[i], width=w, minwidth=w, anchor="w" if i == 0 else "center", stretch=True)
        self.tree.tag_configure("odd", background="#F8FAFC")
        self.tree.tag_configure("ok", foreground=C["success"])
        self.tree.tag_configure("ko", foreground=C["danger"])

        vs = ctk.CTkScrollbar(wrap, orientation="vertical", command=self.tree.yview, **SB)
        hs = ctk.CTkScrollbar(wrap, orientation="horizontal", command=self.tree.xview, **SB)
        self.tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(1, 0), pady=(1, 0))
        vs.grid(row=0, column=1, sticky="ns", padx=3, pady=3)
        hs.grid(row=1, column=0, sticky="ew", padx=3, pady=3)

        self.empty = ctk.CTkLabel(wrap, text="Aucune donnée", text_color=C["muted"], fg_color=C["card"])

    @staticmethod
    def _fmt(v):
        return f"{v:.2f}" if isinstance(v, float) else str(v)

    def set_rows(self, rows):
        self._rows = [tuple(r) for r in rows]
        self._render()

    def _render(self):
        q = self._q.get().strip().lower()
        self.tree.delete(*self.tree.get_children())
        n = 0
        for r in self._rows:
            if q and not any(q in str(v).lower() for v in r):
                continue
            tags = ["odd"] if n % 2 else []
            if self._status is not None:
                tags.append("ok" if r[self._status] == "Admis" else "ko")
            self.tree.insert("", "end", values=[self._fmt(v) for v in r], tags=tags)
            n += 1
        if n:
            self.empty.place_forget()
        else:
            self.empty.place(relx=0.5, rely=0.5, anchor="center")