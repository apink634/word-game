"""SQLite storage for users and rounds. Every query is parameterized."""

import json
import sqlite3
import time

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    session_version INTEGER NOT NULL DEFAULT 1,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS rounds (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    state TEXT NOT NULL,
    moves INTEGER NOT NULL DEFAULT 0,
    chain_length INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'ended')),
    started_at INTEGER NOT NULL,
    finished_at INTEGER
);
-- At most one unfinished chain per player, enforced by the database itself.
CREATE UNIQUE INDEX IF NOT EXISTS one_active_round
    ON rounds(user_id) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS rounds_by_user ON rounds(user_id, finished_at);
"""


def get_db() -> sqlite3.Connection:
    """One connection per request, closed by ``close_db``."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    get_db().executescript(SCHEMA)


# --- users ---------------------------------------------------------------------


def create_user(email: str, display_name: str, password_hash: str) -> int | None:
    """Insert a user; None if the email is already registered."""
    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO users (email, display_name, password_hash, created_at)"
            " VALUES (?, ?, ?, ?)",
            (email, display_name, password_hash, int(time.time())),
        )
    except sqlite3.IntegrityError:
        return None
    db.commit()
    return cursor.lastrowid


def user_by_email(email: str) -> sqlite3.Row | None:
    return get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()


def user_by_id(user_id: int) -> sqlite3.Row | None:
    return get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def update_display_name(user_id: int, name: str) -> None:
    db = get_db()
    db.execute("UPDATE users SET display_name = ? WHERE id = ?", (name, user_id))
    db.commit()


def end_sessions(user_id: int) -> None:
    """Bump the session version so every existing session for this user stops working."""
    db = get_db()
    db.execute("UPDATE users SET session_version = session_version + 1 WHERE id = ?", (user_id,))
    db.commit()


def update_password(user_id: int, password_hash: str) -> int:
    """Store a new hash and bump the session version, ending other sessions."""
    db = get_db()
    db.execute(
        "UPDATE users SET password_hash = ?, session_version = session_version + 1 WHERE id = ?",
        (password_hash, user_id),
    )
    db.commit()
    return user_by_id(user_id)["session_version"]


# --- rounds --------------------------------------------------------------------


def active_round(user_id: int) -> sqlite3.Row | None:
    return (
        get_db()
        .execute("SELECT * FROM rounds WHERE user_id = ? AND status = 'active'", (user_id,))
        .fetchone()
    )


def start_round(user_id: int, state: dict) -> sqlite3.Row:
    """Return the player's unfinished chain, or start one.

    A double-clicked "New chain" can't create two chains: the unique index
    rejects the second insert, and we return the chain that already exists.
    """
    existing = active_round(user_id)
    if existing:
        return existing
    db = get_db()
    try:
        db.execute(
            "INSERT INTO rounds (user_id, state, started_at) VALUES (?, ?, ?)",
            (user_id, json.dumps(state), int(time.time())),
        )
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
    return active_round(user_id)


def save_progress(round_id: int, user_id: int, expected_moves: int, state, ended: bool) -> bool:
    """Save a move only if the chain is still where the player saw it.

    ``expected_moves`` is how many moves had been made when the form was shown.
    A repeated or stale submission (double click, back button, second tab)
    finds a different count, changes nothing and returns False. So each move,
    and the final result, is recorded exactly once.
    """
    db = get_db()
    cursor = db.execute(
        "UPDATE rounds SET state = ?, moves = ?, chain_length = ?, status = ?, finished_at = ?"
        " WHERE id = ? AND user_id = ? AND status = 'active' AND moves = ?",
        (
            json.dumps(state.as_dict()),
            state.moves,
            state.length,
            "ended" if ended else "active",
            int(time.time()) if ended else None,
            round_id,
            user_id,
            expected_moves,
        ),
    )
    db.commit()
    return cursor.rowcount == 1


def round_for_user(round_id: int, user_id: int) -> sqlite3.Row | None:
    """A round only if it belongs to this user (others get None -> 404)."""
    return (
        get_db()
        .execute("SELECT * FROM rounds WHERE id = ? AND user_id = ?", (round_id, user_id))
        .fetchone()
    )


def finished_rounds(user_id: int) -> list[sqlite3.Row]:
    return (
        get_db()
        .execute(
            "SELECT * FROM rounds WHERE user_id = ? AND status = 'ended'"
            " ORDER BY finished_at DESC, id DESC",
            (user_id,),
        )
        .fetchall()
    )
