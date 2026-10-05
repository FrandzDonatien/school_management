def class_stats(res, effectif):
    avs = [r["moy"] for r in res.values() if r["moy"] is not None]
    return dict(effectif=effectif, max=max(avs) if avs else None, min=min(avs) if avs else None,
                avg=sum(avs) / len(avs) if avs else None)


def mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def seuil_decisions(moy):
    """Décisions du conseil des professeurs cochées selon la moyenne."""
    ok = lambda c: "☑" if c else "☐"
    m = moy if moy is not None else -1
    return dict(excellence=ok(m >= 16), honneur=ok(m >= 14), felicitations=ok(m >= 12),
                encouragements=ok(10 <= m < 12))
