"""Bulletins de notes : préparation des données et génération du PDF imprimable."""
import base64
import datetime

from app.calculations.statistics import seuil_decisions
from app.constants import PERIODES
from app.database.connection import query
from app.repositories import class_repository, grade_repository, schedule_repository, student_repository
from app.reports.bulletin import write_pdf
from app.services.grade_service import compute_class
from app.services.settings_service import get_settings, logo_data_uri
from app.utils.files import open_file, pdf_path
from app.utils.formatting import fmt, mention, rang_fr

# --- Réglages du bulletin -------------------------------------------------------------------
REPUBLIQUE = "République Togolaise"
DEVISE = "Travail - Liberté - Patrie"

# Distinctions : (libellé affiché, clé renvoyée par seuil_decisions). Les seuils restent ceux de
# app/calculations/statistics.py : rien à régler ici.
DISTINCTIONS = [("Tableau d'Excellence", "excellence"), ("Tableau d'Honneur", "honneur"),
                ("Félicitations", "felicitations"), ("Encouragements", "encouragements")]
_UNCHECKED = {"", "non", "no", "-", "—", "–", "false", "0", "☐", "✗", "✘"}

# Une ligne « Moyenne <catégorie> » n'est affichée que si la catégorie compte au moins ce nombre de matières
MIN_SUBJECTS_FOR_AVERAGE = 2
# ----------------------------------------------------------------------------------------------


def _g(o, key, default=""):
    """Lecture tolérante : dict, sqlite3.Row ou objet."""
    try:
        v = o[key]
    except Exception:
        v = getattr(o, key, default)
    return default if v is None else v


def _first(o, *keys):
    for k in keys:
        v = _g(o, k, "")
        if v not in ("", None):
            return str(v)
    return ""


def _short(s, maxlen=18):
    """Nom affiché sur le bulletin : l'abréviation de la matière si le nom est trop long pour la cellule."""
    nom = s["nom"]
    return nom if len(nom) <= maxlen else (_g(s, "code", "") or nom)


def _rang(r):
    return rang_fr(r) if r else ""


def _checked(v):
    """Interprète la valeur renvoyée par seuil_decisions (booléen, « Oui »/« Non », case cochée…)."""
    if isinstance(v, str):
        return v.strip().lower() not in _UNCHECKED
    return bool(v)


def _min_max_avg(values):
    vs = [v for v in values if v is not None]
    return (min(vs), max(vs), sum(vs) / len(vs)) if vs else (None, None, None)


def teacher_name(cid, subject_id):
    return schedule_repository.teacher_name(cid, subject_id)


def titulaire_name(cl):
    r = query("SELECT TRIM(nom||' '||prenom) AS n FROM teachers WHERE id=?", (_g(cl, "titulaire_id", None),))
    return r[0]["n"] if r else (_g(cl, "prof_titulaire", "") or "")


def _logo_bytes():
    try:
        uri = logo_data_uri()
        return base64.b64decode(uri.split(",", 1)[1]) if uri else None
    except Exception:
        return None


def _periods_block(cid, per, sid, cache):
    idx = PERIODES.index(per) if per in PERIODES else len(PERIODES) - 1
    out = []
    for p in reversed(PERIODES[:idx + 1]):
        if p not in cache:
            try:
                cache[p] = compute_class(cid, p)
            except Exception:
                continue
        res_p, _, stats_p = cache[p]
        mine = res_p.get(sid)
        if not mine or mine["moy"] is None:
            continue
        eff = _g(stats_p, "effectif", len(res_p))
        out.append(dict(label=p, moy=fmt(mine["moy"]),
                        rang=f"{_rang(mine['rang'])} sur {eff}" if mine["rang"] else "",
                        max=fmt(_g(stats_p, "max", None)), min=fmt(_g(stats_p, "min", None)),
                        avg=fmt(_g(stats_p, "avg", None))))
    if not out:
        out.append(dict(label=per, moy="", rang="", max="", min="", avg=""))
    return out


