import sqlite3
from flask import Flask, render_template, request, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_db, init_db, seed_db
from database.queries import (
    get_user_by_id,
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
)


def rupees(value):
    """Format a numeric amount as Indian Rupees, e.g. 346.24 -> '₹346.24'."""
    return f"₹{value:,.2f}"

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

    raw_stats = get_summary_stats(user_id)
    stats = {
        "total_spent": rupees(raw_stats["total_spent"]),
        "transaction_count": raw_stats["transaction_count"],
        "top_category": raw_stats["top_category"],
    }

    transactions = [
        {**tx, "amount": rupees(tx["amount"])}
        for tx in get_recent_transactions(user_id)
    ]

    categories = [
        {"name": cat["name"], "amount": rupees(cat["amount"]), "percent": cat["pct"]}
        for cat in get_category_breakdown(user_id)
    ]

    return render_template("profile.html", user=user, stats=stats,
                           transactions=transactions, categories=categories)


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
