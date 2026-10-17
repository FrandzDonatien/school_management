import customtkinter as ctk

from app.constants import C, FONT, R
from app.ui.components.icons import icon

DANGER_LIGHT = "#FDE8EB"
TONES = {  # (texte, fond) des badges
    "success": (C["success"], C["success_light"]),
    "danger": (C["danger"], DANGER_LIGHT),
    "warning": (C["warning"], C["warning_light"]),
    "primary": (C["primary"], C["primary_light"]),
}

def card(parent, **kw):
    return ctk.CTkFrame(parent, fg_color=C["card"], corner_radius=R, border_width=1,
                        border_color=C["border"], **kw)

def label(parent, text, size=12, bold=False, color=None, **kw):
    return ctk.CTkLabel(parent, text=text, text_color=color or C["text"],
                        font=(FONT, size, "bold" if bold else "normal"), **kw)

def badge(parent, text, tone="primary"):
    fg, bg = TONES.get(tone, TONES["primary"])
    return ctk.CTkLabel(parent, text=f" {text} ", text_color=fg, fg_color=bg, corner_radius=10,
                        height=22, font=(FONT, 10, "bold"))

class StatCard(ctk.CTkFrame):
    """Carte KPI : titre + icône en carré arrondi, grande valeur, badge + légende."""

    def __init__(self, master, title, ic, color, light):
        super().__init__(master, fg_color=C["card"], corner_radius=R, border_width=1, border_color=C["border"])
        self._ic = ic
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(18, 0))
        label(top, title, 12, True, C["muted"]).pack(side="left")
        ctk.CTkLabel(top, text="", image=icon(ic, color, 20), width=40, height=40, corner_radius=10,
                     fg_color=light).pack(side="right")
        self.value = label(self, "0", 30, True)
        self.value.pack(anchor="w", padx=20, pady=(2, 0))
        self.foot = ctk.CTkFrame(self, fg_color="transparent")
        self.foot.pack(fill="x", padx=20, pady=(6, 18))
        self._badge = None
        self.sub = label(self.foot, "", 11, color=C["muted"])
        self.sub.pack(side="left")

    def set(self, value, sub="", badge_text=None, tone="primary"):
        self.value.configure(text=value)
        self.sub.configure(text=sub)
        if self._badge is not None:
            self._badge.destroy()
            self._badge = None
        if badge_text:
            self._badge = badge(self.foot, badge_text, tone)
            self._badge.pack(side="left", padx=(0, 8), before=self.sub)


class RankList(ctk.CTkFrame):
    """Liste type « top performers » : avatar à initiales, nom, classe, note et barre de progression."""

    def __init__(self, master, title, subtitle, tone="primary", maximum=20):
        super().__init__(master, fg_color=C["card"], corner_radius=R, border_width=1, border_color=C["border"])
        self.tone, self.maximum = tone, maximum
        label(self, title, 15, True).pack(anchor="w", padx=20, pady=(16, 0))
        label(self, subtitle, 11, color=C["muted"]).pack(anchor="w", padx=20, pady=(0, 8))
        ctk.CTkFrame(self, height=1, fg_color=C["border"]).pack(fill="x")
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=20, pady=(8, 14))

    def set(self, items):
        """items : liste de (nom, sous-titre, valeur)."""
        for w in self.body.winfo_children():
            w.destroy()
        fg, bg = TONES[self.tone]
        if not items:
            label(self.body, "Aucune donnée", 12, color=C["muted"]).pack(pady=24)
            return
        for name, sub, val in items:
            row = ctk.CTkFrame(self.body, fg_color="transparent")
            row.pack(fill="x", pady=6)
            ini = "".join(p[0] for p in name.split()[:2]).upper() or "?"
            ctk.CTkLabel(row, text=ini, width=38, height=38, corner_radius=19, fg_color=bg, text_color=fg,
                         font=(FONT, 12, "bold")).pack(side="left")
            mid = ctk.CTkFrame(row, fg_color="transparent")
            mid.pack(side="left", fill="x", expand=True, padx=12)
            head = ctk.CTkFrame(mid, fg_color="transparent")
            head.pack(fill="x")
            label(head, name, 12, True).pack(side="left")
            label(head, f"{val:.2f}", 12, True, fg).pack(side="right")
            label(mid, sub, 10, color=C["muted"]).pack(anchor="w")
            bar = ctk.CTkProgressBar(mid, height=6, corner_radius=3, fg_color=C["bg"], progress_color=fg)
            bar.pack(fill="x", pady=(3, 0))
            bar.set(max(0.0, min(1.0, val / self.maximum)))
