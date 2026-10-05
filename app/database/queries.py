"""Requêtes transverses : année active / année consultée."""
from app.database.connection import query

_view_year = None  # année consultée (None = année active)


def active_year():
    """Année active (seule modifiable)."""
    r = query("SELECT value FROM settings WHERE key='annee_id'")
    try:
        yid = int(r[0]["value"]) if r else None
    except ValueError:
        yid = None
    if yid and query("SELECT 1 FROM years WHERE id=?", (yid,)):
        return yid
    y = query("SELECT id FROM years ORDER BY libelle DESC LIMIT 1")
    return y[0]["id"] if y else None


def cur_year():
    """Année affichée dans toute l'application (active ou consultée)."""
    if _view_year and query("SELECT 1 FROM years WHERE id=?", (_view_year,)):
        return _view_year
    return active_year()


def set_view_year(y):
    global _view_year
    _view_year = y


def get_view_year():
    return _view_year


def is_read_only():
    """True si l'année affichée n'est pas l'année active."""
    return cur_year() != active_year()


def year_params():
    return (cur_year(),)


def year_extra():
    return {"annee_id": cur_year()}
