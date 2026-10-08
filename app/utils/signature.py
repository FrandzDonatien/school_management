"""Signatures des enseignants, imprimées sur le bulletin (colonne « Appréciations générales »).

Une image PNG par enseignant dans assets/signatures/, nommée d'après son nom : « amakou.png ».
Si l'enseignant a un prénom, « nom_prenom.png » est cherché en premier, puis « nom.png ».
Il suffit donc de déposer des fichiers NOM.png dans le dossier, ou d'utiliser le bouton « Choisir… » de la
fiche enseignant, qui détoure automatiquement la signature (fond du papier rendu transparent, marges rognées).
"""
import os

from app.config import SIGNATURES_DIR
from app.utils.formatting import norm

EXTS = (".png", ".jpg", ".jpeg")
MAX_WIDTH = 500          # largeur maximale de l'image enregistrée (en pixels)
_cache = {}              # {(chemin, date de modification): octets}


def _names(nom, prenom=""):
    """Noms de fichier possibles (sans extension), du plus précis au plus général."""
    n, p = norm(nom), norm(prenom)
    return [f"{n}_{p}", n] if p and n else ([n] if n else [])


def find(nom, prenom=""):
    """Chemin de la signature de l'enseignant, ou None."""
    for name in _names(nom, prenom):
        for ext in EXTS:
            path = os.path.join(SIGNATURES_DIR, name + ext)
            if os.path.isfile(path):
                return path
    return None


def load_bytes(nom, prenom=""):
    """Contenu de l'image (pour l'insérer dans le PDF), ou None."""
    path = find(nom, prenom)
    if not path:
        return None
    key = (path, os.path.getmtime(path))
    if key not in _cache:
        with open(path, "rb") as f:
            _cache[key] = f.read()
    return _cache[key]


def process(img):
    """Image PIL -> signature détourée : l'encre reste opaque, le papier devient transparent, marges rognées."""
    from PIL import Image
    im = img.convert("RGB")
    g = im.convert("L")
    hist, total, acc, bg = g.histogram(), g.width * g.height, 0, 255
    for v, n in enumerate(hist):             # niveau de gris du papier = 80e centile (le papier domine l'image)
        acc += n
        if acc >= total * 0.80:
            bg = v
            break
    hi = max(60, bg - 30)                    # plus clair que « hi » : transparent
    lo = max(0, hi - 90)                     # plus sombre que « lo » : opaque
    alpha = g.point(lambda v: 255 if v <= lo else 0 if v >= hi else int(255 * (hi - v) / (hi - lo)))
    alpha = alpha.point(lambda v: 0 if v < 50 else v)       # efface les points parasites très pâles (grain du papier)
    im.putalpha(alpha)
    box = alpha.point(lambda v: 255 if v > 60 else 0).getbbox()
    if box:
        pad = 6
        im = im.crop((max(0, box[0] - pad), max(0, box[1] - pad), min(im.width, box[2] + pad), min(im.height, box[3] + pad)))
    if im.width > MAX_WIDTH:
        im = im.resize((MAX_WIDTH, max(1, round(im.height * MAX_WIDTH / im.width))), Image.LANCZOS)
    return im


def import_image(src, nom, prenom=""):
    """Détoure l'image choisie et l'enregistre comme signature de l'enseignant. Retourne le chemin du fichier."""
    from PIL import Image, ImageOps
    names = _names(nom, prenom)
    if not names:
        raise ValueError("Nom d'enseignant vide.")
    with Image.open(src) as im:
        out = process(ImageOps.exif_transpose(im))
    os.makedirs(SIGNATURES_DIR, exist_ok=True)
    remove(nom, prenom)                      # une seule signature par enseignant
    dest = os.path.join(SIGNATURES_DIR, names[0] + ".png")
    out.save(dest, "PNG", optimize=True)
    return dest


def remove(nom, prenom=""):
    """Supprime la signature affichée pour cet enseignant. Retourne True si un fichier a été supprimé."""
    path = find(nom, prenom)
    if path:
        os.remove(path)
    return bool(path)