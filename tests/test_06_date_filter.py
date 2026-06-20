"""Tests for Step 6: Date Filter on the /profile route.

All expected behaviour is derived from .claude/specs/06-date-filter.md.
Seed data (8 June-2026 expenses) comes from database/db.py::seed_db().

Seed expenses (user demo@spendly.com):
  2026-06-01  Food          ₹42.50
  2026-06-03  Transport     ₹45.00
  2026-06-05  Bills         ₹120.00
  2026-06-08  Health        ₹30.00
  2026-06-10  Entertainment ₹25.99
  2026-06-12  Shopping      ₹60.00
  2026-06-15  Food          ₹8.75
  2026-06-18  Other         ₹14.00
  Total: ₹346.24, 8 transactions
"""

import pytest

from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
)


# ------------------------------------------------------------------ #
# Helper                                                              #
# ------------------------------------------------------------------ #

def _get(auth_client, params=""):
    """GET /profile with optional query string, return response."""
    url = f"/profile{params}"
    return auth_client.get(url, follow_redirects=False)


# ================================================================== #
# Happy paths — HTTP layer                                            #
# ================================================================== #

def test_date_filter_no_params_returns_all(auth_client):
    """Spec: no query params → unfiltered view with all 8 expenses (₹346.24)."""
    resp = _get(auth_client)
    assert resp.status_code == 200
    body = resp.data.decode()
    # All 8 transactions visible — check total and count
    assert "346.24" in body
    assert "8" in body


def test_date_filter_range_returns_correct_subset(auth_client):
    """Spec: date_from=2026-06-05, date_to=2026-06-12 → 4 transactions, ₹235.99 total."""
    resp = _get(auth_client, "?date_from=2026-06-05&date_to=2026-06-12")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "235.99" in body
    assert "4" in body


def test_date_filter_start_only(auth_client):
    """Spec: date_from=2026-06-10 only → transactions on/after 2026-06-10 (4 rows)."""
    resp = _get(auth_client, "?date_from=2026-06-10")
    assert resp.status_code == 200
    body = resp.data.decode()
    # 06-10 (25.99) + 06-12 (60.00) + 06-15 (8.75) + 06-18 (14.00) = 108.74, 4 rows
    assert "108.74" in body
    assert "4" in body


def test_date_filter_end_only(auth_client):
    """Spec: date_to=2026-06-10 only → transactions on/before 2026-06-10 (5 rows)."""
    resp = _get(auth_client, "?date_to=2026-06-10")
    assert resp.status_code == 200
    body = resp.data.decode()
    # 06-01 (42.50) + 06-03 (45.00) + 06-05 (120.00) + 06-08 (30.00) + 06-10 (25.99) = 263.49, 5 rows
    assert "263.49" in body
    assert "5" in body


def test_date_filter_range_15_to_30(auth_client):
    """Spec: date_from=2026-06-15, date_to=2026-06-30 → 2 transactions, ₹22.75 total."""
    resp = _get(auth_client, "?date_from=2026-06-15&date_to=2026-06-30")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "22.75" in body
    assert "2" in body


def test_date_filter_no_matches(auth_client):
    """Spec: range with no expenses → ₹0.00 total, 0 transactions, no errors."""
    resp = _get(auth_client, "?date_from=2025-01-01&date_to=2025-01-31")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "0.00" in body


# ================================================================== #
# Edge cases                                                          #
# ================================================================== #

def test_date_filter_start_after_end(auth_client):
    """Spec: start > end → flash 'Start date must be before end date.' and
    fall back to the unfiltered view (all 8 transactions, ₹346.24)."""
    resp = _get(auth_client, "?date_from=2026-06-30&date_to=2026-06-01")
    assert resp.status_code == 200
    body = resp.data.decode()
    # Must show an error message to the user
    assert "Start date must be before end date" in body
    # Must fall back to the unfiltered total
    assert "346.24" in body


def test_date_filter_malformed_date_returns_200(auth_client):
    """Spec: malformed date string → silently falls back to unfiltered view
    (no crash, HTTP 200)."""
    resp = _get(auth_client, "?date_from=not-a-date")
    assert resp.status_code == 200


def test_date_filter_malformed_end_returns_200(auth_client):
    """Spec: malformed end date → silently falls back to unfiltered view."""
    resp = _get(auth_client, "?date_to=13/32/2026")
    assert resp.status_code == 200


def test_date_filter_empty_string_params_returns_200(auth_client):
    """Spec: empty string date params → treated as absent, no crash (HTTP 200)."""
    resp = _get(auth_client, "?date_from=&date_to=")
    assert resp.status_code == 200


def test_date_filter_rupee_symbol_always_present(auth_client):
    """Spec: ₹ symbol must appear regardless of the active filter."""
    resp = _get(auth_client, "?date_from=2026-06-05&date_to=2026-06-12")
    assert resp.status_code == 200
    assert "₹" in resp.data.decode()


