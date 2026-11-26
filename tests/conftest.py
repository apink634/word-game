import re

import pytest

from wordgame import create_app, play


class FixedPicker:
    """Predictable picks: APPLE first, then the alphabetically first candidate.

    So a test chain always goes APPLE -> EAGLE -> EARTH -> HEART -> ...
    """

    def pick(self, words):
        return "apple" if "apple" in words else sorted(words)[0]


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(play, "choose_picker", lambda _mode: FixedPicker())
    # CSRF stays ON in tests: every form post must carry a real token.
    return create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.sqlite3")})


@pytest.fixture
def client(app):
    return app.test_client()


def token(client, path="/login"):
    """Read the CSRF token from a real page, as a browser would."""
    html = client.get(path).get_data(as_text=True)
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


def post(client, url, data=None, page="/login", **kwargs):
    return client.post(url, data={"csrf_token": token(client, page), **(data or {})}, **kwargs)


def signup(client, email="ann@example.com", password="correct horse", name="Ann"):
    return post(
        client,
        "/signup",
        {"email": email, "password": password, "display_name": name},
        page="/signup",
    )


def login(client, email="ann@example.com", password="correct horse"):
    return post(client, "/login", {"email": email, "password": password})


def logout(client):
    return post(client, "/logout", page="/account")
