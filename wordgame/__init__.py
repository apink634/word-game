"""Flask app factory for Word Chain."""

import os
import secrets
from pathlib import Path

from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect

from wordgame import db
from wordgame.auth import bp as auth_bp
from wordgame.auth import login_manager
from wordgame.play import bp as play_bp

csrf = CSRFProtect()


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    app.config.update(
        # Set WORDGAME_SECRET_KEY outside development so sessions survive restarts.
        SECRET_KEY=os.environ.get("WORDGAME_SECRET_KEY") or secrets.token_hex(32),
        DATABASE=os.environ.get(
            "WORDGAME_DATABASE", str(Path(app.instance_path) / "wordchain.sqlite3")
        ),
        WORD_PICKER=os.environ.get("WORDGAME_PICKER", "random"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("WORDGAME_SECURE_COOKIES") == "1",
        REMEMBER_COOKIE_DURATION=0,
    )
    if test_config:
        app.config.update(test_config)

    csrf.init_app(app)
    login_manager.init_app(app)
    app.teardown_appcontext(db.close_db)
    with app.app_context():
        db.init_db()

    app.register_blueprint(auth_bp)
    app.register_blueprint(play_bp)

    @app.get("/")
    def home():
        return render_template("home.html")

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", message="Page not found."), 404

    @app.errorhandler(400)
    def bad_request(error):
        # CSRF failures land here: show a plain message, not a stack trace.
        return render_template(
            "error.html", message=getattr(error, "description", "Bad request.")
        ), 400

    @app.after_request
    def security_headers(response):
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self'; script-src 'none'; "
            "form-action 'self'; frame-ancestors 'none'; base-uri 'none'",
        )
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        return response

    return app
