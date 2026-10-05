"""Icônes vectorielles (grille 24x24, trait arrondi) dessinées avec Pillow + logo de l'école."""
import math

import customtkinter as ctk
from PIL import Image, ImageDraw

from app.services.settings_service import logo_path

_TRAY = [(21, 15), (21, 19), (19, 21), (5, 21), (3, 19), (3, 15)]
ICONS = {
    "grid": [("rrect", 3, 3, 10, 10, 1.5), ("rrect", 14, 3, 21, 10, 1.5),
             ("rrect", 14, 14, 21, 21, 1.5), ("rrect", 3, 14, 10, 21, 1.5)],
    "cap": [("poly", [(12, 4), (22, 9), (12, 14), (2, 9)], True), ("line", [(6, 11.5), (6, 16.5)]),
            ("arc", 12, 16.5, 6, 0, 90), ("arc", 12, 16.5, 6, 90, 180), ("line", [(18, 11.5), (18, 16.5)]),
            ("line", [(22, 9), (22, 15)])],
    "user": [("circle", 12, 7.5, 4), ("line", [(20, 21), (20, 19)]), ("arc", 16, 19, 4, 270, 360),
             ("line", [(16, 15), (8, 15)]), ("arc", 8, 19, 4, 180, 270), ("line", [(4, 19), (4, 21)])],
    "book": [("rrect", 5, 3, 19, 21, 2), ("line", [(9, 3), (9, 21)]), ("line", [(12.5, 8), (15.5, 8)]),
             ("line", [(12.5, 12), (15.5, 12)])],
    "school": [("poly", [(2, 10), (12, 3), (22, 10)], False), ("poly", [(4, 10), (4, 21), (20, 21), (20, 10)], False),
               ("poly", [(10, 21), (10, 15), (14, 15), (14, 21)], False)],
    "pencil": [("poly", [(15.5, 4.5), (19.5, 8.5), (8.5, 19.5), (3.5, 20.5), (4.5, 15.5)], True),
               ("line", [(13, 7), (17, 11)])],
    "file": [("poly", [(14, 2), (6, 2), (4, 4), (4, 20), (6, 22), (18, 22), (20, 20), (20, 8), (14, 2)], True),
             ("poly", [(14, 2), (14, 8), (20, 8)], False), ("line", [(8, 13), (16, 13)]),
             ("line", [(8, 17), (16, 17)]), ("line", [(8, 9), (10, 9)])],
    "table": [("rrect", 3, 4, 21, 20, 2), ("line", [(3, 10), (21, 10)]), ("line", [(9.5, 10), (9.5, 20)]),
              ("line", [(15.5, 10), (15.5, 20)])],
    "clock": [("circle", 12, 12, 9), ("poly", [(12, 7), (12, 12), (15.5, 14)], False)],
    "calendar": [("rrect", 3, 5, 21, 21, 2), ("line", [(3, 10), (21, 10)]), ("line", [(8, 3), (8, 7)]),
                 ("line", [(16, 3), (16, 7)])],
    "gear": [("circle", 12, 12, 3), ("circle", 12, 12, 7), ("spokes", 12, 12, 7, 10.2, 8)],
    "logout": [("poly", [(9, 3), (5, 3), (3, 5), (3, 19), (5, 21), (9, 21)], False),
               ("poly", [(16, 17), (21, 12), (16, 7)], False), ("line", [(21, 12), (9, 12)])],
    "upload": [("poly", [(17, 8), (12, 3), (7, 8)], False), ("line", [(12, 3), (12, 15)]), ("poly", _TRAY, False)],
    "download": [("poly", [(7, 10), (12, 15), (17, 10)], False), ("line", [(12, 15), (12, 3)]), ("poly", _TRAY, False)],
    "search": [("circle", 11, 11, 7), ("line", [(16.5, 16.5), (21, 21)])],
    "plus": [("line", [(12, 5), (12, 19)]), ("line", [(5, 12), (19, 12)])],
    "trash": [("line", [(3, 6), (21, 6)]), ("poly", [(6, 6), (6, 20), (8, 22), (16, 22), (18, 20), (18, 6)], False),
              ("poly", [(9, 6), (9, 4), (10, 3), (14, 3), (15, 4), (15, 6)], False),
              ("line", [(10, 11), (10, 17)]), ("line", [(14, 11), (14, 17)])],
    "save": [("poly", [(5, 3), (16, 3), (21, 8), (21, 19), (19, 21), (5, 21), (3, 19), (3, 5), (5, 3)], True),
             ("poly", [(7, 3), (7, 8), (15, 8), (15, 3)], False), ("poly", [(7, 21), (7, 14), (17, 14), (17, 21)], False)],
    "zap": [("poly", [(13, 2), (4, 14), (12, 14), (11, 22), (20, 10), (12, 10), (13, 2)], True)],
    "check": [("poly", [(4, 12.5), (9.5, 18), (20, 6.5)], False)],
    "x": [("line", [(6, 6), (18, 18)]), ("line", [(18, 6), (6, 18)])],
    "lock": [("rrect", 5, 11, 19, 21, 2), ("line", [(8, 11), (8, 7)]), ("arc", 12, 7, 4, 180, 360),
             ("line", [(16, 7), (16, 11)])],
    "alert": [("poly", [(12, 3), (22, 20), (2, 20), (12, 3)], True), ("line", [(12, 9), (12, 14)]),
              ("dot", 12, 17, 0.9)],
    "chev-l": [("poly", [(15, 5), (8, 12), (15, 19)], False)],
    "chev-r": [("poly", [(9, 5), (16, 12), (9, 19)], False)],
    "copy": [("rrect", 9, 9, 21, 21, 2),
             ("poly", [(15, 9), (15, 5), (13, 3), (5, 3), (3, 5), (3, 13), (5, 15), (9, 15)], False)],
    "layers": [("poly", [(12, 3), (22, 8), (12, 13), (2, 8), (12, 3)], True),
               ("poly", [(2, 12), (12, 17), (22, 12)], False), ("poly", [(2, 16), (12, 21), (22, 16)], False)],
}
_ICON_CACHE = {}


