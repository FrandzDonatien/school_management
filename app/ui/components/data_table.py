"""DataTable (recherche, tri, pagination) et CrudPage (formulaire + liste générique)."""
import sqlite3
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


class DataTable(ctk.CTkFrame):
    SIZES = ["5", "10", "25", "50", "100"]

    def __init__(self, master, columns, page_size=10, search=True, paginate=True, with_id=True, height=8):
        super().__init__(master, fg_color="transparent")
        self.columns, self.with_id, self.paginate = columns, with_id, paginate
        self.page_size = page_size
        self.rows, self.view = [], []
        self.page, self.sort_i, self.sort_rev = 0, None, False
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.search = None
        if search or paginate:
            bar = ctk.CTkFrame(self, fg_color="transparent")
            bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
            if paginate:
                label(bar, "Afficher", 12, color=C["muted"]).pack(side="left")
                self.size_cb = combo(bar, self.SIZES, command=self.set_size, width=80)
                self.size_cb.set(str(page_size))
                self.size_cb.pack(side="left", padx=6)
                label(bar, "lignes", 12, color=C["muted"]).pack(side="left")
            if search:
                sb = ctk.CTkFrame(bar, fg_color="transparent")
                sb.pack(side="right")
                ctk.CTkLabel(sb, text="", image=icon("search", C["muted"], 16)).pack(side="left", padx=(0, 8))
                self.search = entry(sb, "Rechercher…", width=230)
                self.search.pack(side="left")
                self.search.bind("<KeyRelease>", lambda e: self.on_search())

        ids = [f"c{i}" for i in range(len(columns))]
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=1, column=0, sticky="nsew")
        self.tree = ttk.Treeview(frame, columns=ids, show="headings", height=height, selectmode="browse")
        for k, (i, (title, w)) in enumerate(zip(ids, columns)):
            self.tree.heading(i, text=title, anchor="w", command=lambda k=k: self.sort_by(k))
            self.tree.column(i, width=w, anchor="w", minwidth=40)
        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self.tree.tag_configure("odd", background="#F9FAFC")

        if paginate:
            foot = ctk.CTkFrame(self, fg_color="transparent")
            foot.grid(row=2, column=0, sticky="ew", pady=(8, 0))
            self.info = label(foot, "", 11, color=C["muted"])
            self.info.pack(side="left")
            kw = dict(text="", width=36, height=30, fg_color="#EEF2F7", hover_color="#DCE4EF")
            self.next_b = ctk.CTkButton(foot, image=icon("chev-r", C["text"], 16), command=lambda: self.go(1), **kw)
            self.next_b.pack(side="right")
            self.page_lbl = label(foot, "", 11, True)
            self.page_lbl.pack(side="right", padx=10)
            self.prev_b = ctk.CTkButton(foot, image=icon("chev-l", C["text"], 16), command=lambda: self.go(-1), **kw)
            self.prev_b.pack(side="right")

    @staticmethod
    def sort_key(v):
        if v is None or v == "":
            return (2, 0, "")
        try:
            return (0, float(str(v).replace(",", ".")), "")
        except ValueError:
            return (1, 0, str(v).lower())

    def set_size(self, value):
        self.page_size, self.page = int(value), 0
        self.apply()

    def on_search(self):
        self.page = 0
        self.apply()

    def sort_by(self, k):
        self.sort_rev = (not self.sort_rev) if self.sort_i == k else False
        self.sort_i, self.page = k, 0
        self.apply()

    def go(self, step):
        self.page += step
        self.apply()

    def set_rows(self, rows):
        self.rows = [tuple(r) for r in rows]
        self.page = 0
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
        self.tree.delete(*self.tree.get_children())
        for k, r in enumerate(shown):
            vals, iid = (r[1:], str(r[0])) if self.with_id else (r, None)
            self.tree.insert("", "end", iid=iid, values=["" if v is None else v for v in vals],
                             tags=("odd",) if k % 2 else ())
        for k, (title, _) in enumerate(self.columns):
            arrow = (" ▼" if self.sort_rev else " ▲") if self.sort_i == k else ""
            self.tree.heading(f"c{k}", text=title + arrow)
        if self.paginate:
            filt = f" (filtré sur {len(self.rows)})" if n != len(self.rows) else ""
            self.info.configure(text=f"Affichage de {a + 1 if n else 0} à {a + len(shown)} sur {n} entrée(s){filt}")
            self.page_lbl.configure(text=f"Page {self.page + 1} / {pages}")
            self.prev_b.configure(state="normal" if self.page > 0 else "disabled")
            self.next_b.configure(state="normal" if self.page < pages - 1 else "disabled")


class CrudPage(ctk.CTkFrame):
    """Page générique : formulaire à gauche, liste (DataTable) à droite."""

    def __init__(self, master, title, table, fields, list_sql, columns, after_insert=None,
                 list_params=None, insert_extra=None, actions=()):
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
        self.dt = DataTable(right, columns)
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
