def rank_subjects(res, subjects):
    """Rang de chaque élève dans chaque matière (rang = 1 + nombre d'élèves strictement meilleurs)."""
    for sub in subjects:
        vals = [(sid, r["subjects"][sub["id"]]["mg"]) for sid, r in res.items() if sub["id"] in r["subjects"]]
        for sid, mg in vals:
            res[sid]["subjects"][sub["id"]]["rang"] = 1 + sum(1 for _, o in vals if o > mg)


def rank_categories(res):
    """Rang de chaque élève dans chaque catégorie (d'après la moyenne de la catégorie)."""
    for cid in {c for r in res.values() for c in r["categories"]}:
        vals = [(sid, r["categories"][cid]["mg"]) for sid, r in res.items() if cid in r["categories"]]
        for sid, mg in vals:
            res[sid]["categories"][cid]["rang"] = 1 + sum(1 for _, o in vals if o > mg)


def rank_students(res):
    avs = [r["moy"] for r in res.values() if r["moy"] is not None]
    for r in res.values():
        if r["moy"] is not None:
            r["rang"] = 1 + sum(1 for o in avs if o > r["moy"])