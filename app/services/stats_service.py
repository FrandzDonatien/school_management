"""Statistiques des notes : mêmes calculs que les bulletins (compute_class / compute_recap).
Période = un trimestre, ou « Annuel » (moyennes annuelles issues de compute_recap)."""
from collections import Counter

from app.constants import PERIODES
from app.database.connection import query
from app.repositories import schedule_repository, student_repository
from app.services import grade_service
from app.utils.formatting import fmt, person

ANNUEL = "Annuel"
SEUIL = 10  # moyenne minimale pour être « admis »
SEXES = {"M": "M", "G": "M", "H": "M", "F": "F"}

# --- en-têtes partagés entre l'UI et l'Excel
H_MAT = ["Matière", "Élèves", "Moyenne", "Moy. classe max", "Moy. classe min", "Note max", "Note min",
         "[0-6[", "[6-10[", "[10-15[", "[15-20]"]
H_MAT_SEXE = ["Matière", "Garçons Eff.", "Garçons Moy.", "Filles Eff.", "Filles Moy."]
H_SEXE = ["Sexe", "Effectif", "Admis", "Échecs", "Réussite %", "Moyenne", "Min", "Max"]
H_PROF = ["Professeur", "Matières", "Classes", "Élèves", "Moyenne", "Note min", "Note max", "Réussite %"]
H_CLASSES = ["Classe"] + [f"{p} {x}" for p in ("G", "F", "T") for x in ("Eff.", "Adm.", "%")]


def _n_prev(per):
    """Nombre de colonnes « Moy. Tn » avant la moyenne finale."""
    if per == ANNUEL:
        return len(PERIODES)
    return PERIODES.index(per) if per in PERIODES else 0


def rank_headers(per):
    """Classement : une colonne par trimestre précédent (tous en mode annuel), puis la moyenne finale."""
    return (["Classe", "Rang", "Matricule", "Nom", "Prénoms", "Sexe"]
            + [f"Moy. T{i + 1}" for i in range(_n_prev(per))]
            + ["Moy. Ann." if per == ANNUEL else "Moyenne", "Décision"])


# ---------------------------------------------------------------- données
def _g(o, key, default=""):
    """Lecture tolérante : dict, sqlite3.Row ou objet."""
    try:
        v = o[key]
    except Exception:
        v = getattr(o, key, default)
    return default if v is None else v


def fetch_grades(year, periode, class_id=None):
    """Une ligne par (élève, matière), calculée comme le bulletin.
    periode = un trimestre ou ANNUEL. Chaque ligne porte aussi la moyenne/rang officiels de l'élève."""
    annual_mode = periode == ANNUEL
    target = PERIODES[-1] if annual_mode else periode
    studs, teachers, out = {}, {}, []
    for c in query("SELECT id, nom FROM classes WHERE annee_id=? ORDER BY nom", (year,)):
        if class_id and c["id"] != class_id:
            continue
        res, subs, _ = grade_service.compute_class(c["id"], target)
        prev, annual = grade_service.compute_recap(c["id"], target, current=res)
        names = {s["id"]: s["nom"] for s in subs}
        for sid, r in res.items():
            if annual_mode:
                a = (annual or {}).get(sid)
                if not a:
                    continue
                moy, rang, subj = a["moy"], a["rang"], a["subjects"]
            else:
                moy, rang = r["moy"], r["rang"]
                subj = {k: v["mg"] for k, v in r["subjects"].items()}
            if moy is None:
                continue
            if sid not in studs:
                studs[sid] = student_repository.get(sid)
            stu = studs[sid]
            tris = [pres.get(sid, {}).get("moy") for _, pres in prev] + [r["moy"]]
            ident = dict(eid=sid, cid=c["id"], classe=c["nom"],
                         matricule=_g(stu, "matricule"), nom=str(_g(stu, "nom")).upper(),
                         prenom=_g(stu, "prenom"), sexe=_g(stu, "sexe", _g(stu, "genre", "")),
                         moy=moy, rang=rang, tris=tris)
            for mid, note in subj.items():
                if note is None or mid not in names:
                    continue
                key = (c["id"], mid)
                if key not in teachers:
                    t = schedule_repository.teacher_of(c["id"], mid)
                    teachers[key] = person(t["nom"], t["prenom"]) if t else ""
                out.append(dict(ident, mid=mid, matiere=names[mid], note=float(note), prof=teachers[key]))
    return out


# ---------------------------------------------------------------- calculs
def _pct(part, total):
    return round(100 * part / total, 1) if total else 0.0


def _bande(n):
    return 0 if n < 6 else 1 if n < 10 else 2 if n < 15 else 3


def _sexe(v):
    return SEXES.get((v or "").strip().upper()[:1], "?")