def build_bulletins(ids, cid, per):
    S = get_settings()
    res, subs, stats = compute_class(cid, per)
    cl = class_repository.get(cid)
    teachers = {s["id"]: teacher_name(cid, s["id"]) for s in subs}
    titulaire = titulaire_name(cl)
    logo = _logo_bytes()
    cache = {per: (res, subs, stats)}
    today = datetime.date.today().strftime("%d/%m/%Y")
    effectif = _g(stats, "effectif", len(res))

    # Regroupement des matières par catégorie (catégories paramétrées dans la page « Matières »).
    # Les matières arrivent déjà triées par ordre de catégorie ; sans catégorie = en dernier.
    by_cat = {}
    for s in subs:
        by_cat.setdefault(s["categorie_id"], []).append(s)
    categorized = any(k is not None for k in by_cat)

    # Statistiques de classe par matière et par catégorie
    sub_stats = {}
    for s in subs:
        vals = [r["subjects"][s["id"]].get("mg") for r in res.values() if r["subjects"].get(s["id"])]
        sub_stats[s["id"]] = _min_max_avg(vals)
    cat_stats = {k: _min_max_avg([r["categories"][k]["mg"] for r in res.values() if k in r.get("categories", {})])
                 for k in by_cat if k is not None}

    header = dict(republique=REPUBLIQUE, devise=DEVISE, ministere=_first(S, "ministere"),
                  direction=_first(S, "direction"), inspection=_first(S, "inspection"),
                  ecole=_first(S, "ecole_nom"), logo=logo)
    chef = _first(S, "directeur")

    bulletins = []
    for sid in ids:
        stu = student_repository.get(sid)
        r = res.get(sid, dict(subjects={}, categories={}, moy=None, rang=None))
        d = grade_repository.get_discipline(sid, per)
        sexe = _first(stu, "sexe", "genre").upper()[:1]
        moy = r["moy"]

        groups = []
        for key, gsubs in by_cat.items():
            first = gsubs[0]
            title = None
            if categorized:
                title = ((first["categorie_titre"] or f"Matières {first['categorie']}").upper()
                         if key is not None else "AUTRES MATIÈRES")
            rows = []
            for s in gsubs:
                x = r["subjects"].get(s["id"])
                mn, mx, av = sub_stats[s["id"]]
                v = dict(name=_short(s), teacher=teachers.get(s["id"], "") or "",
                         coef=f"{(x['coef'] if x else _g(s, 'coefficient', 0)):g}",
                         min=fmt(mn), max=fmt(mx), moy=fmt(av))
                if x:
                    v.update(interro=fmt(x.get("interro")), devoir=fmt(x.get("devoir")), compo=fmt(x.get("compo")),
                             mg=fmt(x.get("mg")), nd=fmt(x.get("nd")), rang=_rang(x.get("rang")),
                             appr=mention(x.get("mg")) or "")
                rows.append(v)
            avg = None
            cat = r.get("categories", {}).get(key) if key is not None else None
            if cat and len(gsubs) >= MIN_SUBJECTS_FOR_AVERAGE:
                mn, mx, av = cat_stats[key]
                avg = dict(label=f"Moyenne {first['categorie']}", interro=fmt(cat["interro"]),
                           devoir=fmt(cat["devoir"]), compo=fmt(cat["compo"]), mg=fmt(cat["mg"]),
                           coef=f"{cat['coef']:g}", nd=fmt(cat["nd"]), rang=_rang(cat["rang"]),
                           min=fmt(mn), max=fmt(mx), moy=fmt(av), appr=mention(cat["mg"]) or "")
            groups.append(dict(title=title, rows=rows, avg=avg))

        dc = seuil_decisions(moy)
        bulletins.append(dict(
            header=header,
            student=dict(nom=f"{_g(stu, 'nom').upper()} {_g(stu, 'prenom')}".strip(),
                         sexe={"M": "Masculin", "F": "Féminin"}.get(sexe, ""),
                         classe=str(_g(cl, "nom")).upper(), annee=_first(S, "annee"),
                         statut=_first(stu, "statut"), effectif=effectif, periode=per),
            groups=groups,
            periods=_periods_block(cid, per, sid, cache),
            distinctions=[(lab, _checked(_g(dc, key, ""))) for lab, key in DISTINCTIONS],
            discipline=[("Nbre d'heures d'absence :", str(_g(d, "absences", "")) if d else ""),
                        ("Sanctions :", str(_g(d, "sanctions", "")) if d else ""),
                        ("Mérites :", str(_g(d, "merites", "")) if d else ""),
                        ("Exclusions :", str(_g(d, "exclusions", "")) if d else "")],
            decision=mention(moy) or "", titulaire=titulaire, chef=chef, date=today))
    return bulletins


def generate(ids, cid, per, name):
    """Construit le bulletin au format PDF, l'enregistre dans exports/bulletins et l'ouvre pour l'impression."""
    bulletins = build_bulletins(ids, cid, per)
    path = pdf_path(name)
    try:
        write_pdf(path, bulletins, title=name)
    except PermissionError:  # fichier déjà ouvert dans un lecteur PDF
        path = pdf_path(name + datetime.datetime.now().strftime("_%H%M%S"))
        write_pdf(path, bulletins, title=name)
    open_file(path)
    return path