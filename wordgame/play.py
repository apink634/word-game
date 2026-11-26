"""Play a chain, use hints, and see your private history."""

import json

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from wordgame import db, game, words
from wordgame.pickers import choose_picker, next_word

bp = Blueprint("play", __name__)


def _state(row) -> game.ChainState:
    return game.ChainState.from_dict(json.loads(row["state"]))


def clue_for(word: str) -> str:
    """The AI-written clue, or a safe fallback if it would give the word away."""
    return words.safe_hint(word) or f"A {len(word)}-letter word ending in {word[-1].upper()}."


def _expected_moves() -> int:
    try:
        return int(request.form.get("expected_moves", ""))
    except ValueError:
        abort(400, description="That form is out of date. Reload the page.")


def _picker():
    return choose_picker(current_app.config["WORD_PICKER"])


@bp.get("/play")
@login_required
def play():
    row = db.active_round(current_user.id)
    if row is None:
        return render_template("play.html", round=None, tries=game.GUESSES_PER_LINK)
    state = _state(row)
    link = state.current
    # The current answer is never sent to the page; only its clue and first letter.
    return render_template(
        "play.html",
        round=row,
        state=state,
        solved=[lk.word for lk in state.links if lk.solved],
        clue=clue_for(link.word),
        first_letter=link.word[0].upper(),
        last_letter=link.word[-1].upper() if link.hinted else None,
        wrong=[g.upper() for g in link.guesses],
        tries_left=link.tries_left,
        can_hint=state.can_hint(),
        tries=game.GUESSES_PER_LINK,
    )


@bp.post("/play/new")
@login_required
def new_round():
    first = _picker().pick(words.answers())
    db.start_round(current_user.id, game.ChainState.start(first).as_dict())
    return redirect(url_for("play.play"))


def _move(apply):
    """Apply one move to the active chain and save it exactly once."""
    row = db.active_round(current_user.id)
    if row is None:
        flash("Start a new chain first.")
        return redirect(url_for("play.play"))
    state = _state(row)
    expected = _expected_moves()
    if expected != state.moves:
        flash("That move was already counted.")
        return redirect(url_for("play.play"))
    try:
        message = apply(state)
    except game.InvalidGuess as error:
        flash(str(error))
        return redirect(url_for("play.play"))
    if not db.save_progress(row["id"], current_user.id, expected, state, state.ended):
        flash("That move was already counted.")
        return redirect(url_for("play.play"))
    if message:
        flash(message)
    if state.ended:
        return redirect(url_for("play.round_detail", round_id=row["id"]))
    return redirect(url_for("play.play"))


@bp.post("/play/guess")
@login_required
def guess():
    raw = request.form.get("guess", "")

    def apply(state: game.ChainState) -> str:
        word = game.normalize(raw, words.allowed(), state.current.word[0])
        if state.guess(word):
            solved = word.upper()
            state.add_link(next_word(_picker(), words.answers(), word[-1], state.used_words))
            if state.ended:
                return f"{solved} ✓ — you've used every word that could come next. Chain complete!"
            return f"{solved} ✓ Chain: {state.length}. Next word starts with {word[-1].upper()}."
        if state.ended:
            return f"Out of guesses. The word was {state.current.word.upper()}."
        return f"Not {word.upper()}. {state.current.tries_left} left for this link."

    return _move(apply)


@bp.post("/play/hint")
@login_required
def hint():
    return _move(lambda state: f"It ends with {state.use_hint().upper()} (that cost a guess).")


@bp.get("/dashboard")
@login_required
def dashboard():
    rows = db.finished_rounds(current_user.id)
    lengths = [row["chain_length"] for row in rows]
    stats = {
        "played": len(rows),
        "best": max(lengths, default=0),
        "average": round(sum(lengths) / len(lengths), 1) if lengths else None,
    }
    chains = [
        {"id": row["id"], "length": row["chain_length"], "words": _solved_words(row)}
        for row in rows
    ]
    return render_template(
        "dashboard.html", chains=chains, stats=stats, active=db.active_round(current_user.id)
    )


def _solved_words(row) -> list[str]:
    return [link.word.upper() for link in _state(row).links if link.solved]


@bp.get("/rounds/<int:round_id>")
@login_required
def round_detail(round_id: int):
    row = db.round_for_user(round_id, current_user.id)
    if row is None:
        abort(404)  # someone else's chain looks exactly like a missing one
    if row["status"] == "active":
        return redirect(url_for("play.play"))
    state = _state(row)
    return render_template("round.html", round=row, state=state, clue_for=clue_for)
