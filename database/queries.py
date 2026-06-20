"""Pure query helpers for the profile page.

No Flask imports here — each function opens its own connection via get_db()
and closes it before returning. Parameterised SQL only.
"""

from datetime import datetime

from database.db import get_db


def _initials(name):
    parts = [p for p in name.split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][0].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def _member_since(created_at):
    # created_at is stored as "YYYY-MM-DD HH:MM:SS" (datetime('now')).
    if not created_at:
        return ""
    try:
        dt = datetime.strptime(created_at[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            dt = datetime.strptime(created_at[:10], "%Y-%m-%d")
        except ValueError:
            return ""
    return dt.strftime("%B %Y")


def get_user_by_id(user_id):
    """Return dict with name, email, member_since, initials — or None."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    return {
        "name": row["name"],
        "email": row["email"],
        "member_since": _member_since(row["created_at"]),
        "initials": _initials(row["name"]),
    }


def get_summary_stats(user_id):
    """Return dict with total_spent, transaction_count, top_category."""
    conn = get_db()
    try:
        agg = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS cnt "
            "FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        top = conn.execute(
            "SELECT category FROM expenses WHERE user_id = ? "
            "GROUP BY category ORDER BY SUM(amount) DESC, category ASC "
            "LIMIT 1",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()

    if agg["cnt"] == 0:
        return {"total_spent": 0, "transaction_count": 0, "top_category": "—"}

    return {
        "total_spent": round(agg["total"], 2),
        "transaction_count": agg["cnt"],
        "top_category": top["category"],
    }


def get_recent_transactions(user_id, limit=10):
    """Return list of dicts (date, description, category, amount), newest-first."""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT date, description, category, amount FROM expenses "
            "WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    finally:
        conn.close()

    return [
        {
            "date": r["date"],
            "description": r["description"],
            "category": r["category"],
            "amount": r["amount"],
        }
        for r in rows
    ]


def get_category_breakdown(user_id):
    """Return list of dicts (name, amount, pct) ordered by amount desc.

    pct values are integers that sum to exactly 100; the largest category
    absorbs any rounding remainder.
    """
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT category, SUM(amount) AS total FROM expenses "
            "WHERE user_id = ? GROUP BY category "
            "ORDER BY total DESC, category ASC",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return []

    grand_total = sum(r["total"] for r in rows)
    breakdown = [
        {"name": r["category"], "amount": round(r["total"], 2),
         "pct": int(round(r["total"] / grand_total * 100))}
        for r in rows
    ]

    # Adjust the largest category (first, since ordered desc) to make pct sum to 100.
    remainder = 100 - sum(item["pct"] for item in breakdown)
    if breakdown:
        breakdown[0]["pct"] += remainder

    return breakdown
