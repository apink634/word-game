"""Integration checks through the Flask test client, with CSRF switched on.

Covers the Review 3 checks: wrong passwords, second-user access, stale
sessions and duplicate result requests, plus persistence and maintenance.
"""

import sqlite3

from conftest import login, logout, post, signup, token

from wordgame import create_app

# --- accounts and wrong passwords ---------------------------------------------


def test_password_is_stored_as_a_hash(client, app):
    signup(client)
    row = (
        sqlite3.connect(app.config["DATABASE"])
        .execute("SELECT password_hash FROM users")
        .fetchone()
    )
    assert "correct horse" not in row[0]
    assert row[0].startswith(("scrypt:", "pbkdf2:"))


def test_duplicate_email_is_rejected(client):
    signup(client)
    logout(client)
    response = signup(client, email="ANN@example.com")
    assert response.status_code == 400
    assert "already registered" in response.get_data(as_text=True)


def test_wrong_password_and_unknown_email_get_the_same_reply(client):
    signup(client)
    logout(client)
    wrong = login(client, password="wrong password")
    unknown = login(client, email="nobody@example.com")
    assert wrong.status_code == unknown.status_code == 401
    message = "Email or password is incorrect."
    assert message in wrong.get_data(as_text=True)
    assert message in unknown.get_data(as_text=True)
    assert client.get("/dashboard").status_code == 302  # still logged out


def test_pages_need_login(client):
    for path in ("/play", "/dashboard", "/account", "/rounds/1"):
        response = client.get(path)
        assert response.status_code == 302 and "/login" in response.headers["Location"]


def test_forms_without_a_csrf_token_are_refused(client):
    signup(client)
    assert client.post("/play/new").status_code == 400
    assert client.post("/login", data={"email": "a@b.co", "password": "x"}).status_code == 400


# --- playing and saving -------------------------------------------------------
# The test picker always starts with APPLE, then EAGLE, EARTH, HEART ...


def play(client, word, expected):
    return post(client, "/play/guess", {"guess": word, "expected_moves": expected}, page="/play")


def finish_a_chain(client):
    """Solve APPLE, then miss EAGLE three times: a finished chain of 1."""
    post(client, "/play/new", page="/play")
    play(client, "apple", 0)
    play(client, "earth", 1)
    play(client, "eight", 2)
    return play(client, "enemy", 3)


def test_full_chain_is_saved_to_private_history(client):
    signup(client)
    response = finish_a_chain(client)
    assert response.status_code == 302 and "/rounds/" in response.headers["Location"]
    detail = client.get(response.headers["Location"]).get_data(as_text=True)
    assert "Chain of 1" in detail and "EAGLE" in detail and "missed" in detail
    page = client.get("/dashboard").get_data(as_text=True)
    assert "Best chain</dt><dd>1" in page and "APPLE" in page


def test_solving_a_word_moves_the_chain_on(client):
    signup(client)
    post(client, "/play/new", page="/play")
    play(client, "apple", 0)
    page = client.get("/play").get_data(as_text=True)
    assert "Chain: <strong>1</strong>" in page
    assert "E _ _ _ _" in page  # next word starts with APPLE's last letter
    assert "APPLE" in page  # shown in the solved chain


def test_current_answer_is_not_on_the_page(client):
    signup(client)
    post(client, "/play/new", page="/play")
    page = client.get("/play").get_data(as_text=True).lower()
    assert "apple" not in page
    assert "a _ _ _ _" in page


def test_invalid_guess_does_not_use_a_guess(client):
    signup(client)
    post(client, "/play/new", page="/play")
    play(client, "tiger", 0)  # wrong first letter
    play(client, "azzzz", 0)  # not a word
    page = client.get("/play").get_data(as_text=True)
    assert "Guesses left for this word: <strong>3</strong>" in page


def test_hint_shows_last_letter_and_costs_a_guess(client):
    signup(client)
    post(client, "/play/new", page="/play")
    post(client, "/play/hint", {"expected_moves": 0}, page="/play")
    page = client.get("/play").get_data(as_text=True)
    assert "A _ _ _ E" in page
    assert "Guesses left for this word: <strong>2</strong>" in page
    assert "Show the last letter" not in page  # one hint per word
    again = post(client, "/play/hint", {"expected_moves": 1}, page="/play", follow_redirects=True)
    assert "No hint available" in again.get_data(as_text=True)


# --- duplicate result requests -------------------------------------------------


