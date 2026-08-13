import re
import sqlite3
import calendar
import math
from datetime import date, datetime
from flask import Flask, render_template, request, redirect, url_for, session, abort, flash
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import (
    get_db, init_db, seed_db,
    get_user_by_email,
    get_expenses,           # B1
    get_detailed_summary,   # B2
    get_category_breakdown, # B3
)
from database import queries

app = Flask(__name__)
app.secret_key = 'spendly-dev-secret-key'


def _parse_date(value):
    if not value:
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
        return parsed.strftime("%Y-%m-%d")
    except ValueError:
        return None


EXPENSE_CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]


def _months_ago(base, months):
    month_index = base.month - 1 - months
    year = base.year + month_index // 12
    month = month_index % 12 + 1
    day = min(base.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        error = None

        if not name:
            error = "Name is required."
        elif len(name) > 255:
            error = "Name must be 255 characters or less."
        elif not email:
            error = "Email is required."
        elif not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            error = "Invalid email address."
        elif not password:
            error = "Password is required."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."

        if error is None:
            db = get_db()
            try:
                db.execute(
                    "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                    (name, email, generate_password_hash(password))
                )
                db.commit()
                db.close()
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                error = "Email already registered."
                db.close()

        return render_template("register.html", error=error)

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        error = None

        if not email:
            error = "Email is required."
        elif not password:
            error = "Password is required."
        else:
            user = get_user_by_email(email)
            if user is None or not check_password_hash(user["password_hash"], password):
                error = "Invalid email or password."

        if error is not None:
            return render_template("login.html", error=error)

        session.clear()
        session["user_id"] = user["id"]
        return redirect(url_for("profile"))

    return render_template("login.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    user = queries.get_user_by_id(session["user_id"])
    if user is None:
        abort(404)

    today = date.today()
    this_month_start = today.replace(day=1)
    this_month_end = date(today.year, today.month,
                           calendar.monthrange(today.year, today.month)[1])
    last_3_start = _months_ago(today, 3)
    last_6_start = _months_ago(today, 6)

    parsed_from = _parse_date(request.args.get("date_from"))
    parsed_to = _parse_date(request.args.get("date_to"))

    date_from = date_to = None
    display_from = display_to = None

    if parsed_from and parsed_to:
        display_from, display_to = parsed_from, parsed_to
        if parsed_from > parsed_to:
            flash("Start date must be before end date.")
        else:
            date_from, date_to = parsed_from, parsed_to
    # else: partial or malformed params -> stay None, silent fallback

    active_preset = "all_time"
    if date_from == this_month_start.isoformat() and date_to == this_month_end.isoformat():
        active_preset = "this_month"
    elif date_from == last_3_start.isoformat() and date_to == today.isoformat():
        active_preset = "last_3_months"
    elif date_from == last_6_start.isoformat() and date_to == today.isoformat():
        active_preset = "last_6_months"
    elif date_from and date_to:
        active_preset = "custom"

    summary = queries.get_summary_stats(session["user_id"], date_from, date_to)
    transactions = queries.get_recent_transactions(session["user_id"], date_from=date_from, date_to=date_to)
    breakdown = queries.get_category_breakdown(session["user_id"], date_from, date_to)

    return render_template(
        "profile.html",
        user=user,
        summary=summary,
        transactions=transactions,
        breakdown=breakdown,
        active_preset=active_preset,
        filter_from=display_from,
        filter_to=display_to,
        this_month_start=this_month_start.isoformat(),
        this_month_end=this_month_end.isoformat(),
        last_3_start=last_3_start.isoformat(),
        last_6_start=last_6_start.isoformat(),
        today=today.isoformat(),
    )


# ------------------------------------------------------------------ #
# B1 — Transaction History                                            #
# Subagent 1 writes here: GET /expenses                              #
# ------------------------------------------------------------------ #

@app.route("/expenses")
def expenses():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    rows = get_expenses(session["user_id"])
    return render_template("expenses.html", expenses=rows)


# ------------------------------------------------------------------ #
# B2 — Summary Stats                                                  #
# Subagent 2 writes here: GET /expenses/summary                      #
# ------------------------------------------------------------------ #

@app.route("/expenses/summary")
def expenses_summary():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    summary = get_detailed_summary(session["user_id"])
    return render_template("summary.html", summary=summary)


# ------------------------------------------------------------------ #
# B3 — Category Breakdown                                             #
# Subagent 3 writes here: GET /expenses/categories                   #
# ------------------------------------------------------------------ #

@app.route("/expenses/categories")
def expenses_categories():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    breakdown = get_category_breakdown(session["user_id"])
    return render_template("categories.html", breakdown=breakdown)


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    if request.method == "POST":
        amount_raw = request.form.get("amount", "").strip()
        category = request.form.get("category", "").strip()
        date_str = request.form.get("date", "").strip()
        description_raw = request.form.get("description", "").strip()

        error = None
        amount = None
        parsed_date = None

        if not amount_raw:
            error = "Amount is required."
        else:
            try:
                amount = float(amount_raw)
            except ValueError:
                error = "Amount must be a number."
            else:
                if not math.isfinite(amount) or amount <= 0:
                    error = "Amount must be greater than 0."

        if error is None and category not in EXPENSE_CATEGORIES:
            error = "Please select a valid category."

        if error is None:
            parsed_date = _parse_date(date_str)
            if parsed_date is None:
                error = "Please enter a valid date."

        if error is None and len(description_raw) > 200:
            error = "Description must be 200 characters or less."

        if error is not None:
            return render_template(
                "add-expense.html",
                error=error,
                categories=EXPENSE_CATEGORIES,
                form_amount=amount_raw,
                form_category=category,
                form_date=date_str,
                form_description=description_raw,
            )

        description = description_raw or None
        queries.insert_expense(session["user_id"], amount, category, parsed_date, description)
        return redirect(url_for("profile"))

    return render_template(
        "add-expense.html",
        categories=EXPENSE_CATEGORIES,
        form_amount="",
        form_category="",
        form_date=date.today().strftime("%Y-%m-%d"),
        form_description="",
    )


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return render_template("edit-expense.html")


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return render_template("delete-expense.html")


@app.route("/analytics")
def analytics():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("analytics.html")


# ------------------------------------------------------------------ #
# Database initialisation — runs once at startup                      #
# ------------------------------------------------------------------ #
with app.app_context():
    init_db()
    seed_db()


if __name__ == "__main__":
    app.run(debug=True, port=5001)
