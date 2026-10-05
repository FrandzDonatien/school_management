import customtkinter as ctk

from app.constants import C, FONT
from app.ui.components.icons import icon


def button(parent, text, command, kind="primary", ic=None, **kw):
    colors = {"primary": (C["primary"], C["primary_dark"], "white"),
              "danger": (C["danger"], C["danger_hover"], "white"),
              "light": ("#EEF2F7", "#DCE4EF", C["text"])}[kind]
    extra = {}
    if ic:
        extra = dict(image=icon(ic, "#FFFFFF" if kind != "light" else C["text"], 18), compound="left")
    return ctk.CTkButton(parent, text=text, command=command, fg_color=colors[0], hover_color=colors[1],
                         text_color=colors[2], corner_radius=8, height=38, font=(FONT, 12, "bold"),
                         **extra, **kw)
