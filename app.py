import sqlite3
from flask import Flask, render_template, request, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_db, init_db, seed_db

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

    user = {
        "name": "Alex Johnson",
        "email": "alex@example.com",
        "member_since": "January 2024",
        "initials": "AJ",
    }
    stats = {
        "total_spent": "₹12,450",
        "transaction_count": 24,
        "top_category": "Food",
    }
    transactions = [
        {"date": "Jun 18, 2025", "description": "Swiggy order",        "category": "Food",          "amount": "₹340"},
        {"date": "Jun 17, 2025", "description": "Metro card recharge",  "category": "Transport",     "amount": "₹500"},
        {"date": "Jun 15, 2025", "description": "Electricity bill",     "category": "Bills",         "amount": "₹1,200"},
        {"date": "Jun 14, 2025", "description": "Pharmacy",             "category": "Health",        "amount": "₹280"},
        {"date": "Jun 12, 2025", "description": "Netflix subscription", "category": "Entertainment", "amount": "₹649"},
        {"date": "Jun 10, 2025", "description": "Grocery run",          "category": "Food",          "amount": "₹875"},
    ]
    categories = [
        {"name": "Food",          "amount": "₹4,200", "percent": 34},
        {"name": "Bills",         "amount": "₹3,100", "percent": 25},
        {"name": "Shopping",      "amount": "₹2,400", "percent": 19},
        {"name": "Transport",     "amount": "₹1,500", "percent": 12},
        {"name": "Health",        "amount": "₹750",   "percent": 6},
        {"name": "Entertainment", "amount": "₹500",   "percent": 4},
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
