import base64
import glob
import hashlib
import mimetypes
import os

from app.calculations.schedule import build_plan
from app.config import DATA_DIR
from app.constants import PLAN, SLOTS
from app.database.connection import execute, query
from app.database.queries import cur_year
from app.utils.dates import current_school_year_label


def default_settings():
    return dict(ecole_nom="Mon Établissement", ministere="Ministère de l'Éducation Nationale",
                direction="Direction Régionale de l'Éducation", inspection="", devise="EXCELLENCE-SAGESSE",
                ville="Lomé", annee=current_school_year_label(), directeur="", logo="",
                matin_debut="07:00", matin_fin="12:00", apres_debut="15:00", apres_fin="17:00",
                pause_debut="09:45", pause_fin="10:10", duree_cours="55",
                heures_hebdo="21", heures_libres="2", mode_libres="Enchaînées")


def get_settings():
    d = default_settings()
    # Le logo (volumineux) est exclu : il se lit via logo_data_uri() / logo_path()
    for r in query("SELECT key,value FROM settings WHERE key NOT IN ('logo_data','logo_mime')"):
        d[r["key"]] = r["value"]
    y = query("SELECT libelle FROM years WHERE id=?", (cur_year(),))
    if y:
        d["annee"] = y[0]["libelle"]
    return d


def set_setting(k, v):
    execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (k, v))


def default_hours():
    """Volume hebdomadaire par défaut d'un enseignant (paramétrable)."""
    try:
        return max(1, int(get_settings()["heures_hebdo"]))
    except (ValueError, KeyError):
        return 21


def free_params():
    """(heures libres tolérées par semaine, mode « Enchaînées » / « Réparties »)."""
    S = get_settings()
    try:
        f = max(0, int(S["heures_libres"]))
    except ValueError:
        f = 2
    return f, S["mode_libres"]


# ---------- Logo stocké en base ----------
def _logo_row():
    d = {r["key"]: r["value"]
         for r in query("SELECT key,value FROM settings WHERE key IN ('logo_data','logo_mime')")}
    return (d.get("logo_data") or ""), (d.get("logo_mime") or "image/png")


def set_logo(path):
    """Enregistre le fichier image dans la base (base64)."""
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    set_setting("logo_data", b64)
    set_setting("logo_mime", mimetypes.guess_type(path)[0] or "image/png")


def clear_logo():
    execute("DELETE FROM settings WHERE key IN ('logo_data','logo_mime','logo')")


def has_logo():
    return bool(_logo_row()[0])


def logo_data_uri():
    b64, mime = _logo_row()
    return f"data:{mime};base64,{b64}" if b64 else ""


def logo_path():
    """Chemin d'un fichier temporaire reconstruit depuis la base (pour les composants qui exigent un fichier)."""
    b64, mime = _logo_row()
    if not b64:
        return None
    ext = mimetypes.guess_extension(mime) or ".png"
    cache_dir = os.path.join(DATA_DIR, "cache")
    os.makedirs(cache_dir, exist_ok=True)
    p = os.path.join(cache_dir, f"logo_{hashlib.sha1(b64.encode()).hexdigest()[:10]}{ext}")
    if not os.path.exists(p):
        for old in glob.glob(os.path.join(cache_dir, "logo_*")):
            try:
                os.remove(old)
            except OSError:
                pass
        with open(p, "wb") as f:
            f.write(base64.b64decode(b64))
    return p


def import_legacy_logo():
    """Migration : ancien logo stocké sous forme de chemin -> base."""
    if has_logo():
        return
    r = query("SELECT value FROM settings WHERE key='logo'")
    p = r[0]["value"] if r else ""
    if p and os.path.exists(p):
        set_logo(p)
    if r:
        set_setting("logo", "")


def load_plan():
    """Recalcule PLAN et SLOTS (listes partagées, modifiées en place)."""
    try:
        plan = build_plan(get_settings())
    except Exception:
        plan = build_plan(default_settings())
    PLAN[:] = plan
    SLOTS[:] = [(s, e) for k, _, s, e in plan if k == "slot"]