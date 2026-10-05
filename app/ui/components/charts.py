"""Graphiques (barres, barres horizontales, donut, courbe) dessinés sur Canvas."""
import customtkinter as ctk

from app.constants import C, CHART_COLORS, FONT, R
from app.ui.components.card import label
from app.utils.formatting import num, trunc


class Chart(ctk.CTkFrame):
    def __init__(self, master, title, kind, center="", ymax=None):
        super().__init__(master, fg_color=C["card"], corner_radius=R, border_width=1, border_color=C["border"])
        label(self, title, 15, True).pack(anchor="w", padx=20, pady=(16, 0))
        self.canvas = ctk.CTkCanvas(self, bg="white", highlightthickness=0, height=210)
        self.canvas.pack(fill="both", expand=True, padx=16, pady=(8, 14))
        self.canvas.bind("<Configure>", lambda e: self.draw())
        self.kind, self.center, self.ymax, self.data = kind, center, ymax, []

    def set(self, data):
        self.data = data
        self.draw()

    def draw(self):
        c = self.canvas
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        if w < 60 or h < 60:
            return
        vals = [v for _, v in self.data if v is not None]
        if not vals or (self.kind != "line" and not any(vals)):
            c.create_text(w / 2, h / 2, text="Aucune donnée", fill=C["muted"], font=(FONT, 11))
            return
        getattr(self, "_" + self.kind)(c, w, h)

    def _bar(self, c, w, h):
        n, mx = len(self.data), max(v for _, v in self.data) or 1
        top, bottom = 24, 30
        slot = (w - 20) / n
        bw = min(46, slot * 0.55)
        for i in range(5):
            y = top + (h - top - bottom) * i / 4
            c.create_line(0, y, w, y, fill="#EEF2F6")
        for i, (name, v) in enumerate(self.data):
            x = 10 + slot * i + slot / 2
            bh = (h - top - bottom) * v / mx
            c.create_rectangle(x - bw / 2, h - bottom - bh, x + bw / 2, h - bottom,
                               fill=CHART_COLORS[i % len(CHART_COLORS)], outline="")
            c.create_text(x, h - bottom + 14, text=trunc(name, max(4, int(slot / 7))), fill=C["muted"], font=(FONT, 9))
            c.create_text(x, h - bottom - bh - 10, text=num(v), fill=C["text"], font=(FONT, 10, "bold"))

    def _hbar(self, c, w, h):
        n, mx = len(self.data), max(v for _, v in self.data) or 1
        lw = min(150, w * 0.38)
        rh = min(30, (h - 10) / n)
        for i, (name, v) in enumerate(self.data):
            y = 8 + rh * i + rh / 2
            c.create_text(lw - 8, y, text=trunc(name, 22), anchor="e", fill=C["text"], font=(FONT, 10))
            bl = max(2, (w - lw - 50) * v / mx)
            c.create_rectangle(lw, y - rh * 0.3, lw + bl, y + rh * 0.3, fill=CHART_COLORS[i % len(CHART_COLORS)], outline="")
            c.create_text(lw + bl + 6, y, text=num(v), anchor="w", fill=C["text"], font=(FONT, 10, "bold"))

    def _donut(self, c, w, h):
        d = min(h - 16, w * 0.52)
        x0, y0 = 10, (h - d) / 2
        thick = max(18, d * 0.2)
        ins = thick / 2
        box = (x0 + ins, y0 + ins, x0 + d - ins, y0 + d - ins)
        total = sum(v for _, v in self.data)
        nz = [(i, n, v) for i, (n, v) in enumerate(self.data) if v]
        if len(nz) == 1:
            c.create_oval(*box, outline=CHART_COLORS[nz[0][0] % len(CHART_COLORS)], width=thick)
        else:
            start = 90
            for i, n, v in nz:
                ext = 360 * v / total
                c.create_arc(*box, start=start, extent=-ext, style="arc", width=thick,
                             outline=CHART_COLORS[i % len(CHART_COLORS)])
                start -= ext
        cx, cy = x0 + d / 2, y0 + d / 2
        c.create_text(cx, cy - 6, text=num(total), fill=C["text"], font=(FONT, 20, "bold"))
        c.create_text(cx, cy + 14, text=self.center, fill=C["muted"], font=(FONT, 9))
        lx = x0 + d + 20
        ly = h / 2 - len(self.data) * 11 + 11
        for i, (n, v) in enumerate(self.data):
            y = ly + i * 24
            c.create_rectangle(lx, y - 6, lx + 12, y + 6, fill=CHART_COLORS[i % len(CHART_COLORS)], outline="")
            pct = 100 * v / total if total else 0
            c.create_text(lx + 20, y, anchor="w", fill=C["text"], font=(FONT, 10),
                          text=f"{trunc(n, 16)}  {num(v)} ({pct:.0f}%)")

    def _line(self, c, w, h):
        left, right, top, bottom = 36, 16, 22, 30
        vals = [v for _, v in self.data if v is not None]
        ymax = self.ymax or (max(vals) * 1.15) or 1
        for i in range(5):
            y = top + (h - top - bottom) * i / 4
            c.create_line(left, y, w - right, y, fill="#EEF2F6")
            c.create_text(left - 6, y, text=num(ymax * (1 - i / 4)), anchor="e", fill=C["muted"], font=(FONT, 9))
        n = len(self.data)
        pts = []
        for i, (name, v) in enumerate(self.data):
            x = left + 24 + (w - left - right - 48) * (i / (n - 1) if n > 1 else 0.5)
            c.create_text(x, h - bottom + 14, text=name, fill=C["muted"], font=(FONT, 9))
            pts.append(None if v is None else (x, top + (h - top - bottom) * (1 - v / ymax), v))
        for a, b in zip(pts, pts[1:]):
            if a and b:
                c.create_line(a[0], a[1], b[0], b[1], fill=C["primary"], width=3)
        for p in pts:
            if p:
                c.create_oval(p[0] - 5, p[1] - 5, p[0] + 5, p[1] + 5, fill="white", outline=C["primary"], width=2)
                c.create_text(p[0], p[1] - 14, text=num(p[2]), fill=C["text"], font=(FONT, 10, "bold"))
