import base64
import mimetypes
import os

from app.calculations.schedule import build_plan
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
    for r in query("SELECT key,value FROM settings"):
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


def logo_path():
    p = get_settings()["logo"]
    return p if p and os.path.exists(p) else None


def logo_data_uri():
    p = logo_path()
    if not p:
        return ""
    mime = mimetypes.guess_type(p)[0] or "image/png"
    with open(p, "rb") as f:
        return f"data:{mime};base64,{base64.b64encode(f.read()).decode()}"


def load_plan():
    """Recalcule PLAN et SLOTS (listes partagées, modifiées en place)."""
    try:
        plan = build_plan(get_settings())
    except Exception:
        plan = build_plan(default_settings())
    PLAN[:] = plan
    SLOTS[:] = [(s, e) for k, _, s, e in plan if k == "slot"]
