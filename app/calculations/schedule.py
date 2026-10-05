"""Horaires de cours et moteur de génération de l'emploi du temps (recuit simulé)
   Contraintes dures : un enseignant n'est jamais dans deux classes au même créneau ;
                       une matière n'a pas plus de 2 heures par jour dans une classe.
   Contraintes souples : les cours de chaque classe occupent les créneaux consécutifs dès la 1re heure,
                       variété des créneaux de chaque enseignant (pas toujours la 1re heure),
                       heures libres (trous dans la journée) limitées, soit enchaînées (une plage de N h),
                       soit réparties (1 h sur plusieurs jours).
"""
import math
import random
import time
from collections import Counter, defaultdict

from app.constants import TIME_KEYS
from app.utils.dates import to_min, to_str


# ----------------------------------------------------------------------------
# Horaires
# ----------------------------------------------------------------------------
def build_plan(S):
    d = int(S["duree_cours"])
    ms, me, a_s, ae, ps, pe = (to_min(S[k]) for k in TIME_KEYS)
    plan = []

    def segment(a, b):
        t = a
        while t + d <= b:
            plan.append(("slot", None, to_str(t), to_str(t + d)))
            t += d

    def block(a, b):
        if a <= ps < pe <= b:
            segment(a, ps)
            plan.append(("break", "Récréation", to_str(ps), to_str(pe)))
            segment(pe, b)
        else:
            segment(a, b)

    block(ms, me)
    if a_s > me:
        plan.append(("break", "Pause déjeuner", to_str(me), to_str(a_s)))
    block(a_s, ae)
    return plan


def check_hours(v):
    t = {k: to_min(v[k]) for k in TIME_KEYS}
    if not (t["matin_debut"] < t["matin_fin"] <= t["apres_debut"] < t["apres_fin"]):
        return ("Les heures doivent respecter : début du matin < fin du matin ≤ reprise de l'après-midi "
                "< fin de l'après-midi.")
    if not t["pause_debut"] < t["pause_fin"]:
        return "La fin de la récréation doit être après son début."
    in_m = t["matin_debut"] <= t["pause_debut"] and t["pause_fin"] <= t["matin_fin"]
    in_a = t["apres_debut"] <= t["pause_debut"] and t["pause_fin"] <= t["apres_fin"]
    if not (in_m or in_a):
        return "La récréation doit se situer dans la matinée ou dans l'après-midi."
    if not 20 <= int(v["duree_cours"]) <= 180:
        return "La durée d'un cours doit être comprise entre 20 et 180 minutes."
    if not any(k == "slot" for k, *_ in build_plan(v)):
        return "Ces horaires ne permettent aucun cours."
    return None


# ----------------------------------------------------------------------------
# Solveur
# ----------------------------------------------------------------------------
DAY_PRIORITY = [0, 3, 2, 4, 1]


def day_counts(hours, nd, ns):
    order = [d for d in DAY_PRIORITY if d < nd] + [d for d in range(nd) if d not in DAY_PRIORITY]
    counts = [0] * nd
    left = hours
    while left > 0:
        moved = False
        for d in order:
            if left > 0 and counts[d] < ns:
                counts[d] += 1
                left -= 1
                moved = True
        if not moved:
            break
    return counts


