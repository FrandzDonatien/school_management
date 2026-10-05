from app.calculations.schedule import TimetableSolver, build_plan, check_hours
from app.services.settings_service import default_settings


def test_default_plan_has_slots():
    plan = build_plan(default_settings())
    assert sum(1 for k, *_ in plan if k == "slot") >= 5
    assert check_hours(default_settings()) is None


def test_solver_no_conflict():
    # 2 classes partagent l'enseignant 1 : jamais au même créneau
    classes = {1: [(10, 1)] * 4 + [(11, 2)] * 4, 2: [(10, 1)] * 4 + [(12, 3)] * 4}
    solver = TimetableSolver(classes, 5, 6, [], 2, "Enchaînées", seed=1)
    grid, info = solver.solve(time_limit=10, polish=1)
    assert grid is not None and info["hard"] == 0
    seen = set()
    for g in grid.values():
        for (d, s), (_, t) in g.items():
            assert (t, d, s) not in seen
            seen.add((t, d, s))