def _stats(v):
    """(moyenne, min, max) arrondis."""
    if not v:
        return 0.0, 0.0, 0.0
    return round(sum(v) / len(v), 2), round(min(v), 2), round(max(v), 2)


def _add(d, s):
    for k in ["T"] + ([s["sexe"]] if s["sexe"] in ("M", "F") else []):
        d[k][0] += 1
        d[k][1] += int(s["avg"] >= SEUIL)


def _fmt(d, name):
    return {"classe": name, **{k: (v[0], v[1], _pct(v[1], v[0])) for k, v in d.items()}}


def compute(rows, per=None):
    # ----- par matière (+ par sexe)
    mat = {}
    for r in rows:
        m = mat.setdefault(r["mid"], {"matiere": r["matiere"], "notes": [], "cls": {}, "sx": {"M": [], "F": []}})
        m["notes"].append(r["note"])
        m["cls"].setdefault(r["classe"], []).append(r["note"])
        sx = _sexe(r["sexe"])
        if sx in m["sx"]:
            m["sx"][sx].append(r["note"])
    matieres, matieres_sexe = [], []
    for m in sorted(mat.values(), key=lambda x: x["matiere"]):
        moy, mn, mx = _stats(m["notes"])
        cls_avg = [sum(v) / len(v) for v in m["cls"].values()]
        bandes = [0] * 4
        for v in m["notes"]:
            bandes[_bande(v)] += 1
        matieres.append({"matiere": m["matiere"], "effectif": len(m["notes"]), "moyenne": moy,
                         "moy_max": round(max(cls_avg), 2), "moy_min": round(min(cls_avg), 2),
                         "max": mx, "min": mn, "bandes": bandes})
        g, f = m["sx"]["M"], m["sx"]["F"]
        matieres_sexe.append({"matiere": m["matiere"], "M": (len(g), _stats(g)[0]), "F": (len(f), _stats(f)[0])})

    # ----- élèves : moyenne et rang OFFICIELS (ceux du bulletin)
    students = {}
    for r in rows:
        if r["eid"] not in students:
            students[r["eid"]] = {"classe": r["classe"], "matricule": r["matricule"], "nom": r["nom"],
                                  "prenom": r["prenom"], "sexe": _sexe(r["sexe"]), "avg": round(r["moy"], 2),
                                  "rang": r["rang"], "tris": r["tris"]}

    # ----- résultats par sexe
    sexes = []
    for k, lab in (("M", "Garçons"), ("F", "Filles"), ("T", "Ensemble")):
        lst = [s["avg"] for s in students.values() if k == "T" or s["sexe"] == k]
        if not lst:
            continue
        adm = sum(a >= SEUIL for a in lst)
        moy, mn, mx = _stats(lst)
        sexes.append({"label": lab, "effectif": len(lst), "admis": adm, "echecs": len(lst) - adm,
                      "taux": _pct(adm, len(lst)), "moyenne": moy, "min": mn, "max": mx})

    # ----- par professeur
    profs = {}
    for r in rows:
        if not r["prof"]:
            continue
        d = profs.setdefault(r["prof"], {"notes": [], "mat": set(), "cls": set(), "eleves": set()})
        d["notes"].append(r["note"])
        d["mat"].add(r["matiere"])
        d["cls"].add(r["classe"])
        d["eleves"].add(r["eid"])
    professeurs = []
    for p in sorted(profs):
        d = profs[p]
        moy, mn, mx = _stats(d["notes"])
        professeurs.append({"prof": p, "matieres": ", ".join(sorted(d["mat"])),
                            "classes": ", ".join(sorted(d["cls"])), "eleves": len(d["eleves"]),
                            "moyenne": moy, "min": mn, "max": mx,
                            "taux": _pct(sum(n >= SEUIL for n in d["notes"]), len(d["notes"]))})

    # ----- réussite par classe et par sexe
    cls, tot = {}, {"M": [0, 0], "F": [0, 0], "T": [0, 0]}
    for s in students.values():
        _add(cls.setdefault(s["classe"], {"M": [0, 0], "F": [0, 0], "T": [0, 0]}), s)
        _add(tot, s)
    classes = [_fmt(cls[k], k) for k in sorted(cls)]
    total = _fmt(tot, "Ensemble")

    # ----- classement par classe : rang du bulletin, « ex » si plusieurs élèves ont le même rang
    ties = Counter((s["classe"], s["rang"]) for s in students.values() if s["rang"])
    ranking = []
    for s in sorted(students.values(), key=lambda s: (s["classe"], s["rang"] or 9999, s["nom"], s["prenom"])):
        rang = ""
        if s["rang"]:
            rang = f"{s['rang']} ex" if ties[(s["classe"], s["rang"])] > 1 else str(s["rang"])
        ranking.append({"classe": s["classe"], "rang": rang, "matricule": s["matricule"], "nom": s["nom"],
                        "prenom": s["prenom"], "sexe": s["sexe"] if s["sexe"] != "?" else "",
                        "moyenne": s["avg"], "tris": s["tris"],
                        "decision": "Admis" if s["avg"] >= SEUIL else "Échec"})

    # ----- synthèse
    n = len(students)
    admis = sum(1 for s in students.values() if s["avg"] >= SEUIL)
    avgs = [s["avg"] for s in students.values()]

    def taux(lab):
        return next((x["taux"] for x in sexes if x["label"] == lab), 0.0)

    summary = {"eleves": n, "admis": admis, "echecs": n - admis, "reussite": _pct(admis, n),
               "moyenne": round(sum(avgs) / n, 2) if n else 0.0,
               "max": max(avgs) if avgs else 0.0, "min": min(avgs) if avgs else 0.0,
               "taux_M": taux("Garçons"), "taux_F": taux("Filles")}
    return {"per": per, "summary": summary, "matieres": matieres, "matieres_sexe": matieres_sexe,
            "sexes": sexes, "professeurs": professeurs, "classes": classes, "total": total,
            "ranking": ranking}


