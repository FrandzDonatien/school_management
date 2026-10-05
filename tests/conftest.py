import os
import sys
import tempfile

# Base temporaire AVANT tout import de l'application
_tmp = tempfile.mkdtemp(prefix="edumanager_test_")
os.environ["EDUMANAGER_DB"] = os.path.join(_tmp, "test.db")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def database():
    from app.database.migrations import init_db
    init_db()
    yield
