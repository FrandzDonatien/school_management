from app.database.connection import query
from app.database.queries import active_year, cur_year
from app.services.auth_service import authenticate


def test_tables_created():
    names = {r["name"] for r in query("SELECT name FROM sqlite_master WHERE type='table'")}
    for t in ("users", "settings", "years", "students", "teachers", "subjects", "classes", "grades",
              "schedule", "assignments", "teacher_subjects", "discipline"):
        assert t in names


def test_default_admin_and_year():
    assert authenticate("admin", "admin123")
    assert not authenticate("admin", "mauvais")
    assert active_year() is not None and cur_year() == active_year()


def test_default_subjects_seeded():
    assert query("SELECT COUNT(*) FROM subjects")[0][0] >= 8
