"""Rendu PDF (A4 portrait, imprimable) du bulletin scolaire de notes, avec reportlab.

Ce module ne dépend d'aucune autre partie de l'application (hors app/reports/security.py) : il reçoit des dictionnaires
déjà formatés (voir `app/services/bulletin_service.py`, fonction `build_bulletins`) et
écrit un PDF contenant une page par élève.
"""
import io
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.platypus import Image as RLImage, Paragraph, Table, TableStyle
from app.utils import security

PW, PH = A4
M = 26                      # marge de la page
X0, X1 = M, PW - M          # cadre extérieur
INNER_X, INNER_W = M + 2, 539
BOX_H = 128                 # hauteur du bloc Distinctions / Décision / Visa
FOOT_H = 18                 # hauteur réservée au pied de page
GREY = colors.Color(0.90, 0.90, 0.90)
GREY2 = colors.Color(0.80, 0.80, 0.80)
SERIF_B = "Times-Bold"

COLS = [100, 34, 34, 34, 38, 28, 42, 42, 34, 34, 34, 85]   # total = 539


def _p(text, size=8.0, bold=False, align=TA_CENTER, italic=False, leading=None, raw=False, font=None):
    name = font or ("Helvetica-Bold" if bold else "Helvetica-Oblique" if italic else "Helvetica")
    st = ParagraphStyle("p", fontName=name, fontSize=size, leading=leading or size * 1.18, alignment=align,
                        textColor=colors.black)
    return Paragraph(text if raw else escape(str(text)), st)


def _fit(text, font, size, maxw):
    text = str(text or "")
    if stringWidth(text, font, size) <= maxw:
        return text
    while text and stringWidth(text + "...", font, size) > maxw:
        text = text[:-1]
    return text + "..."


def _draw_par(c, par, x, y_top, w):
    _, h = par.wrap(w, 1000)
    par.drawOn(c, x, y_top - h)
    return h


def _checkbox(c, x, y, checked):
    c.setLineWidth(0.7)
    c.rect(x, y, 7, 7)
    if checked:
        c.setLineWidth(1.2)
        c.line(x + 1, y + 1, x + 6, y + 6)
        c.line(x + 1, y + 6, x + 6, y + 1)
    c.setLineWidth(0.7)


# ----------------------------------------------------------------------------- en-tête
# Trois cadres séparés comme sur le bulletin papier : 1) ministère / logo / République, 2) école, année et titre,
# 3) informations de l'élève.
GAP = 3                      # espace entre les cadres
HEAD_MIN_H, TITLE_H, INFO_H = 72, 60, 52
LEFT_W = 134                 # largeur du bloc ministère / direction (la direction régionale passe sur 2 lignes)
STARS = "<font name='Times-Bold' size='6.5'>*** *** ***</font>"
_STATUT_F = {"nouveau": "Nouvelle", "redoublant": "Redoublante", "ancien": "Ancienne"}


def _box(c, y_top, h):
    c.setLineWidth(0.8)
    c.rect(INNER_X, y_top - h, INNER_W, h)


