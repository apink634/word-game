"""Sign up, log in, log out and account maintenance.

Sessions carry a version number. Changing the password or logging out bumps
it, so an old session cookie (a stale session) stops working everywhere.
"""

import re

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from werkzeug.security import check_password_hash, generate_password_hash

from wordgame import db

bp = Blueprint("auth", __name__)
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to play."

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD = 8
MAX_NAME = 30
# Compared against when an email isn't registered, so a wrong email takes as
# long as a wrong password and the reply can't reveal who has an account.
_DUMMY_HASH = generate_password_hash("not-a-real-password")
LOGIN_FAILED = "Email or password is incorrect."


class User(UserMixin):
    def __init__(self, row) -> None:
        self.id = row["id"]
        self.email = row["email"]
        self.display_name = row["display_name"]
        self.session_version = row["session_version"]

    def get_id(self) -> str:
        return f"{self.id}:{self.session_version}"


@login_manager.user_loader
def load_user(session_id: str):
    """Accept a session only if its version matches the database."""
    try:
        user_id, version = (int(part) for part in session_id.split(":"))
    except ValueError:
        return None
    row = db.user_by_id(user_id)
    if row is None or row["session_version"] != version:
        return None
    return User(row)


def _clean_name(raw: str) -> str | None:
    name = " ".join((raw or "").split())
    return name if 1 <= len(name) <= MAX_NAME else None


@bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        name = _clean_name(request.form.get("display_name", ""))
        password = request.form.get("password", "")
        error = None
        if not EMAIL.match(email):
            error = "Enter a valid email address."
        elif name is None:
            error = f"Display name must be 1–{MAX_NAME} characters."
        elif len(password) < MIN_PASSWORD:
            error = f"Password must be at least {MIN_PASSWORD} characters."
        else:
            user_id = db.create_user(email, name, generate_password_hash(password))
            if user_id is None:
                error = "That email is already registered. Try logging in."
            else:
                login_user(User(db.user_by_id(user_id)))
                return redirect(url_for("play.dashboard"))
        flash(error)
        return render_template("signup.html", email=email), 400
    return render_template("signup.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        row = db.user_by_email(email)
        valid = check_password_hash(row["password_hash"] if row else _DUMMY_HASH, password)
        if row is None or not valid:
            flash(LOGIN_FAILED)
            return render_template("login.html", email=email), 401
        login_user(User(row))
        return redirect(url_for("play.dashboard"))
    return render_template("login.html")


@bp.post("/logout")
@login_required
def logout():
    # Bumping the version ends this session on every device, so a copied or
    # saved session cookie can't be reused after logging out.
    db.end_sessions(current_user.id)
    logout_user()
    flash("You're logged out.")
    return redirect(url_for("home"))


@bp.route("/account", methods=["GET", "POST"])
@login_required
def account():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "name":
            name = _clean_name(request.form.get("display_name", ""))
            if name is None:
                flash(f"Display name must be 1–{MAX_NAME} characters.")
                return render_template("account.html"), 400
            db.update_display_name(current_user.id, name)
            flash("Display name updated.")
        elif action == "password":
            row = db.user_by_id(current_user.id)
            current = request.form.get("current_password", "")
            new = request.form.get("new_password", "")
            if not check_password_hash(row["password_hash"], current):
                flash("Current password is incorrect.")
                return render_template("account.html"), 400
            if len(new) < MIN_PASSWORD:
                flash(f"New password must be at least {MIN_PASSWORD} characters.")
                return render_template("account.html"), 400
            db.update_password(current_user.id, generate_password_hash(new))
            # Other sessions are now stale; keep this one signed in.
            login_user(User(db.user_by_id(current_user.id)))
            flash("Password changed. Other sessions were signed out.")
        return redirect(url_for("auth.account"))
    return render_template("account.html")