def test_resubmitting_a_solving_guess_counts_once(client, app):
    signup(client)
    post(client, "/play/new", page="/play")
    play(client, "apple", 0)
    again = play(client, "apple", 0)  # same form sent again (double click / back button)
    assert again.status_code == 302
    assert "already counted" in client.get("/play").get_data(as_text=True)
    row = (
        sqlite3.connect(app.config["DATABASE"])
        .execute("SELECT chain_length, moves FROM rounds")
        .fetchone()
    )
    assert row == (1, 1)


def test_resubmitting_the_final_move_records_one_result(client, app):
    signup(client)
    finish_a_chain(client)
    play(client, "enemy", 3)
    rows = (
        sqlite3.connect(app.config["DATABASE"])
        .execute("SELECT status, chain_length FROM rounds")
        .fetchall()
    )
    assert rows == [("ended", 1)]
    assert "Chains played</dt><dd>1" in client.get("/dashboard").get_data(as_text=True)


def test_double_clicking_new_chain_makes_one_chain(client, app):
    signup(client)
    post(client, "/play/new", page="/play")
    post(client, "/play/new", page="/play")
    count = (
        sqlite3.connect(app.config["DATABASE"])
        .execute("SELECT COUNT(*) FROM rounds WHERE status = 'active'")
        .fetchone()[0]
    )
    assert count == 1


# --- second-user access --------------------------------------------------------


def test_second_user_cannot_see_or_play_the_first_users_chains(app):
    ann, bo = app.test_client(), app.test_client()
    signup(ann)
    finish_a_chain(ann)
    signup(bo, email="bo@example.com", name="Bo")
    assert bo.get("/rounds/1").status_code == 404
    assert "APPLE" not in bo.get("/dashboard").get_data(as_text=True)
    post(bo, "/play/new", page="/play")
    play(bo, "apple", 0)  # Bo's moves only touch Bo's chain
    assert ann.get("/rounds/1").status_code == 200
    assert "Chains played</dt><dd>1" in ann.get("/dashboard").get_data(as_text=True)


# --- stale sessions -----------------------------------------------------------


def test_password_change_signs_out_other_sessions(app):
    laptop, phone = app.test_client(), app.test_client()
    signup(laptop)
    login(phone)
    assert phone.get("/dashboard").status_code == 200
    response = post(
        laptop,
        "/account",
        {
            "action": "password",
            "current_password": "correct horse",
            "new_password": "new secret 123",
        },
        page="/account",
    )
    assert response.status_code == 302
    assert laptop.get("/dashboard").status_code == 200  # this session stays in
    assert phone.get("/dashboard").status_code == 302  # the other one is stale
    logout(laptop)
    assert login(laptop, password="correct horse").status_code == 401
    assert login(laptop, password="new secret 123").status_code == 302


def test_old_session_cookie_does_not_work_after_logout(app):
    client = app.test_client()
    signup(client)
    saved = client.get_cookie("session").value  # an attacker copies the cookie
    logout(client)
    replay = app.test_client()
    replay.set_cookie("session", saved)
    assert replay.get("/dashboard").status_code == 302


def test_password_change_needs_the_current_password(client):
    signup(client)
    response = post(
        client,
        "/account",
        {"action": "password", "current_password": "wrong", "new_password": "new secret 123"},
        page="/account",
    )
    assert response.status_code == 400
    assert "Current password is incorrect." in response.get_data(as_text=True)


# --- account maintenance and persistence --------------------------------------


def test_display_name_change_shows_on_the_dashboard(client):
    signup(client)
    post(client, "/account", {"action": "name", "display_name": "  Ann   C. "}, page="/account")
    assert "Ann C.'s history" in client.get("/dashboard").get_data(as_text=True)
    too_long = post(
        client, "/account", {"action": "name", "display_name": "x" * 31}, page="/account"
    )
    assert too_long.status_code == 400


def test_history_survives_an_app_restart(app):
    client = app.test_client()
    signup(client)
    finish_a_chain(client)
    restarted = create_app({"TESTING": True, "DATABASE": app.config["DATABASE"]})
    fresh = restarted.test_client()
    login(fresh)
    assert "APPLE" in fresh.get("/dashboard").get_data(as_text=True)


def test_security_headers_are_sent(client):
    response = client.get("/")
    assert "script-src 'none'" in response.headers["Content-Security-Policy"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert token(client)  # pages carry a CSRF token
