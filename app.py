import sqlite3
import calendar
from datetime import date, datetime
from flask import Flask, render_template, request, session, redirect, url_for, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_db, init_db, seed_db
from database.queries import (
    get_user_by_id,
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
    insert_expense,
    get_expense_by_id,
    update_expense,
    delete_expense as delete_expense_row,
)

# The seven fixed expense categories used across add/edit forms and validation.
CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]


def _validate_expense_form(form):
    """Validate add/edit expense form data.

    Returns (values, error): ``values`` is a dict of the cleaned/submitted
    fields suitable for re-populating the form; ``error`` is an error message
    string or None when the data is valid. When valid, ``values`` also carries
    the parsed ``amount`` as a float.
    """
    amount_raw = form.get("amount", "").strip()
    category = form.get("category", "").strip()
    date_raw = form.get("date", "").strip()
    description = form.get("description", "").strip()

    values = {
        "amount": amount_raw,
        "category": category,
        "date": date_raw,
        "description": description,
    }

    try:
        amount = float(amount_raw)
    except ValueError:
        return values, "Amount is required and must be a number."
    if amount <= 0:
        return values, "Amount must be greater than 0."

    if category not in CATEGORIES:
        return values, "Please choose a valid category."

    try:
        datetime.strptime(date_raw, "%Y-%m-%d")
    except ValueError:
        return values, "Please enter a valid date."

    values["amount"] = amount
    values["description"] = description or None
    return values, None


def rupees(value):
    """Format a numeric amount as Indian Rupees, e.g. 346.24 -> '₹346.24'."""
    return f"₹{value:,.2f}"


def _valid_date(value):
    """Return value if it is a well-formed YYYY-MM-DD date, else None.

    A malformed bound is ignored (treated as not supplied) rather than raising.
    """
    if not value:
        return None
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return value
    except ValueError:
        return None


def _months_ago(d, months):
    """Return the date `months` calendar months before `d`, clamping the day."""
    month_index = d.month - 1 - months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


app = Flask(__name__)
app.secret_key = "spendly-dev-secret"  # replace with env var before production

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        if session.get("user_id"):
            return redirect(url_for("dashboard"))
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not name or not email or not password:
        return render_template("register.html", error="All fields are required.", name=name, email=email)

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password)),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return render_template("register.html", error="An account with that email already exists.", name=name, email=email)
    conn.close()
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if session.get("user_id"):
            return redirect(url_for("dashboard"))
        return render_template("login.html", next=request.args.get("next", ""))

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()

    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.", email=email)

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]

    next_url = request.form.get("next", "")
    if next_url and next_url.startswith("/"):
        return redirect(next_url)
    return redirect(url_for("profile"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/dashboard")
def dashboard():
    if not session.get("user_id"):
        return redirect(url_for("login", next="/dashboard"))
    return render_template("dashboard.html", name=session["user_name"])


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login", next="/profile"))

    user_id = session["user_id"]

    user = get_user_by_id(user_id)
    if user is None:
        session.clear()
        return redirect(url_for("login", next="/profile"))

    date_from = _valid_date(request.args.get("date_from", "").strip())
    date_to = _valid_date(request.args.get("date_to", "").strip())

    # Both bounds are valid YYYY-MM-DD strings here, so lexicographic order
    # matches chronological order. An inverted range is a user mistake: clear
    # both bounds and tell them, rather than silently showing an empty page.
    if date_from and date_to and date_from > date_to:
        flash("Start date must be before end date.")
        date_from = date_to = None

    raw_stats = get_summary_stats(user_id, date_from=date_from, date_to=date_to)
    stats = {
        "total_spent": rupees(raw_stats["total_spent"]),
        "transaction_count": raw_stats["transaction_count"],
        "top_category": raw_stats["top_category"],
    }

    transactions = [
        {**tx, "amount": rupees(tx["amount"])}
        for tx in get_recent_transactions(user_id, date_from=date_from, date_to=date_to)
    ]

    categories = [
        {"name": cat["name"], "amount": rupees(cat["amount"]), "percent": cat["pct"]}
        for cat in get_category_breakdown(user_id, date_from=date_from, date_to=date_to)
    ]

    # Quick-select preset boundaries (computed here, never in the template).
    today = date.today()
    presets = {
        "today": today.isoformat(),
        "this_month": today.replace(day=1).isoformat(),
        "last_3m": _months_ago(today, 3).isoformat(),
        "last_6m": _months_ago(today, 6).isoformat(),
    }

    if not date_from and not date_to:
        active_preset = "all"
    elif date_to == presets["today"] and date_from == presets["this_month"]:
        active_preset = "this_month"
    elif date_to == presets["today"] and date_from == presets["last_3m"]:
        active_preset = "last_3m"
    elif date_to == presets["today"] and date_from == presets["last_6m"]:
        active_preset = "last_6m"
    else:
        active_preset = "custom"

    active_range = {
        "date_from": date_from or "",
        "date_to": date_to or "",
        "active": bool(date_from or date_to),
        "preset": active_preset,
    }

    return render_template("profile.html", user=user, stats=stats,
                           transactions=transactions, categories=categories,
                           active_range=active_range, presets=presets)


@app.route("/analytics")
def analytics():
    if not session.get("user_id"):
        return redirect(url_for("login", next="/analytics"))
    return render_template("analytics.html")


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if not session.get("user_id"):
        return redirect(url_for("login", next="/expenses/add"))

    if request.method == "GET":
        return render_template(
            "add_expense.html",
            categories=CATEGORIES,
            values={"date": date.today().isoformat()},
        )

    values, error = _validate_expense_form(request.form)
    if error:
        return render_template(
            "add_expense.html", categories=CATEGORIES, values=values, error=error
        )

    insert_expense(
        session["user_id"],
        values["amount"],
        values["category"],
        values["date"],
        values["description"],
    )
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    if not session.get("user_id"):
        return redirect(url_for("login", next=f"/expenses/{id}/edit"))

    expense = get_expense_by_id(id, session["user_id"])
    if expense is None:
        abort(404)

    if request.method == "GET":
        return render_template(
            "edit_expense.html", categories=CATEGORIES, expense=expense, values=expense
        )

    values, error = _validate_expense_form(request.form)
    if error:
        return render_template(
            "edit_expense.html",
            categories=CATEGORIES,
            expense=expense,
            values=values,
            error=error,
        )

    update_expense(
        id,
        session["user_id"],
        values["amount"],
        values["category"],
        values["date"],
        values["description"],
    )
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/delete", methods=["POST"])
def delete_expense(id):
    if not session.get("user_id"):
        return redirect(url_for("login", next="/profile"))

    expense = get_expense_by_id(id, session["user_id"])
    if expense is None:
        abort(404)

    delete_expense_row(id, session["user_id"])
    return redirect(url_for("profile"))


if __name__ == "__main__":
    app.run(debug=True, port=5001)
