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
from reportlab.platypus import Paragraph, Table, TableStyle

from app.utils import security

PW, PH = A4
M = 26
X0, X1 = M, PW - M
INNER_X, INNER_W = M + 2, 539
BOX_H = 128
FOOT_H = 18
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
def _header(c, b, ytop):
    h = b["header"]
    left = ("<font name='Helvetica-Bold' size='10.5'>%s</font><br/><font size='7.5'>%s</font>"
            "<br/><br/><font size='7.5'>%s</font>") % (escape(h["republique"]), escape(h["devise"]),
                                                       escape(h["ministere"]))
    _draw_par(c, _p(left, align=TA_LEFT, raw=True, leading=11), X0 + 8, ytop, 195)
    right = "<br/>".join(escape(t) for t in (h["direction"], h["inspection"]) if t)
    if right:
        _draw_par(c, _p(right, 8, align=TA_CENTER, raw=True, leading=10.5, font="Helvetica-Oblique"),
                  X1 - 8 - 190, ytop, 190)
    if h.get("logo"):
        try:
            c.drawImage(ImageReader(io.BytesIO(h["logo"])), PW / 2 - 31, ytop - 62, 62, 62,
                        preserveAspectRatio=True, mask="auto")
        except Exception:
            pass
    c.setFont(SERIF_B, 23)
    c.drawCentredString(PW / 2, ytop - 82, "Bulletin Scolaire de Notes")
    c.setFont(SERIF_B, 18)
    c.drawCentredString(PW / 2, ytop - 104, _fit(h["ecole"], SERIF_B, 18, 480))
    return ytop - 112


def _info(c, b, y):
    s = b["student"]
    c.setLineWidth(0.8)
    c.line(X0, y, X1, y)
    rows_l = [("Nom de l'élève :", s["nom"]), ("Sexe :", s["sexe"]), ("Classe :", s["classe"]),
              ("Année Scolaire :", s["annee"])]
    rows_r = [("Statut :", s["statut"]), ("Effectif :", s["effectif"]), ("Période :", s["periode"])]
    yy = y - 13
    for lab, val in rows_l:
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(X0 + 8, yy, lab)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(X0 + 98, yy, _fit(val, "Helvetica-Bold", 10, 230))
        yy -= 14
    if b.get("code"):
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(X0 + 340, y - 13, "N° du bulletin :")
        c.setFont("Helvetica-Bold", 10)
        c.drawString(X0 + 420, y - 13, b["code"])
    yy = y - 27
    for lab, val in rows_r:
        if val in ("", None):
            yy -= 14
            continue
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(X0 + 340, yy, lab)
        c.setFont("Helvetica", 9.5)
        c.drawString(X0 + 392, yy, _fit(val, "Helvetica", 9.5, 120))
        yy -= 14
    return y - 60


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
        ("FONTNAME", (1, 2), (-2, -1), "Helvetica"),
        ("FONTSIZE", (1, 2), (-2, -1), fs_num),
        ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("BACKGROUND", (0, 0), (-1, 1), GREY),
        ("SPAN", (0, 0), (0, 1)), ("SPAN", (8, 0), (10, 0)), ("SPAN", (11, 0), (11, 1)),
    ] + [("SPAN", (i, 0), (i, 1)) for i in range(1, 8)]

    def line(r, name_html, v, bold_cells=False):
        appr = _p(v.get("appr", ""), 6.8 if big else 6.2, italic=True, leading=7.8)
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


def draw_bulletin(c, b):
    security.draw_copy_pattern(c, PW, PH)                          # fond anti-photocopie
    security.draw_logo_watermark(c, b["header"].get("logo"), b["header"].get("ecole"), PW, PH)
    top = PH - M - 6
    y = _header(c, b, top)
    y = _info(c, b, y)
    y_boxes = M + FOOT_H
    n_per = len(b["periods"])
    sum_h = 15 + 14 * n_per
    y_sum = y_boxes + BOX_H + 6
    c.setLineWidth(0.8)
    c.line(X0, y, X1, y)
    th = _grade_table(c, b, y - 1, avail=(y - 1) - (y_sum + sum_h + 6))
    _summary(c, b, y_sum)
    _bottom(c, b, y_boxes)
    # cadre extérieur + pied de page
    c.setLineWidth(1.1)
    c.rect(X0, M + FOOT_H - 2, X1 - X0, PH - 2 * M - FOOT_H + 2)
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(X0 + 2, M + 3, "Ce bulletin est à conserver précieusement. Aucun duplicata ne sera délivré "
                                "en cas de perte !")
    c.drawRightString(X1 - 2, M + 3, "Imprimé le, " + b["date"])


def write_pdf(path, bulletins, title="Bulletins"):
    c = canvas.Canvas(path, pagesize=A4, pageCompression=1)
    c.setTitle(title)
    c.setAuthor("EduManager")
    for b in bulletins:
        draw_bulletin(c, b)
        c.showPage()
    c.save()
    return path