def _header(c, b, ytop):
    """Cadre ministère / logo / République, puis cadre « école – année scolaire – titre ». Retourne le y du bas."""
    h = b["header"]
    # gauche : ministère, direction régionale, inspection (centrés, séparés par des étoiles)
    items = [t for t in (h.get("ministere"), h.get("direction"), h.get("inspection")) if t]
    html = ""
    for i, t in enumerate(items):
        if i:
            html += "<br/>" + STARS + "<br/>" + ("<font size='5'>&nbsp;</font><br/>" if i == len(items) - 1 and i > 1 else "")
        html += escape(t)
    left = _p(html, 8.5, align=TA_CENTER, raw=True, leading=10.2, font="Times-Roman") if items else None
    # droite : République + devise nationale
    devise = (h.get("devise") or "").replace(" - ", "-")
    right = _p("%s<br/>%s" % (escape((h.get("republique") or "").upper()), escape(devise)), 9, align=TA_CENTER,
               raw=True, leading=11.5, font="Times-Roman")
    lh = left.wrap(LEFT_W, 1000)[1] if left else 0
    rh = right.wrap(130, 1000)[1]
    box_h = max(HEAD_MIN_H, lh + 12, rh + 12)
    _box(c, ytop, box_h)
    if left:
        left.drawOn(c, INNER_X + 93 - LEFT_W / 2, ytop - 6 - lh)
    right.drawOn(c, INNER_X + INNER_W - 8 - 130, ytop - 6 - rh)
    cx = PW / 2
    if h.get("logo"):
        try:
            c.drawImage(ImageReader(io.BytesIO(h["logo"])), cx - 27, ytop - 4 - 54, 54, 54,
                        preserveAspectRatio=True, mask="auto")
        except Exception:
            pass
    if h.get("motto"):
        c.setFont("Times-Roman", 6.5)
        c.drawCentredString(cx, ytop - box_h + 5, str(h["motto"]).upper())

    # cadre titre : établissement, année scolaire, période
    top = ytop - box_h - GAP
    _box(c, top, TITLE_H)
    s = b["student"]
    c.setFont(SERIF_B, 19)
    c.drawCentredString(cx, top - 22, _fit(h.get("ecole", ""), SERIF_B, 19, 440))
    c.setFont(SERIF_B, 10.5)
    c.drawCentredString(cx, top - 37, "ANNÉE SCOLAIRE : " + str(s.get("annee", "")))
    c.setFont(SERIF_B, 12.5)
    c.drawCentredString(cx, top - 53, "Bulletin de notes du " + str(s.get("periode", "")))
    return top - TITLE_H - GAP


def _info(c, b, y):
    """Cadre des informations de l'élève (nom, sexe, statut à gauche ; numéro, classe, effectif à droite)."""
    s = b["student"]
    _box(c, y, INFO_H)
    x = INNER_X + 8
    statut = s.get("statut") or ""
    if s.get("sexe") == "Féminin":
        statut = _STATUT_F.get(statut.strip().lower(), statut)
    c.setFont("Times-Italic", 9.5)
    c.drawString(x, y - 16, "Nom et Prénoms de l'Élève :")
    c.setFont("Times-Bold", 11.5)
    c.drawString(INNER_X + 150, y - 16, _fit(s.get("nom", ""), "Times-Bold", 11.5, 190))
    if b.get("code"):
        c.setFont("Helvetica-Bold", 8)
        c.drawString(INNER_X + 350, y - 16, "N° du bulletin :")
        c.setFont("Helvetica-Bold", 9.5)
        c.drawString(INNER_X + 415, y - 16, b["code"])
    for yy, lab, val, lab2, val2 in ((y - 32, "Sexe :", s.get("sexe", ""), "Classe :", s.get("classe", "")),
                                     (y - 45, "Statut :", statut, "Effectif :", s.get("effectif", ""))):
        c.setFont("Times-Italic", 8.5)
        c.drawString(x, yy, lab)
        c.drawString(INNER_X + 372, yy, lab2)
        c.setFont("Times-Roman", 8.5)
        if val not in ("", None):
            c.drawString(x + 52, yy, str(val))
        if val2 not in ("", None):
            c.drawString(INNER_X + 415, yy, _fit(val2, "Times-Roman", 8.5, 110))
    return y - INFO_H - GAP


