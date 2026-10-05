import datetime
import re
import unicodedata


def person(nom, prenom):
    return f"{nom or ''} {prenom or ''}".strip()


def abbr(name):
    return re.sub(r"[^A-Za-zÀ-ÿ]", "", name or "").upper()[:4]


def fmt(x):
    return "" if x is None else f"{x:.2f}"


def num(v):
    return f"{round(v, 2):g}"


def mention(m):
    if m is None:
        return ""
    return ("Excellent" if m >= 16 else "Très bien" if m >= 14 else "Bien" if m >= 12
            else "Assez bien" if m >= 10 else "Insuffisant")


def rang_fr(n):
    return f"{n}{'er' if n == 1 else 'e'}"


def ordinal(i):
    return f"{i + 1}{'er' if i == 0 else 'e'} H"


def trunc(text, n):
    text = str(text)
    return text if len(text) <= n else text[:max(1, n - 1)] + "…"


def new_matricule(sid):
    return f"EL{datetime.date.today().year}{sid:04d}"


def norm(s):
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())