def render_icon(name, color, size, scale=16):
    S = 24 * scale
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = 1.9 * scale
    wi = int(round(w))
    r = w / 2
    P = lambda p: (p[0] * scale, p[1] * scale)

    def cap(x, y):
        d.ellipse((x - r, y - r, x + r, y + r), fill=color)

    def stroke(pts):
        pts = [P(p) for p in pts]
        d.line(pts, fill=color, width=wi, joint="curve")
        for x, y in pts:
            cap(x, y)

    for prim in ICONS[name]:
        k = prim[0]
        if k == "line":
            stroke(prim[1])
        elif k == "poly":
            pts = list(prim[1])
            stroke(pts + [pts[0]] if prim[2] else pts)
        elif k == "rrect":
            _, x0, y0, x1, y1, rr = prim
            d.rounded_rectangle((x0 * scale - r, y0 * scale - r, x1 * scale + r, y1 * scale + r),
                                radius=rr * scale + r, outline=color, width=wi)
        elif k == "circle":
            _, cx, cy, rad = prim
            d.ellipse(((cx - rad) * scale - r, (cy - rad) * scale - r, (cx + rad) * scale + r,
                       (cy + rad) * scale + r), outline=color, width=wi)
        elif k == "dot":
            _, cx, cy, rad = prim
            d.ellipse(((cx - rad) * scale, (cy - rad) * scale, (cx + rad) * scale, (cy + rad) * scale), fill=color)
        elif k == "arc":
            _, cx, cy, rad, a0, a1 = prim
            d.arc(((cx - rad) * scale - r, (cy - rad) * scale - r, (cx + rad) * scale + r,
                   (cy + rad) * scale + r), a0, a1, fill=color, width=wi)
            for a in (a0, a1):
                cap(cx * scale + math.cos(math.radians(a)) * rad * scale,
                    cy * scale + math.sin(math.radians(a)) * rad * scale)
        elif k == "spokes":
            _, cx, cy, r0, r1, n = prim
            for i in range(n):
                a = math.radians(360 * i / n)
                stroke([(cx + math.cos(a) * r0, cy + math.sin(a) * r0), (cx + math.cos(a) * r1, cy + math.sin(a) * r1)])
    return img.resize((size * 3, size * 3), Image.LANCZOS)


def icon(name, color="#1C2434", size=18):
    key = (name, color, size)
    if key not in _ICON_CACHE:
        img = render_icon(name, color, size)
        _ICON_CACHE[key] = ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
    return _ICON_CACHE[key]


def logo_ctk(max_px):
    p = logo_path()
    if not p:
        return None
    try:
        img = Image.open(p).convert("RGBA")
        w, h = img.size
        r = min(max_px / w, max_px / h)
        return ctk.CTkImage(light_image=img, size=(max(1, int(w * r)), max(1, int(h * r))))
    except Exception:
        return None