class TimetableSolver:
    def __init__(self, classes, nd, ns, fixed=(), free=2, mode="Enchaînées", seed=None):
        self.nd, self.ns = nd, ns
        self.free, self.chain = free, mode.startswith("Ench")
        self.rnd = random.Random(seed)
        self.classes = classes
        self.cells, self.grid = {}, {}
        self.pres = defaultdict(lambda: [[0] * ns for _ in range(nd)])   # présence enseignant [jour][créneau]
        self.cdc = defaultdict(Counter)
        self.tsc = defaultdict(Counter)
        self.tcost = defaultdict(int)
        self.hard = self.soft = 0
        self.stop = False
        hrs = Counter()
        for lessons in classes.values():
            for _, t in lessons:
                if t is not None:
                    hrs[t] += 1
        for cid, lessons in classes.items():
            dc = day_counts(len(lessons), nd, ns)
            self.cells[cid] = [(d, s) for d in range(nd) for s in range(dc[d])]
            self.grid[cid] = {}
        eff = max([max(day_counts(len(l), nd, ns)) for l in classes.values()] or [1]) or 1
        self.lim = defaultdict(lambda: 99, {t: math.ceil(h / eff) for t, h in hrs.items()})
        for t, d, s in fixed:
            self.pres[t][d][s] += 1
            self.tsc[t][s] += 1
        for t in {f[0] for f in fixed}:
            self.tcost[t] = self._tcost(t)
            self.soft += self.tcost[t]

    def _tcost(self, t):
        """Coût des heures libres (trous entre le 1er et le dernier cours de la journée)."""
        p = self.pres[t]
        total = cost = 0
        for d in range(self.nd):
            row = p[d]
            idx = [s for s in range(self.ns) if row[s] > 0]
            if len(idx) < 2:
                continue
            runs, run = [], 0
            for s in range(idx[0], idx[-1] + 1):
                if row[s] > 0:
                    if run:
                        runs.append(run)
                    run = 0
                else:
                    run += 1
            for r in runs:
                total += r
                if self.chain:
                    if r != self.free:
                        cost += r
                elif r > 1:
                    cost += (r - 1) * 2
        return cost + max(0, total - self.free) * 3

    @staticmethod
    def _nb(g, d, s, subj):
        n = 0
        for x in (s - 1, s + 1):
            o = g.get((d, x))
            if o and o[0] == subj:
                n += 1
        return n

    def _add(self, c, d, s, les):
        subj, tid = les
        h = sf = dc = 0
        if tid is not None:
            p = self.pres[tid]
            if p[d][s] >= 1:
                h += 1
            p[d][s] += 1
            t = self.tsc[tid]
            if t[s] >= self.lim[tid]:
                sf += 1
            t[s] += 1
            new = self._tcost(tid)
            dc = new - self.tcost[tid]
            self.tcost[tid] = new
        k = self.cdc[(c, d)]
        n = k[subj]
        if n >= 2:
            h += 1
        elif n == 1:
            sf += 2
        k[subj] = n + 1
        g = self.grid[c]
        sf += self._nb(g, d, s, subj)
        g[(d, s)] = les
        self.hard += h
        self.soft += sf + dc

    def _rem(self, c, d, s):
        g = self.grid[c]
        les = g.pop((d, s))
        subj, tid = les
        h = sf = dc = 0
        if tid is not None:
            p = self.pres[tid]
            p[d][s] -= 1
            if p[d][s] >= 1:
                h += 1
            t = self.tsc[tid]
            t[s] -= 1
            if t[s] >= self.lim[tid]:
                sf += 1
            new = self._tcost(tid)
            dc = new - self.tcost[tid]
            self.tcost[tid] = new
        k = self.cdc[(c, d)]
        k[subj] -= 1
        n = k[subj]
        if n >= 2:
            h += 1
        elif n == 1:
            sf += 2
        sf += self._nb(g, d, s, subj)
        self.hard -= h
        self.soft += dc - sf
        return les

    def _bad(self, c, d, s):
        subj, tid = self.grid[c][(d, s)]
        if tid is not None and self.pres[tid][d][s] > 1:
            return True
        return self.cdc[(c, d)][subj] > 2

    def solve(self, time_limit=30.0, polish=6.0, progress=None):
        rnd = self.rnd
        for cid, lessons in self.classes.items():
            ls = list(lessons)
            rnd.shuffle(ls)
            for (d, s), les in zip(self.cells[cid], ls):
                self._add(cid, d, s, les)
        cids = [c for c in self.cells if len(self.cells[c]) > 1]
        if not cids:
            ok = self.hard == 0
            return ({c: dict(g) for c, g in self.grid.items()} if ok else None), dict(hard=self.hard, soft=self.soft)
        weights = [len(self.cells[c]) for c in cids]
        total = lambda: self.hard * 10 + self.soft
        T, t0 = 3.0, time.time()
        best, best_soft, first_ok = None, None, None
        best_hard = self.hard
        steps = 0
        while time.time() - t0 < time_limit and not self.stop:
            for _ in range(400):
                c = rnd.choices(cids, weights)[0]
                cells = self.cells[c]
                a = None
                for _try in range(4):
                    a = cells[rnd.randrange(len(cells))]
                    if self._bad(c, *a):
                        break
                b = cells[rnd.randrange(len(cells))]
                la, lb = self.grid[c][a], self.grid[c][b]
                if a == b or la[0] == lb[0]:
                    continue
                before = total()
                self._rem(c, *a)
                self._rem(c, *b)
                self._add(c, *a, lb)
                self._add(c, *b, la)
                delta = total() - before
                if delta > 0 and rnd.random() >= math.exp(-delta / T):
                    self._rem(c, *a)
                    self._rem(c, *b)
                    self._add(c, *a, la)
                    self._add(c, *b, lb)
                steps += 1
                if self.hard < best_hard:
                    best_hard = self.hard
                if self.hard == 0 and (best_soft is None or self.soft < best_soft):
                    best_soft = self.soft
                    best = {c2: dict(g) for c2, g in self.grid.items()}
                    if first_ok is None:
                        first_ok = time.time()
            T = max(0.2, T * 0.985)
            if first_ok is None and T <= 0.2 and rnd.random() < 0.02:
                T = 2.0  # réchauffage
            if first_ok is not None and (time.time() - first_ok > polish or best_soft == 0):
                break
            if progress:
                progress(best_hard, steps)
        return best, dict(hard=best_hard, soft=best_soft, steps=steps, secs=time.time() - t0)
