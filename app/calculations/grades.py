"""Calculs des notes (modèle togolais)
   Moy. classe           = moyenne (interrogation, devoir)
   Moy. générale matière = moyenne (Moy. classe, composition)
   Note définitive       = Moy. générale x coefficient
   Moyenne d'une catégorie = moyennes des matières pondérées par leur coefficient
"""


def calc_mg(interro, devoir, compo):
    cl = [x for x in (interro, devoir) if x is not None]
    mc = sum(cl) / len(cl) if cl else None
    p = [x for x in (mc, compo) if x is not None]
    return mc, (sum(p) / len(p) if p else None)


def _wavg(items, key):
    pairs = [(x[key], x["coef"]) for x in items if x[key] is not None]
    tw = sum(c for _, c in pairs)
    return sum(v * c for v, c in pairs) / tw if tw else None


def category_result(items):
    """Résultat d'une catégorie à partir des résultats de ses matières (None si aucune note)."""
    tc = sum(x["coef"] for x in items)
    if not items or not tc:
        return None
    tn = sum(x["nd"] for x in items)
    return dict(interro=_wavg(items, "interro"), devoir=_wavg(items, "devoir"), mc=_wavg(items, "mc"),
                compo=_wavg(items, "compo"), mg=tn / tc, coef=tc, nd=tn, rang=None)


def student_result(subjects, grades_by_subject):
    """Résultats d'un élève. subjects : lignes (id, coefficient, categorie_id) ; grades_by_subject : {subject_id: note}."""
    d, by_cat = {}, {}
    for sub in subjects:
        g = grades_by_subject.get(sub["id"])
        if not g:
            continue
        mc, mg = calc_mg(g["interro"], g["devoir"], g["compo"])
        if mg is None:
            continue
        d[sub["id"]] = dict(interro=g["interro"], devoir=g["devoir"], compo=g["compo"], mc=mc, mg=mg,
                            coef=sub["coefficient"], nd=mg * sub["coefficient"], rang=None)
        by_cat.setdefault(sub["categorie_id"], []).append(d[sub["id"]])
    cats = {}
    for cid, items in by_cat.items():
        r = category_result(items)
        if r:
            cats[cid] = r
    tc = sum(x["coef"] for x in d.values())
    tn = sum(x["nd"] for x in d.values())
    return dict(subjects=d, categories=cats, tc=tc, tn=tn, moy=(tn / tc if tc else None), rang=None)