# ---------------------------------------------------------------- lignes de tableaux (UI + Excel)
def rows_matieres(d):
    return [(x["matiere"], x["effectif"], x["moyenne"], x["moy_max"], x["moy_min"], x["max"], x["min"],
             *x["bandes"]) for x in d["matieres"]]


def rows_matieres_sexe(d):
    return [(x["matiere"], *x["M"], *x["F"]) for x in d["matieres_sexe"]]


def rows_sexes(d):
    return [(x["label"], x["effectif"], x["admis"], x["echecs"], x["taux"], x["moyenne"], x["min"], x["max"])
            for x in d["sexes"]]


def rows_profs(d):
    return [(x["prof"], x["matieres"], x["classes"], x["eleves"], x["moyenne"], x["min"], x["max"], x["taux"])
            for x in d["professeurs"]]


def rows_classes(d):
    rows = [(x["classe"], *x["M"], *x["F"], *x["T"]) for x in d["classes"]]
    if d["classes"]:
        t = d["total"]
        rows.append((t["classe"], *t["M"], *t["F"], *t["T"]))
    return rows


def rows_ranking(d):
    """Même présentation que le bulletin : moyennes des trimestres précédents, puis moyenne finale
    (en mode annuel : T1, T2, T3 puis « Moy. Ann. »)."""
    per = d["per"]
    n = _n_prev(per)
    out = []
    for x in d["ranking"]:
        tris = x["tris"] if per == ANNUEL else x["tris"][:-1]
        tri = [fmt(m) for m in tris][:n]
        tri += [""] * (n - len(tri))
        out.append((x["classe"], x["rang"], x["matricule"], x["nom"], x["prenom"], x["sexe"],
                    *tri, x["moyenne"], x["decision"]))
    return out


# ---------------------------------------------------------------- export Excel
def export_excel(data, path, titre):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    fill = PatternFill("solid", fgColor="3C50E0")
    white = Font(bold=True, color="FFFFFF")
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin = Side(style="thin", color="D0D7E2")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    def sheet(name, header, rows, first=False):
        ws = wb.active if first else wb.create_sheet()
        ws.title = name
        ws.append(header)
        for r in rows:
            ws.append(list(r))
        for row in ws.iter_rows():
            for c in row:
                c.border = border
                if c.row == 1:
                    c.font, c.fill, c.alignment = white, fill, center
        for idx, col in enumerate(ws.iter_cols(), 1):
            w = max((len(str(c.value)) for c in col if c.value is not None), default=8)
            ws.column_dimensions[get_column_letter(idx)].width = min(max(w + 3, 9), 45)

    s = data["summary"]
    sheet("Synthèse", ["Indicateur", "Valeur"], [
        ["Filtre", titre], ["Élèves évalués", s["eleves"]], ["Admis (moy. ≥ 10)", s["admis"]],
        ["Échecs", s["echecs"]], ["Taux de réussite (%)", s["reussite"]], ["Moyenne générale", s["moyenne"]],
        ["Meilleure moyenne", s["max"]], ["Plus faible moyenne", s["min"]],
        ["Réussite garçons (%)", s["taux_M"]], ["Réussite filles (%)", s["taux_F"]]], first=True)
    sheet("Par matière", H_MAT, rows_matieres(data))
    sheet("Matière x sexe", H_MAT_SEXE, rows_matieres_sexe(data))
    sheet("Par sexe", H_SEXE, rows_sexes(data))
    sheet("Par professeur", H_PROF, rows_profs(data))
    sheet("Classe x sexe", H_CLASSES, rows_classes(data))
    sheet("Classement", rank_headers(data["per"]), rows_ranking(data))
    wb.save(path)