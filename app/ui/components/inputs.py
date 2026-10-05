import customtkinter as ctk

from app.constants import C, FONT
from app.ui.components.card import label


def entry(parent, placeholder="", **kw):
    return ctk.CTkEntry(parent, placeholder_text=placeholder, height=38, corner_radius=8, border_width=1,
                        border_color="#DCE3EC", fg_color="white", text_color=C["text"], font=(FONT, 12), **kw)


def combo(parent, values, command=None, **kw):
    return ctk.CTkComboBox(parent, values=values or [""], command=command, state="readonly", height=38,
                           corner_radius=8, border_width=1, border_color="#DCE3EC", fg_color="white",
                           button_color="#E8EDF3", button_hover_color="#CBD5E1", text_color=C["text"],
                           dropdown_font=(FONT, 12), font=(FONT, 12), **kw)


def labeled_combo(parent, col, text, command=None, values=None):
    box = ctk.CTkFrame(parent, fg_color="transparent")
    box.grid(row=0, column=col, sticky="ew", padx=14, pady=16)
    label(box, text, 12, color=C["muted"]).pack(anchor="w", pady=(0, 3))
    cb = combo(box, values or [""], command=command)
    cb.pack(fill="x")
    return cb
