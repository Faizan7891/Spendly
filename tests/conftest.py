"""Shared pytest fixtures for Spendly tests.

Each test session runs against a throwaway SQLite database in a temp directory
so the developer's real spendly.db is never touched. The temp path is wired in
by overriding database.db.DB_PATH *before* app.py is imported, because app.py
calls init_db()/seed_db() at import time.
"""

import os
import sys
import tempfile

import pytest

# Make the project root importable (tests/ is one level down).
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


@pytest.fixture(scope="session")
def app():
    tmp_dir = tempfile.mkdtemp(prefix="spendly-test-")
    db_path = os.path.join(tmp_dir, "test.db")

    import database.db as db
    db.DB_PATH = db_path

    # Import app only after DB_PATH is patched so its import-time
    # init_db()/seed_db() populate the temp database.
    import app as app_module
    app_module.app.config.update(TESTING=True)

    with app_module.app.app_context():
        db.init_db()
        db.seed_db()

    yield app_module.app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def seed_user_id(app):
    """Return the id of the seeded demo user."""
    from database.db import get_db
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)
    ).fetchone()
    conn.close()
    return row["id"]


@pytest.fixture
def auth_client(client, seed_user_id):
    """A test client with the seed user logged in via session."""
    with client.session_transaction() as sess:
        sess["user_id"] = seed_user_id
        sess["user_name"] = "Demo User"
    return client