# ----------------------------------------------------------------------------- tableau des notes
def _grade_table(c, b, y_top, avail):
    groups = b["groups"]
    n_rows = sum(len(g["rows"]) + (1 if g.get("avg") else 0) for g in groups)
    n_titles = sum(1 for g in groups if g.get("title"))
    body_avail = avail - 36 - 15 * n_titles
    rh = max(17.0, min(32.0, body_avail / n_rows)) if n_rows else 20.0
    big = rh >= 26
    fs_num, fs_name, fs_t = (9.5, 9.5, 7) if big else (8.5, 8.5, 6.3)

    hp = lambda t: _p(t, 7.2, True, raw=True, leading=8.4)
    data = [
        [hp("Discipline<br/><font name='Helvetica' size='6.5'>Nom du professeur</font>"),
         hp("Moy.<br/>Interro"), hp("Note de<br/>Devoir"), hp("Note de<br/>Compo"), hp("Moy.<br/>sur 20"),
         hp("Coef"), hp("Note<br/>définitive"), hp("Rang"), hp("Moyennes de la Classe"), "", "",
         hp("Appréciations<br/>Générales")],
        ["", "", "", "", "", "", "", "", hp("Moy.<br/>Min"), hp("Moy.<br/>Max"), hp("Moy.<br/>Gén."), ""],
    ]
    heights = [19, 19]
    style = [
        ("GRID", (0, 0), (-1, -1), 0.6, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 2), (-2, -1), "CENTER"),
        ("ALIGN", (11, 2), (11, -1), "CENTER"),  # signature centrée sous l'appréciation
        ("FONTNAME", (1, 2), (-2, -1), "Helvetica"),
        ("FONTSIZE", (1, 2), (-2, -1), fs_num),
        ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("BACKGROUND", (0, 0), (-1, 1), GREY),
        ("SPAN", (0, 0), (0, 1)), ("SPAN", (8, 0), (10, 0)), ("SPAN", (11, 0), (11, 1)),
    ] + [("SPAN", (i, 0), (i, 1)) for i in range(1, 8)]

    def appr_cell(v):
        """Appréciation, suivie de la signature de l'enseignant (réduite pour tenir dans la hauteur de la ligne)."""
        appr = _p(v.get("appr", ""), 6.8 if big else 6.2, italic=True, leading=7.8)
        free_h = rh - 2 - 7.8 - 1
        if not v.get("sig") or free_h < 7:
            return appr
        try:
            w, h = ImageReader(io.BytesIO(v["sig"])).getSize()
            k = min((COLS[11] - 8) / w, free_h / h)
            return [appr, RLImage(io.BytesIO(v["sig"]), width=w * k, height=h * k)]
        except Exception:
            return appr

    def line(r, name_html, v, bold_cells=False):
        appr = appr_cell(v)
        return [_p(name_html, align=TA_LEFT, raw=True, leading=fs_name + 1.4),
                v.get("interro", ""), v.get("devoir", ""), v.get("compo", ""), v.get("mg", ""),
                v.get("coef", ""), v.get("nd", ""), v.get("rang", ""), v.get("min", ""), v.get("max", ""),
                v.get("moy", ""), appr]

    for g in groups:
        if g.get("title"):
            r = len(data)
            data.append([_p(g["title"], 9.5, True, font=SERIF_B)] + [""] * 11)
            heights.append(15)
            style += [("SPAN", (0, r), (-1, r)), ("BACKGROUND", (0, r), (-1, r), GREY2)]
        for v in g["rows"]:
            r = len(data)
            name = ("<font name='Helvetica-Bold' size='%s'>%s</font><br/><font name='Helvetica' size='%s'>%s</font>"
                    % (fs_name, escape(v["name"].upper()), fs_t, escape(v.get("teacher", ""))))
            data.append(line(r, name, v))
            heights.append(rh)
            style += [("FONTNAME", (4, r), (4, r), "Helvetica-Bold"), ("FONTNAME", (6, r), (6, r), "Helvetica-Bold")]
        a = g.get("avg")
        if a:
            r = len(data)
            name = "<font name='Helvetica-Bold' size='%s'>%s</font>" % (fs_name, escape(a["label"]))
            data.append(line(r, name, a))
            heights.append(rh * 0.92)
            style += [("FONTNAME", (1, r), (-2, r), "Helvetica-Bold"), ("BACKGROUND", (0, r), (-1, r), GREY)]

    t = Table(data, colWidths=COLS, rowHeights=heights)
    t.setStyle(TableStyle(style))
    _, th = t.wrapOn(c, INNER_W, 1000)
    t.drawOn(c, INNER_X, y_top - th)
    return th


# ----------------------------------------------------------------------------- récapitulatif des périodes
def _summary(c, b, y_bottom):
    rows = [[_p(t, 7.8, True, raw=True) for t in ("Période", "Moy. Élève", "Rang", "Plus forte Moy.",
                                                    "Plus faible Moy.", "Moy. Gle Classe")]]
    for p in b["periods"]:
        rows.append([p["label"], p["moy"], p["rang"], p["max"], p["min"], p["avg"]])
    t = Table(rows, colWidths=[110, 75, 114, 80, 80, 80], rowHeights=[15] + [14] * (len(rows) - 1))
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, colors.black), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("FONTNAME", (0, 1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, -1), 8.5), ("BACKGROUND", (0, 0), (-1, 0), GREY),
        ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    _, th = t.wrapOn(c, INNER_W, 1000)
    t.drawOn(c, INNER_X, y_bottom)
    return th


