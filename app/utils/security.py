import hashlib
import io
import os
from functools import lru_cache

COPY_PROTECTION = False# False : désactive le motif anti-photocopie
LOGO_WATERMARK = True  # False : désactive le filigrane du logo
COPY_WORD = "PHOTOCOPIE"  # mot qui apparaîtra sur les photocopies
DPI = 300  # résolution du motif
DOT_GRAY = 150  # 0 = noir, 255 = blanc. Plus foncé = plus visible à la copie (mais plus visible à l'œil)
PITCH = 12  # pas (en pixels à 300 dpi) des gros points ; les petits ont un pas moitié
ANGLE = 30  # inclinaison du mot (degrés)
LOGO_ALPHA = 0.09  # opacité du logo en filigrane (0 à 1)
LOGO_SIZE = 300  # taille du logo en filigrane (points)


def _tile(tile, w, h):
    p = tile.width
    from PIL import Image
    row = Image.new("L", (w + p, p), 255)
    for x in range(0, w + p, p):
        row.paste(tile, (x, 0))
    page = Image.new("L", (w + p, h + p), 255)
    for y in range(0, h + p, p):
        page.paste(row, (0, y))
    return page.crop((0, 0, w, h))


def _font(size):
    import reportlab
    from PIL import ImageFont
    return ImageFont.truetype(os.path.join(os.path.dirname(reportlab.__file__), "fonts", "VeraBd.ttf"), size)


def _word_mask(w, h):
    from PIL import Image, ImageDraw
    f = _font(200)
    l, t, r, b = f.getbbox(COPY_WORD)
    f = _font(max(10, int(200 * (w * 0.80) / (r - l))))
    l, t, r, b = f.getbbox(COPY_WORD)
    txt = Image.new("L", (r - l + 20, b - t + 20), 0)
    ImageDraw.Draw(txt).text((10 - l, 10 - t), COPY_WORD, font=f, fill=255)
    txt = txt.rotate(ANGLE, expand=True, resample=Image.BICUBIC)
    mask = Image.new("L", (w, h), 0)
    for fy in (0.18, 0.50, 0.82):
        mask.paste(255, (int(w / 2 - txt.width / 2), int(fy * h - txt.height / 2)), txt)
    return mask.point(lambda v: 255 if v > 127 else 0)


@lru_cache(maxsize=4)
def copy_pattern(width_pt, height_pt):
    """Image (niveaux de gris) pleine page du motif anti-photocopie."""
    from PIL import Image, ImageDraw
    from reportlab.lib.utils import ImageReader
    w, h = round(width_pt / 72 * DPI), round(height_pt / 72 * DPI)
    big = DOT_GRAY

    a = Image.new("L", (PITCH, PITCH), 255)  # gros points : 1 point de 4x4 px par tuile
    q = PITCH // 3
    ImageDraw.Draw(a).rectangle([q, q, q + 3, q + 3], fill=big)

    half = PITCH // 2  # petits points : 4 points de 2x2 px (même densité)
    b = Image.new("L", (half, half), 255)
    ImageDraw.Draw(b).rectangle([1, 1, 2, 2], fill=big)

    page = Image.composite(_tile(b, w, h), _tile(a, w, h), _word_mask(w, h))
    return ImageReader(page)


def draw_copy_pattern(c, pw, ph):
    if COPY_PROTECTION:
        c.drawImage(copy_pattern(round(pw), round(ph)), 0, 0, pw, ph)


def draw_logo_watermark(c, logo, ecole, pw, ph):
    """Filigrane centré : logo en transparence, ou nom de l'école en diagonale s'il n'y a pas de logo."""
    if not LOGO_WATERMARK:
        return
    c.saveState()
    try:
        if logo:
            try:
                from reportlab.lib.utils import ImageReader
                img = ImageReader(io.BytesIO(logo))
                iw, ih = img.getSize()
                k = LOGO_SIZE / max(iw, ih)
                c.setFillAlpha(LOGO_ALPHA)
                c.drawImage(img, (pw - iw * k) / 2, (ph - ih * k) / 2 - 20, iw * k, ih * k, mask="auto")
                return
            except Exception:
                pass
        if ecole:
            c.setFillAlpha(0.07)
            c.setFont("Helvetica-Bold", 46)
            c.translate(pw / 2, ph / 2)
            c.rotate(35)
            c.drawCentredString(0, 0, str(ecole).upper())
    finally:
        c.restoreState()

def hash_pw(p):
    return hashlib.sha256(p.encode()).hexdigest()
