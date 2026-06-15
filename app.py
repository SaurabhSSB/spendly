import re
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, abort
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_db, init_db, seed_db, get_user_by_email, get_user_by_id, get_expense_summary

app = Flask(__name__)
app.secret_key = 'spendly-dev-secret-key'


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
    user = get_user_by_id(session["user_id"])
    if user is None:
        abort(404)
    summary = get_expense_summary(session["user_id"])
    return render_template("profile.html", user=user, summary=summary)


@app.route("/expenses/add")
def add_expense():
    return render_template("add-expense.html")


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return render_template("edit-expense.html")


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return render_template("delete-expense.html")


# ------------------------------------------------------------------ #
# Database initialisation — runs once at startup                      #
# ------------------------------------------------------------------ #
with app.app_context():
    init_db()
    seed_db()


if __name__ == "__main__":
    app.run(debug=True, port=5001)
