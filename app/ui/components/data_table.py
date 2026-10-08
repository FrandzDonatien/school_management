"""DataTable (recherche, tri, pagination) et CrudPage (formulaire + liste générique).

Le design du DataTable s'inspire des « Data Tables » de TailAdmin : barre d'outils « Afficher N lignes » +
recherche, en-têtes avec icônes de tri, lignes aérées séparées par un filet léger, survol et sélection en
couleur, badges de statut, pied de page « Affichage de … » avec pagination numérotée (Précédent / 1 2 3 … / Suivant).
"""
import sqlite3
import sys
import tkinter as tk
from tkinter import ttk, messagebox

import customtkinter as ctk

from app.constants import C, FONT
from app.database.connection import execute, query
from app.ui.components.buttons import button
from app.ui.components.card import card, label
from app.ui.components.dialogs import blocked
from app.ui.components.icons import icon
from app.ui.components.inputs import combo, entry
from app.utils.formatting import num

# --- Palette TailAdmin -----------------------------------------------------------------------
G50, G100, G200, G300, G400 = "#F9FAFB", "#F2F4F7", "#E4E7EC", "#D0D5DD", "#98A2B3"
G500, G600, G700 = "#667085", "#475467", "#344054"
BADGES = {"success": ("#ECFDF3", "#039855"), "warning": ("#FFFAEB", "#DC6803"),
          "error": ("#FEF3F2", "#D92D20"), "brand": ("#ECF3FF", "#465FFF"), "gray": ("#F2F4F7", "#344054")}
ROW_H, HEAD_H, PAD = 50, 46, 18          # hauteur des lignes, de l'en-tête, marge gauche des cellules


def _rw(fw):
    """Largeur relative utile d'une cellule : on retire la marge gauche (CTk interdit width= dans place())."""
    return max(fw - 0.028, fw * 0.6)


def badge_style(text):
    """Couleurs (fond, texte) d'un badge de statut d'après son libellé. Surchargeable via DataTable(badge_fn=...)."""
    t = str(text).lower()
    if any(k in t for k in ("dépass", "depass", "excès", "erreur", "invalide", "retard", "refus", "inactif", "absent")):
        return BADGES["error"]
    if any(k in t for k in ("manque", "incomplet", "partiel", "attente", "insuffis", "faible")):
        return BADGES["warning"]
    if any(k in t for k in ("complet", "ok", "atteint", "actif", "active", "oui", "valid", "présent")):
        return BADGES["success"]
    return BADGES["gray"]


def setup_style():
    s = ttk.Style()
    s.theme_use("clam")
    s.configure("Treeview", background="white", fieldbackground="white", foreground=C["text"],
                rowheight=40, borderwidth=0, font=(FONT, 10))
    s.configure("Treeview.Heading", background="#F1F5F9", foreground=C["text"], font=(FONT, 10, "bold"),
                relief="flat", padding=10)
    s.map("Treeview", background=[("selected", C["primary_light"])], foreground=[("selected", C["primary"])])
    s.map("Treeview.Heading", background=[("active", "#E8EDF3")])
    s.configure("Vertical.TScrollbar", background="#E2E8F0", troughcolor="white", borderwidth=0, arrowsize=12)


class _TreeShim:
    """Compatibilité avec l'ancien ttk.Treeview : bind('<<TreeviewSelect>>'), selection(), selection_set(), ..."""

    def __init__(self, table):
        self._t, self._cbs = table, []

    def bind(self, sequence=None, func=None, add=None):
        if sequence == "<<TreeviewSelect>>" and func:
            self._cbs.append(func)

    def fire(self):
        for cb in list(self._cbs):
            cb(None)

    def selection(self):
        return (self._t.selected,) if self._t.selected is not None else ()

    def selection_set(self, *items):
        if len(items) == 1 and isinstance(items[0], (list, tuple)):
            items = items[0]
        self._t.select(str(items[0]) if items else None, notify=True)

    def selection_remove(self, *items):
        self._t.select(None, notify=False)

    def exists(self, iid):
        return self._t.has_id(iid)


class _Row:
    """Une ligne réutilisable du tableau (les widgets sont créés une fois puis remplis à chaque affichage)."""

    def __init__(self):
        self.frame, self.cells, self.sep = None, [], None
        self.iid, self.shown = None, False
        self.cache, self.paint = [], None


_WHEEL_BOUND = []