# ----------------------------------------------------------------------------- bas de page
def _bottom(c, b, y0):
    """Distinctions / Décision du conseil / Visa. y0 = bas des cases."""
    w1, w2, w3 = 165, 195, 179
    x1 = INNER_X
    x2, x3 = x1 + w1, x1 + w1 + w2
    top = y0 + BOX_H
    c.setLineWidth(0.8)
    for x, w in ((x1, w1), (x2, w2), (x3, w3)):
        c.rect(x, y0, w, BOX_H)

    def title(x, w, y, text, size=10):
        c.setFont(SERIF_B, size)
        c.drawCentredString(x + w / 2, y, text)

    # Distinctions + sanctions
    title(x1, w1, top - 11, "Distinctions")
    c.setLineWidth(0.5)
    c.line(x1, top - 15, x1 + w1, top - 15)
    yy = top - 26
    for lab, ok in b["distinctions"]:
        _checkbox(c, x1 + 6, yy - 1.5, ok)
        c.setFont("Helvetica", 8)
        c.drawString(x1 + 18, yy, lab)
        yy -= 11
    ys = top - 79
    c.line(x1, top - 65, x1 + w1, top - 65)
    title(x1, w1, top - 75, "Sanctions")
    c.line(x1, ys, x1 + w1, ys)
    yy = ys - 12
    for lab, val in b["discipline"]:
        c.setFont("Helvetica", 7.6)
        c.drawString(x1 + 5, yy, lab)
        lw = stringWidth(lab, "Helvetica", 7.6)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(x1 + 8 + lw, yy, _fit(val, "Helvetica-Bold", 8, w1 - lw - 14))
        yy -= 10.5

    # Décision du conseil
    title(x2, w2, top - 11, "Décision du conseil de classe")
    c.setLineWidth(0.5)
    c.line(x2, top - 15, x2 + w2, top - 15)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(x2 + w2 / 2, top - 45, _fit(b["decision"], "Helvetica-Bold", 11, w2 - 12))
    c.line(x2, top - 62, x2 + w2, top - 62)
    c.setFont(SERIF_B, 8.5)
    c.drawCentredString(x2 + w2 / 2, top - 74, "Signature et Nom du professeur titulaire")
    c.setFont("Helvetica-Bold", 8.5)
    c.drawCentredString(x2 + w2 / 2, y0 + 7, _fit(b["titulaire"], "Helvetica-Bold", 8.5, w2 - 10))

    # Visa
    title(x3, w3, top - 11, "Visa du Chef d'établissement")
    c.line(x3, top - 15, x3 + w3, top - 15)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawCentredString(x3 + w3 / 2, y0 + 7, _fit(b["chef"], "Helvetica-Bold", 8.5, w3 - 10))


def draw_bulletin(c, b, protect=True):
    if protect:
        security.draw_copy_pattern(c, PW, PH)                      # fond anti-photocopie
    security.draw_logo_watermark(c, b["header"].get("logo"), b["header"].get("ecole"), PW, PH)
    top = PH - M - 6
    y = _header(c, b, top)
    y = _info(c, b, y)
    y_boxes = M + FOOT_H
    n_per = len(b["periods"])
    sum_h = 15 + 14 * n_per
    y_sum = y_boxes + BOX_H + 6
    th = _grade_table(c, b, y, avail=y - (y_sum + sum_h + 6))
    _summary(c, b, y_sum)
    _bottom(c, b, y_boxes)
    # cadre extérieur + pied de page
    c.setLineWidth(1.1)
    c.rect(X0, M + FOOT_H - 2, X1 - X0, PH - 2 * M - FOOT_H + 2)
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(X0 + 2, M + 3, "Ce bulletin est à conserver précieusement. Aucun duplicata ne sera délivré "
                                "en cas de perte !")
    c.drawRightString(X1 - 2, M + 3, "Imprimé le, " + b["date"])


def write_pdf(path, bulletins, title="Bulletins", preview=False):
    """path : chemin ou objet fichier (BytesIO). preview=True : sans motif anti-photocopie (aperçu à l'écran)."""
    c = canvas.Canvas(path, pagesize=A4, pageCompression=1)
    c.setTitle(title)
    c.setAuthor("EduManager")
    for b in bulletins:
        draw_bulletin(c, b, protect=not preview)
        c.showPage()
    c.save()
    return path