import customtkinter as ctk

from app.constants import C, FONT, R
from app.ui.components.icons import icon


def card(parent, **kw):
    return ctk.CTkFrame(parent, fg_color=C["card"], corner_radius=R, border_width=1,
                        border_color=C["border"], **kw)


def label(parent, text, size=12, bold=False, color=None, **kw):
    return ctk.CTkLabel(parent, text=text, text_color=color or C["text"],
                        font=(FONT, size, "bold" if bold else "normal"), **kw)


class StatCard(ctk.CTkFrame):
    def __init__(self, master, title, ic, color, light):
        super().__init__(master, fg_color=C["card"], corner_radius=R, border_width=1, border_color=C["border"])
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=22, pady=(22, 0))
        ctk.CTkLabel(top, text="", image=icon(ic, color, 24), width=50, height=50, corner_radius=25,
                     fg_color=light).pack(side="left")
        self.value = label(top, "0", 30, True)
        self.value.pack(side="right")
        label(self, title, 12, color=C["muted"]).pack(anchor="w", padx=22, pady=(12, 22))
