import re


def parse_note(raw):
    """-> (valide, valeur). Une saisie vide est valide (valeur None)."""
    raw = raw.strip().replace(",", ".")
    if not raw:
        return True, None
    try:
        v = float(raw)
    except ValueError:
        return False, None
    return (0 <= v <= 20), v


def is_year_label(lab):
    return bool(re.fullmatch(r"\d{4}-\d{4}", lab))
