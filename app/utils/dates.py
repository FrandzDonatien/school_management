import datetime
import re

from app.constants import JOURS_FR, MOIS_FR


def parse_time(s):
    """'7h', '07h30', '7:30', '07:00' -> 'HH:MM' (ou None)."""
    m = re.fullmatch(r"(\d{1,2})\s*[h:]\s*(\d{0,2})", s.strip().lower())
    if not m:
        return None
    hh, mm = int(m.group(1)), int(m.group(2) or 0)
    return f"{hh:02d}:{mm:02d}" if hh < 24 and mm < 60 else None


def to_min(t):
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def to_str(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def date_fr():
    d = datetime.date.today()
    return f"{JOURS_FR[d.weekday()].capitalize()} {d.day} {MOIS_FR[d.month - 1]} {d.year}"


def current_school_year_label():
    t = datetime.date.today()
    a = t.year if t.month >= 9 else t.year - 1
    return f"{a}-{a + 1}"