def test_date_filter_empty_range_rupee_symbol(auth_client):
    """Spec: even with 0 transactions the ₹ symbol must still be shown."""
    resp = _get(auth_client, "?date_from=2025-01-01&date_to=2025-01-31")
    assert resp.status_code == 200
    assert "₹" in resp.data.decode()


# ================================================================== #
# Auth guard                                                          #
# ================================================================== #

def test_date_filter_unauthenticated_redirects(client):
    """Spec (via Step 5): unauthenticated GET /profile must redirect to /login."""
    resp = client.get("/profile", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


# ================================================================== #
# DB helper unit tests — tested directly, not via HTTP                #
# ================================================================== #

def test_get_summary_stats_with_date_range(seed_user_id):
    """get_summary_stats with start/end returns correct total and count for
    the filtered range 2026-06-05..2026-06-12 (₹235.99, 4 transactions)."""
    stats = get_summary_stats(seed_user_id, date_from="2026-06-05", date_to="2026-06-12")
    assert stats["transaction_count"] == 4
    assert stats["total_spent"] == pytest.approx(235.99, abs=0.01)


def test_get_summary_stats_no_params_returns_all(seed_user_id):
    """get_summary_stats with no date bounds returns all 8 expenses (₹346.24)."""
    stats = get_summary_stats(seed_user_id)
    assert stats["transaction_count"] == 8
    assert stats["total_spent"] == pytest.approx(346.24, abs=0.01)


def test_get_summary_stats_empty_range(seed_user_id):
    """get_summary_stats for a range with no data → total 0, count 0, top_category '—'."""
    stats = get_summary_stats(seed_user_id, date_from="2025-01-01", date_to="2025-01-31")
    assert stats["transaction_count"] == 0
    assert stats["total_spent"] == 0
    assert stats["top_category"] == "—"


def test_get_recent_transactions_with_date_range(seed_user_id):
    """get_recent_transactions with start/end returns only transactions in range.

    Range 2026-06-05..2026-06-12 must return exactly 4 rows, all with dates
    within the specified bounds, ordered newest-first.
    """
    txs = get_recent_transactions(seed_user_id, date_from="2026-06-05", date_to="2026-06-12")
    assert len(txs) == 4
    for tx in txs:
        assert "2026-06-05" <= tx["date"] <= "2026-06-12"
    # Verify newest-first ordering
    dates = [tx["date"] for tx in txs]
    assert dates == sorted(dates, reverse=True)


def test_get_recent_transactions_start_only(seed_user_id):
    """get_recent_transactions with start only returns rows on/after that date."""
    txs = get_recent_transactions(seed_user_id, date_from="2026-06-15")
    assert len(txs) == 2
    for tx in txs:
        assert tx["date"] >= "2026-06-15"


def test_get_recent_transactions_end_only(seed_user_id):
    """get_recent_transactions with end only returns rows on/before that date."""
    txs = get_recent_transactions(seed_user_id, date_to="2026-06-03")
    assert len(txs) == 2
    for tx in txs:
        assert tx["date"] <= "2026-06-03"


def test_get_recent_transactions_no_matches(seed_user_id):
    """get_recent_transactions for a range with no data returns an empty list."""
    txs = get_recent_transactions(seed_user_id, date_from="2025-01-01", date_to="2025-01-31")
    assert txs == []


def test_get_category_breakdown_with_date_range(seed_user_id):
    """get_category_breakdown with start/end returns breakdown for filtered range.

    Range 2026-06-05..2026-06-12 has: Bills ₹120, Shopping ₹60, Health ₹30,
    Entertainment ₹25.99. Percentages must sum to 100.
    """
    cats = get_category_breakdown(seed_user_id, date_from="2026-06-05", date_to="2026-06-12")
    # Should have exactly 4 categories in range
    assert len(cats) == 4
    # All required keys present
    for cat in cats:
        assert "name" in cat
        assert "amount" in cat
        assert "pct" in cat
    # Percentages sum to 100
    assert sum(cat["pct"] for cat in cats) == 100
    # Ordered by amount descending — Bills (120) is first
    assert cats[0]["name"] == "Bills"
    assert cats[0]["amount"] == pytest.approx(120.00, abs=0.01)


def test_get_category_breakdown_no_params_returns_all(seed_user_id):
    """get_category_breakdown with no bounds returns breakdown for all expenses."""
    cats = get_category_breakdown(seed_user_id)
    assert len(cats) > 0
    # Percentages still sum to 100
    assert sum(cat["pct"] for cat in cats) == 100
    # Grand total must equal ₹346.24
    total = sum(cat["amount"] for cat in cats)
    assert total == pytest.approx(346.24, abs=0.01)


def test_get_category_breakdown_empty_range(seed_user_id):
    """get_category_breakdown for a range with no data returns an empty list."""
    cats = get_category_breakdown(seed_user_id, date_from="2025-01-01", date_to="2025-01-31")
    assert cats == []
