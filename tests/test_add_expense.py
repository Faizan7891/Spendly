"""Tests for Step 7: Add Expense.

Expected behaviour is derived from .claude/specs/07-add-expense.md.
The session-scoped test DB is seeded by database/db.py::seed_db().
"""

from database.db import get_db
from database.queries import insert_expense


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def _count_expenses(user_id):
    conn = get_db()
    n = conn.execute(
        "SELECT COUNT(*) FROM expenses WHERE user_id = ?", (user_id,)
    ).fetchone()[0]
    conn.close()
    return n


# ================================================================== #
# Unit tests — insert_expense                                         #
# ================================================================== #

def test_insert_expense_inserts_row(seed_user_id):
    new_id = insert_expense(seed_user_id, 50.0, "Food", "2026-03-20", "Lunch")
    conn = get_db()
    row = conn.execute("SELECT * FROM expenses WHERE id = ?", (new_id,)).fetchone()
    conn.close()
    assert row is not None
    assert row["amount"] == 50.0
    assert row["category"] == "Food"
    assert row["date"] == "2026-03-20"
    assert row["description"] == "Lunch"


def test_insert_expense_none_description(seed_user_id):
    new_id = insert_expense(seed_user_id, 12.0, "Other", "2026-03-21", None)
    conn = get_db()
    row = conn.execute(
        "SELECT description FROM expenses WHERE id = ?", (new_id,)
    ).fetchone()
    conn.close()
    assert row["description"] is None


# ================================================================== #
# Route tests — GET                                                   #
# ================================================================== #

def test_get_add_unauthenticated_redirects(client):
    resp = client.get("/expenses/add", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_get_add_authenticated_shows_form(auth_client):
    resp = auth_client.get("/expenses/add")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "<form" in body
    assert 'method="POST"' in body
    for cat in ["Food", "Transport", "Bills", "Health",
                "Entertainment", "Shopping", "Other"]:
        assert cat in body
    assert "<select" in body


# ================================================================== #
# Route tests — POST                                                  #
# ================================================================== #

def test_post_add_unauthenticated_redirects(client):
    resp = client.post("/expenses/add", data={
        "amount": "50.0", "category": "Food", "date": "2026-03-20",
        "description": "Lunch"
    }, follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_post_add_valid_redirects_and_inserts(auth_client, seed_user_id):
    before = _count_expenses(seed_user_id)
    resp = auth_client.post("/expenses/add", data={
        "amount": "50.0", "category": "Food", "date": "2026-03-20",
        "description": "Lunch"
    }, follow_redirects=False)
    assert resp.status_code == 302
    assert "/profile" in resp.headers["Location"]
    assert _count_expenses(seed_user_id) == before + 1


def test_post_add_missing_amount_rerenders(auth_client):
    resp = auth_client.post("/expenses/add", data={
        "amount": "", "category": "Food", "date": "2026-03-20"
    })
    assert resp.status_code == 200
    assert "Amount" in resp.data.decode()


def test_post_add_zero_amount_rerenders(auth_client):
    resp = auth_client.post("/expenses/add", data={
        "amount": "0", "category": "Food", "date": "2026-03-20"
    })
    assert resp.status_code == 200
    assert "greater than 0" in resp.data.decode()


def test_post_add_non_numeric_amount_rerenders(auth_client):
    resp = auth_client.post("/expenses/add", data={
        "amount": "abc", "category": "Food", "date": "2026-03-20"
    })
    assert resp.status_code == 200
    assert "must be a number" in resp.data.decode()


def test_post_add_invalid_category_rerenders(auth_client):
    resp = auth_client.post("/expenses/add", data={
        "amount": "10", "category": "Crypto", "date": "2026-03-20"
    })
    assert resp.status_code == 200
    assert "valid category" in resp.data.decode()


def test_post_add_invalid_date_rerenders(auth_client):
    resp = auth_client.post("/expenses/add", data={
        "amount": "10", "category": "Food", "date": "not-a-date"
    })
    assert resp.status_code == 200
    assert "valid date" in resp.data.decode()


def test_post_add_no_description_saves_null(auth_client, seed_user_id):
    resp = auth_client.post("/expenses/add", data={
        "amount": "33.0", "category": "Bills", "date": "2026-04-01",
        "description": ""
    }, follow_redirects=False)
    assert resp.status_code == 302
    assert "/profile" in resp.headers["Location"]
    conn = get_db()
    row = conn.execute(
        "SELECT description FROM expenses WHERE user_id = ? AND amount = 33.0 "
        "AND date = '2026-04-01'", (seed_user_id,)
    ).fetchone()
    conn.close()
    assert row is not None
    assert row["description"] is None