def _on_wheel(e):
    """Molette : fait défiler le tableau situé sous le pointeur."""
    try:
        w = e.widget.winfo_containing(e.x_root, e.y_root)
    except Exception:
        return
    while w is not None:
        owner = getattr(w, "_dt_owner", None)
        if owner is not None:
            owner.scroll(e)
            return
        w = getattr(w, "master", None)


class DataTable(ctk.CTkFrame):
    SIZES = ["5", "10", "25", "50", "100"]

    def __init__(self, master, columns, page_size=10, search=True, paginate=True, with_id=True, height=8,
                 badge_cols=(), badge_fn=None, empty_text="Aucun résultat"):
        """columns : [(titre, largeur relative)] ; si with_id, la 1re valeur de chaque ligne est l'identifiant.
        badge_cols : titres (ou indices) des colonnes à afficher sous forme de badges colorés."""
        super().__init__(master, fg_color="transparent")
        self.columns, self.with_id, self.paginate = columns, with_id, paginate
        self.page_size = page_size
        self.rows, self.view = [], []
        self.page, self.sort_i, self.sort_rev = 0, None, False
        self.selected = None
        self.badge_idx = {i for i, (t, _) in enumerate(columns) if t in badge_cols or i in badge_cols}
        self.badge_fn = badge_fn or badge_style
        self.empty_text = empty_text
        self.tree = _TreeShim(self)
        self._pool, self._hover, self._search_job = [], None, None
        total = sum(w for _, w in columns) or 1
        self.fracs, x = [], 0
        for _, w in columns:
            self.fracs.append((x / total, w / total))
            x += w
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self._build_toolbar(search)
        self._build_table(height)
        if paginate:
            self._build_footer()
        if not _WHEEL_BOUND:
            self.canvas.bind_all("<MouseWheel>", _on_wheel, add="+")
            self.canvas.bind_all("<Button-4>", _on_wheel, add="+")
            self.canvas.bind_all("<Button-5>", _on_wheel, add="+")
            _WHEEL_BOUND.append(True)

    # ------------------------------------------------------------------ construction
    def _scale(self):
        try:
            return float(self._get_widget_scaling())
        except Exception:
            return 1.0

    def _build_toolbar(self, search):
        self.search = None
        if not (search or self.paginate):
            return
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        if self.paginate:
            label(bar, "Afficher", 12, color=G500).pack(side="left")
            self.size_cb = combo(bar, self.SIZES, command=self.set_size, width=80)
            self.size_cb.set(str(self.page_size))
            self.size_cb.pack(side="left", padx=8)
            label(bar, "lignes", 12, color=G500).pack(side="left")
        if search:
            box = ctk.CTkFrame(bar, fg_color="white", border_width=1, border_color=G300, corner_radius=8)
            box.pack(side="right")
            ctk.CTkLabel(box, text="", image=icon("search", G500, 16)).pack(side="left", padx=(12, 0), pady=2)
            self.search = ctk.CTkEntry(box, placeholder_text="Rechercher…", width=240, height=36, border_width=0,
                                       fg_color="transparent", text_color=C["text"], font=(FONT, 12))
            self.search.pack(side="left", padx=(4, 8), pady=1)
            self.search.bind("<KeyRelease>", lambda e: self.on_search())

    def _build_table(self, height):
        s = self._s = self._scale()
        wrap = ctk.CTkFrame(self, fg_color="transparent")
        wrap.grid(row=1, column=0, sticky="nsew")
        wrap.columnconfigure(0, weight=1)
        wrap.rowconfigure(2, weight=1)
        # en-tête (titres cliquables pour trier)
        self.head = ctk.CTkFrame(wrap, fg_color="transparent", corner_radius=0, height=HEAD_H)
        self.head.grid(row=0, column=0, sticky="ew")
        self.head_cells = []
        for k, (title, _) in enumerate(self.columns):
            fx, fw = self.fracs[k]
            cell = ctk.CTkFrame(self.head, fg_color="transparent", corner_radius=0)
            cell.place(relx=fx, x=PAD, rely=0, relheight=1, relwidth=_rw(fw))
            lab = ctk.CTkLabel(cell, text=title, font=(FONT, 12, "bold"), text_color=G600)
            lab.pack(side="left")
            arrows = tk.Canvas(cell, width=int(10 * s), height=int(14 * s), highlightthickness=0, bd=0,
                               bg=C["card"], cursor="hand2")
            arrows.pack(side="left", padx=(6, 0))
            for w in (cell, lab, arrows):
                w.bind("<Button-1>", lambda e, k=k: self.sort_by(k))
            self.head_cells.append((lab, arrows))
            self._draw_arrows(arrows, None)
        tk.Frame(wrap, height=1, bg=G200, bd=0, highlightthickness=0).grid(row=1, column=0, sticky="ew")
        # corps défilant
        self.canvas = tk.Canvas(wrap, highlightthickness=0, bd=0, bg=C["card"], height=int(height * ROW_H * s),
                                yscrollincrement=max(1, int(16 * s)))
        self.canvas.grid(row=2, column=0, sticky="nsew")
        self.vsb = ctk.CTkScrollbar(wrap, orientation="vertical", command=self.canvas.yview, width=10, fg_color="transparent",
                                    button_color=G300, button_hover_color=G400)
        self.vsb.grid(row=2, column=1, sticky="ns", padx=(4, 0))
        self.vsb.grid_remove()
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.inner = ctk.CTkFrame(self.canvas, fg_color="transparent", corner_radius=0)
        self._win = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas._dt_owner = self.inner._dt_owner = self
        self.empty = label(self.inner, self.empty_text, 13, color=G500)

    def _build_footer(self):
        foot = ctk.CTkFrame(self, fg_color="transparent")
        foot.grid(row=2, column=0, sticky="ew", pady=(14, 0))
        self.info = label(foot, "", 12, color=G500)
        self.info.pack(side="left")
        self.pager = ctk.CTkFrame(foot, fg_color="transparent")
        self.pager.pack(side="right")

    def _draw_arrows(self, cv, state):
        s = self._s
        cv.delete("all")
        up = C["primary"] if state == "asc" else G300
        dn = C["primary"] if state == "desc" else G300
        w = int(10 * s)
        cv.create_polygon(w / 2, 1 * s, 1 * s, 6 * s, w - 1 * s, 6 * s, fill=up, outline=up)
        cv.create_polygon(1 * s, 8 * s, w - 1 * s, 8 * s, w / 2, 13 * s, fill=dn, outline=dn)

    def _new_row(self):
        row = _Row()
        row.frame = ctk.CTkFrame(self.inner, height=ROW_H, fg_color="transparent", corner_radius=0)
        for k in range(len(self.columns)):
            fx, fw = self.fracs[k]
            if k in self.badge_idx:
                w = ctk.CTkLabel(row.frame, text="", height=24, corner_radius=12, font=(FONT, 11, "bold"))
            else:
                w = ctk.CTkLabel(row.frame, text="", anchor="w", font=(FONT, 12, "bold" if k == 0 else "normal"))
                w.place(relx=fx, x=PAD, rely=0, relheight=1, relwidth=_rw(fw))
            row.cells.append(w)
        row.cache = [None] * len(self.columns)
        row.sep = tk.Frame(row.frame, bg=G200, bd=0, highlightthickness=0)       # filet 1 px (tk : fiable à 1 px)
        row.sep.place(relx=0, rely=1.0, anchor="sw", relwidth=1.0, height=1)
        for w in [row.frame, row.sep] + row.cells:
            w.bind("<Enter>", self._hover_later)
            w.bind("<Leave>", self._hover_later)
            w.bind("<Button-1>", lambda e, r=row: self._click(r))
        return row

    # ------------------------------------------------------------------ interactions
    def _hover_later(self, _=None):
        self.after_idle(self._hover_check)

    def _hover_check(self):
        try:
            w = self.winfo_containing(*self.winfo_pointerxy())
        except Exception:
            w = None
        found = None
        rows = {r.frame: r for r in self._pool}
        while w is not None:
            if w in rows:
                found = rows[w]
                break
            w = getattr(w, "master", None)
        old, self._hover = self._hover, found
        for r in (old, found):
            if r is not None:
                self._paint(r)

    def _click(self, row):
        if self.with_id and row.iid is not None:
            self.select(row.iid, notify=True)

    def _paint(self, row):
        sel = self.with_id and row.iid is not None and row.iid == self.selected
        bg = C["primary_light"] if sel else (G50 if row is self._hover else "transparent")
        fg0, fg = (C["primary"], C["primary"]) if sel else (C["text"], G600)
        state = (bg, fg0, fg)
        if row.paint == state:
            return
        row.paint = state
        row.frame.configure(fg_color=bg)
        for k, w in enumerate(row.cells):
            if k not in self.badge_idx:
                w.configure(text_color=fg0 if k == 0 else fg)

    def scroll(self, e):
        try:
            if not self.winfo_exists() or self.canvas.yview() == (0.0, 1.0):
                return
            if getattr(e, "num", 0) == 4:
                step = -3
            elif getattr(e, "num", 0) == 5:
                step = 3
            elif sys.platform == "darwin":
                step = -e.delta
            else:
                step = -int(e.delta / 120) * 3
            self.canvas.yview_scroll(step, "units")
        except tk.TclError:
            pass

    def _on_canvas_resize(self, e):
        self.canvas.itemconfigure(self._win, width=e.width)
        self.after_idle(self._toggle_scrollbar)

    def _toggle_scrollbar(self):
        try:
            need = self.inner.winfo_reqheight() > self.canvas.winfo_height() + 1 and self.canvas.winfo_height() > 1
            if need and not self.vsb.winfo_ismapped():
                self.vsb.grid()
            elif not need and self.vsb.winfo_ismapped():
                self.vsb.grid_remove()
        except tk.TclError:
            pass

    # ------------------------------------------------------------------ données
    @staticmethod
    def sort_key(v):
        if v is None or v == "":
            return (2, 0, "")
        try:
            return (0, float(str(v).replace(",", ".")), "")
        except ValueError:
            return (1, 0, str(v).lower())

    def has_id(self, iid):
        return self.with_id and any(str(r[0]) == str(iid) for r in self.rows)

    def select(self, iid, notify=False):
        self.selected = None if iid is None else str(iid)
        for r in self._pool:
            if r.shown:
                self._paint(r)
        if notify:
            self.tree.fire()

    def set_size(self, value):
        self.page_size, self.page = int(value), 0
        self.apply()

    def on_search(self):
        if self._search_job:
            self.after_cancel(self._search_job)
        self._search_job = self.after(120, self._do_search)

    def _do_search(self):
        self._search_job = None
        self.page = 0
        self.apply()

    def sort_by(self, k):
        self.sort_rev = (not self.sort_rev) if self.sort_i == k else False
        self.sort_i, self.page = k, 0
        self.apply()

    def go(self, step):
        self.page += step
        self.apply()

    def goto(self, page):
        self.page = page
        self.apply()

    def set_rows(self, rows):
        self.rows = [tuple(r) for r in rows]
        self.page = 0
        if self.selected is not None and not self.has_id(self.selected):
            self.selected = None
        self.apply()

    def apply(self):
        off = 1 if self.with_id else 0
        t = self.search.get().strip().lower() if self.search else ""
        rows = [r for r in self.rows
                if not t or t in " ".join("" if v is None else str(v) for v in r[off:]).lower()]
        if self.sort_i is not None:
            rows.sort(key=lambda r: self.sort_key(r[self.sort_i + off]), reverse=self.sort_rev)
        self.view = rows
        n = len(rows)
        if self.paginate:
            pages = max(1, -(-n // self.page_size))
            self.page = max(0, min(self.page, pages - 1))
            a = self.page * self.page_size
            shown = rows[a:a + self.page_size]
        else:
            pages, a, shown = 1, 0, rows
        self._render_rows(shown, off)
        for k, (_, cv) in enumerate(self.head_cells):
            self._draw_arrows(cv, (("desc" if self.sort_rev else "asc") if self.sort_i == k else None))
        if self.paginate:
            filt = f" (filtré sur {len(self.rows)})" if n != len(self.rows) else ""
            self.info.configure(text=f"Affichage de {a + 1 if n else 0} à {a + len(shown)} sur {n} entrée(s){filt}")
            self._render_pager(pages)
        self.canvas.yview_moveto(0)
        self.after_idle(self._toggle_scrollbar)

    def _render_rows(self, shown, off):
        while len(self._pool) < len(shown):
            self._pool.append(self._new_row())
        if shown:
            self.empty.pack_forget()
        else:
            self.empty.pack(pady=40)
        for i, r in enumerate(self._pool):
            if i >= len(shown):
                if r.shown:
                    r.frame.pack_forget()
                    r.shown, r.iid = False, None
                continue
            vals = shown[i]
            r.iid = str(vals[0]) if self.with_id else None
            if not r.shown:
                r.frame.pack(fill="x")
                r.shown = True
            for k, w in enumerate(r.cells):
                v = vals[k + off] if k + off < len(vals) else ""
                text = "" if v is None else str(v)
                if k in self.badge_idx:
                    key = (text, True)
                    if r.cache[k] != key:
                        r.cache[k] = key
                        if text:
                            bg, fg = self.badge_fn(text)
                            w.configure(text=text, fg_color=bg, text_color=fg)
                            w.place(relx=self.fracs[k][0], x=PAD, rely=0.5, anchor="w")
                        else:
                            w.place_forget()
                elif r.cache[k] != text:
                    r.cache[k] = text
                    w.configure(text=text)
            r.paint = None
            self._paint(r)

    def _render_pager(self, pages):
        for w in self.pager.winfo_children():
            w.destroy()
        cur = self.page
        nav = dict(height=36, corner_radius=8, fg_color="white", hover_color=G50, border_width=1,
                   border_color=G300, text_color=G700, text_color_disabled=G400, font=(FONT, 12, "bold"))
        ctk.CTkButton(self.pager, text="Précédent", image=icon("chev-l", G700, 14), compound="left", width=0,
                      state="normal" if cur > 0 else "disabled", command=lambda: self.go(-1), **nav
                      ).pack(side="left", padx=(0, 6))
        for p in self._page_items(cur, pages):
            if p is None:
                label(self.pager, "…", 13, color=G500).pack(side="left", padx=6)
                continue
            on = p == cur
            ctk.CTkButton(self.pager, text=str(p + 1), width=36, height=36, corner_radius=8,
                          fg_color=C["primary"] if on else "transparent", hover_color=C["primary_dark"] if on else C["primary_light"],
                          text_color="white" if on else G700, font=(FONT, 12, "bold"),
                          command=lambda p=p: self.goto(p)).pack(side="left", padx=2)
        ctk.CTkButton(self.pager, text="Suivant", image=icon("chev-r", G700, 14), compound="right", width=0,
                      state="normal" if cur < pages - 1 else "disabled", command=lambda: self.go(1), **nav
                      ).pack(side="left", padx=(6, 0))

    @staticmethod
    def _page_items(cur, pages):
        """Numéros de pages (indices) avec None pour « … » : 1 … 4 5 6 … 20."""
        if pages <= 7:
            return list(range(pages))
        keep = sorted({0, pages - 1, *range(max(0, cur - 1), min(pages, cur + 2))})
        out, prev = [], None
        for p in keep:
            if prev is not None and p - prev > 1:
                out.append(None)
            out.append(p)
            prev = p
        return out


class CrudPage(ctk.CTkFrame):
    """Page générique : formulaire à gauche, liste (DataTable) à droite."""

    def __init__(self, master, title, table, fields, list_sql, columns, after_insert=None,
                 list_params=None, insert_extra=None, actions=(), badge_cols=()):
        super().__init__(master, fg_color=C["bg"])
        self.table, self.fields, self.list_sql = table, fields, list_sql
        self.after_insert, self.list_params, self.insert_extra = after_insert, list_params, insert_extra
        self.selected_id = None
        self.widgets, self.fk_maps = {}, {}
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        form = card(self, width=330)
        form.grid(row=0, column=0, sticky="ns", padx=(0, 16))
        form.grid_propagate(False)
        self.form_title = label(form, "Nouvel enregistrement", 16, True)
        self.form_title.pack(anchor="w", padx=22, pady=(20, 6))
        body = ctk.CTkScrollableFrame(form, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=8)
        self.body = body
        for f in fields:
            req = " *" if f.get("required") else ""
            label(body, f["label"] + req, 12, color=C["muted"]).pack(anchor="w", padx=14, pady=(8, 2))
            if f["type"] == "combo":
                w = combo(body, f["values"])
                w.set(f["values"][0])
            elif f["type"] == "fk":
                w = combo(body, [""])
            else:
                w = entry(body, f.get("placeholder", ""))
            w.pack(fill="x", padx=14)
            self.widgets[f["key"]] = w
        btns = ctk.CTkFrame(form, fg_color="transparent")
        btns.pack(fill="x", padx=22, pady=16)
        button(btns, "Enregistrer", self.save, ic="save").pack(fill="x")
        row = ctk.CTkFrame(btns, fg_color="transparent")
        row.pack(fill="x", pady=(8, 0))
        row.columnconfigure((0, 1), weight=1)
        button(row, "Nouveau", self.clear, "light", ic="plus").grid(row=0, column=0, sticky="ew", padx=(0, 4))
        button(row, "Supprimer", self.delete, "danger", ic="trash").grid(row=0, column=1, sticky="ew", padx=(4, 0))

        right = card(self)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)
        head = ctk.CTkFrame(right, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=22, pady=(20, 10))
        self.head = head
        label(head, title, 16, True).pack(side="left")
        for text, fn, kind, ic in reversed(list(actions)):
            button(head, text, lambda fn=fn: fn(self), kind, ic=ic).pack(side="right", padx=(8, 0))
        self.dt = DataTable(right, columns, badge_cols=badge_cols)
        self.dt.grid(row=1, column=0, sticky="nsew", padx=22, pady=(0, 20))
        self.dt.tree.bind("<<TreeviewSelect>>", self.on_select)

    def refresh(self):
        for f in self.fields:
            if f["type"] == "fk":
                self.fk_maps[f["key"]] = f["options"]()
                self.widgets[f["key"]].configure(values=[""] + list(self.fk_maps[f["key"]]))
        params = self.list_params() if self.list_params else ()
        self.dt.set_rows(query(self.list_sql, params))
        self.clear()

    def clear(self):
        self.selected_id = None
        self.form_title.configure(text="Nouvel enregistrement")
        self.dt.tree.selection_remove(self.dt.tree.selection())
        for f in self.fields:
            w = self.widgets[f["key"]]
            if f["type"] == "combo":
                w.set(f["values"][0])
            elif f["type"] == "fk":
                w.set("")
            else:
                w.delete(0, "end")

    def on_select(self, _=None):
        sel = self.dt.tree.selection()
        if not sel:
            return
        self.selected_id = int(sel[0])
        rec = query(f"SELECT * FROM {self.table} WHERE id=?", (self.selected_id,))[0]
        self.form_title.configure(text="Modifier l'enregistrement")
        for f in self.fields:
            w, v = self.widgets[f["key"]], rec[f["key"]]
            if f["type"] == "fk":
                rev = {i: n for n, i in self.fk_maps[f["key"]].items()}
                w.set(rev.get(v, ""))
            elif f["type"] == "combo":
                w.set(v if v in f["values"] else f["values"][0])
            else:
                w.delete(0, "end")
                w.insert(0, "" if v is None else (num(v) if isinstance(v, float) else v))

    def get_values(self):
        vals = {}
        for f in self.fields:
            raw = self.widgets[f["key"]].get().strip()
            if f.get("required") and not raw:
                messagebox.showwarning("Champ requis", f"Le champ « {f['label']} » est obligatoire.")
                return None
            if f["type"] == "fk":
                vals[f["key"]] = self.fk_maps[f["key"]].get(raw)
            elif f["type"] == "number":
                if not raw and f.get("optional"):
                    vals[f["key"]] = None
                else:
                    try:
                        vals[f["key"]] = float(raw.replace(",", "."))
                    except ValueError:
                        messagebox.showwarning("Valeur invalide", f"« {f['label']} » doit être un nombre.")
                        return None
            else:
                vals[f["key"]] = raw
        return vals

    def save(self):
        if blocked():
            return
        vals = self.get_values()
        if vals is None:
            return
        try:
            if self.selected_id:
                sets = ", ".join(f"{k}=?" for k in vals)
                execute(f"UPDATE {self.table} SET {sets} WHERE id=?", [*vals.values(), self.selected_id])
                rid = self.selected_id
            else:
                if self.insert_extra:
                    vals.update(self.insert_extra())
                rid = execute(f"INSERT INTO {self.table}({', '.join(vals)}) VALUES({', '.join('?' * len(vals))})",
                              list(vals.values()))
                if self.after_insert:
                    self.after_insert(rid)
            self.after_save(rid)
        except sqlite3.IntegrityError:
            messagebox.showerror("Erreur", "Cet enregistrement existe déjà pour cette année scolaire.")
            return
        self.refresh()

    def after_save(self, rid):
        pass

    def delete(self):
        if blocked():
            return
        if not self.selected_id:
            messagebox.showinfo("Suppression", "Sélectionnez d'abord un enregistrement dans la liste.")
            return
        if messagebox.askyesno("Confirmation", "Supprimer définitivement cet enregistrement ?"):
            execute(f"DELETE FROM {self.table} WHERE id=?", (self.selected_id,))
            self.refresh()