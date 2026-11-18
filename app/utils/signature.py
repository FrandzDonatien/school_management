"""Signatures des enseignants, imprimées sur le bulletin (colonne « Appréciations générales »).

Les signatures sont stockées dans la base (table `signatures`, image PNG en BLOB), une par enseignant,
identifiée par son nom normalisé : « amakou_komlan » (nom_prenom) ou « amakou » (nom seul).
Si l'enseignant a un prénom, « nom_prenom » est cherché en premier, puis « nom ».
Le bouton « Choisir… » de la fiche enseignant détoure automatiquement la signature
(fond du papier rendu transparent, marges rognées).
Les anciens fichiers du dossier SIGNATURES_DIR sont repris dans la base au premier lancement.
"""
import io
import os

from app.config import SIGNATURES_DIR
from app.database.connection import execute, query
from app.services.settings_service import set_setting
from app.utils.formatting import norm

EXTS = (".png", ".jpg", ".jpeg")
MAX_WIDTH = 500          # largeur maximale de l'image enregistrée (en pixels)
_cache = {}              # {clé: octets} ; vidé à chaque écriture


def _names(nom, prenom=""):
    """Clés possibles, de la plus précise à la plus générale."""
    n, p = norm(nom), norm(prenom)
    return [f"{n}_{p}", n] if p and n else ([n] if n else [])


def find(nom, prenom=""):
    """Clé de la signature de l'enseignant dans la base, ou None (valeur « vraie » si elle existe)."""
    for name in _names(nom, prenom):
        if query("SELECT 1 FROM signatures WHERE nom=?", (name,)):
            return name
    return None


def load_bytes(nom, prenom=""):
    """Contenu de l'image (pour l'afficher ou l'insérer dans le PDF), ou None."""
    key = find(nom, prenom)
    if not key:
        return None
    if key not in _cache:
        r = query("SELECT data FROM signatures WHERE nom=?", (key,))
        _cache[key] = bytes(r[0]["data"]) if r and r[0]["data"] else None
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
    """Détoure l'image choisie et l'enregistre en base comme signature de l'enseignant. Retourne la clé."""
    from PIL import Image, ImageOps
    names = _names(nom, prenom)
    if not names:
        raise ValueError("Nom d'enseignant vide.")
    with Image.open(src) as im:
        out = process(ImageOps.exif_transpose(im))
    buf = io.BytesIO()
    out.save(buf, "PNG", optimize=True)
    remove(nom, prenom)                      # une seule signature par enseignant
    execute("INSERT INTO signatures(nom, data) VALUES(?,?) "
            "ON CONFLICT(nom) DO UPDATE SET data=excluded.data", (names[0], buf.getvalue()))
    _cache.clear()
    return names[0]


def remove(nom, prenom=""):
    """Supprime la signature de cet enseignant. Retourne True si une signature a été supprimée."""
    found = False
    for name in _names(nom, prenom):
        if query("SELECT 1 FROM signatures WHERE nom=?", (name,)):
            execute("DELETE FROM signatures WHERE nom=?", (name,))
            found = True
    _cache.clear()
    return found


def import_legacy_files():
    """Migration (une seule fois) : fichiers du dossier SIGNATURES_DIR -> base. Les fichiers ne sont pas supprimés."""
    if query("SELECT 1 FROM settings WHERE key='sig_migrated'"):
        return
    if os.path.isdir(SIGNATURES_DIR):
        for fn in sorted(os.listdir(SIGNATURES_DIR)):
            stem, ext = os.path.splitext(fn)
            path = os.path.join(SIGNATURES_DIR, fn)
            if ext.lower() in EXTS and os.path.isfile(path):
                with open(path, "rb") as f:
                    execute("INSERT OR IGNORE INTO signatures(nom, data) VALUES(?,?)", (stem.lower(), f.read()))
    set_setting("sig_migrated", "1")