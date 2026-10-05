"""Affectation des cours, préparation de la génération et lecture de l'emploi du temps."""
from collections import Counter

from app.calculations.schedule import TimetableSolver
from app.constants import DAYS, SLOTS
from app.database.queries import cur_year
from app.repositories import schedule_repository as repo
from app.repositories import teacher_repository
from app.services import settings_service
from app.services.teacher_service import teacher_target
from app.utils.formatting import abbr


class ScheduleError(Exception):
    """Problème bloquant (level='error') ou avertissement (level='warning') à afficher à l'utilisateur."""

    def __init__(self, title, message, level="error"):
        super().__init__(message)
        self.title, self.message, self.level = title, message, level


# -- affectation des cours
def assignment_totals(tid, data):
    """-> (objectif, total des heures saisies)."""
    return teacher_target(tid), sum(data.values())


def taken_assignments(tid, data):
    """Cours (avec heures) déjà attribués à un autre enseignant."""
    return [k for k, h in data.items() if h and repo.is_taken_by_other(k[0], k[1], tid)]


def save_assignment(tid, data):
    repo.save_assignments(cur_year(), tid, data)


# -- statut / charges
def status():
    y = cur_year()
    return repo.hours_needed(y), repo.placed_count(y)


def load_table():
    y = cur_year()
    rows = []
    for r in repo.load_rows(settings_service.default_hours(), y):
        need, tgt, placed = r["need"], r["target"], r["placed"]
        state = ("Sans cours" if not need else f"Incomplet (−{tgt - need} h)" if need < tgt
                 else f"Surcharge (+{need - tgt} h)" if need > tgt else "À générer" if placed == 0
                 else "Complet" if placed == need else "À régénérer")
        rows.append((r["id"], r["n"], r["subs"], tgt, need, placed, state))
    return rows


# -- lecture de l'emploi du temps
def cell_data(mode, ident):
    """{(jour, créneau): dict(subj, code, teacher, cls, key)} pour une classe ('c') ou un enseignant ('t')."""
    data = {}
    for r in repo.cells(mode, ident, cur_year()):
        name = r["sname"] or "Cours"
        data[(r["day"], r["slot"])] = dict(subj=name, code=r["scode"] or abbr(name), teacher=r["tname"] or "",
                                           cls=r["cname"], key=(r["sid"] or 0) if mode == "c" else r["cid"])
    return data


# -- génération
def prepare_generation(cids, cls_map):
    """Valide les données et prépare la génération. Lève ScheduleError si impossible."""
    y = cur_year()
    nd, ns = len(DAYS), len(SLOTS)
    names = {i: n for n, i in cls_map.items()}
    arows = repo.assignment_rows(y, cids)
    if not arows:
        raise ScheduleError("Aucune affectation", "Aucun cours n'est affecté.\nUtilisez d'abord le panneau "
                                                  "« 1. Affectation des cours ».", "warning")
    classes = {}
    for r in arows:
        classes.setdefault(r["class_id"], []).extend([(r["subject_id"], r["teacher_id"])] * r["hours"])
    for cid, lessons in classes.items():
        if len(lessons) > nd * ns:
            raise ScheduleError("Capacité dépassée", f"La classe « {names.get(cid, '')} » a {len(lessons)} "
                                                     f"h/semaine pour {nd * ns} créneaux.")
    fixed = repo.fixed_slots(y, cids) if len(cids) < len(cls_map) else []
    loads = Counter(t for lessons in classes.values() for _, t in lessons if t is not None)
    fixed_n = Counter(t for t, _, _ in fixed)
    tn = teacher_repository.names(y)
    for t, h in loads.items():
        if h + fixed_n[t] > nd * ns:
            raise ScheduleError("Charge trop élevée", f"{tn.get(t, 'Un enseignant')} a {h + fixed_n[t]} "
                                                      f"h/semaine pour {nd * ns} créneaux possibles.")
    tot = repo.teacher_totals(y)
    tgt = teacher_repository.targets(y, settings_service.default_hours())
    diff = [f"• {tn[t]} : {tot.get(t, 0)} h / {tgt[t]} h" for t in sorted(loads, key=lambda t: tn.get(t, ""))
            if t in tgt and tot.get(t, 0) != tgt[t]]
    return dict(classes=classes, fixed=fixed, diff=diff, existing=repo.count_in(y, cids))


def make_solver(prep):
    free, mode = settings_service.free_params()
    return TimetableSolver(prep["classes"], len(DAYS), len(SLOTS), prep["fixed"], free, mode)


def save_generated(grid, cids):
    """Remplace l'emploi du temps des classes cids par la grille générée. -> nombre de cours placés."""
    y = cur_year()
    rows = [(y, t, cid, subj, d, s) for cid, g in grid.items() for (d, s), (subj, t) in g.items()]
    repo.replace_schedule(y, cids, rows)
    return len(rows)


def clear(cids):
    repo.clear(cur_year(), cids)
