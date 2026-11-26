"""Word lists and hints, loaded once from wordgame/data."""

import json
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).with_name("data")


@lru_cache
def answers() -> list[str]:
    """Words that can be the answer (each has a hint)."""
    return (DATA / "answers.txt").read_text(encoding="utf-8").split()


@lru_cache
def allowed() -> frozenset[str]:
    """Every word accepted as a guess (answers included)."""
    words = (DATA / "allowed.txt").read_text(encoding="utf-8").split()
    return frozenset(words) | frozenset(answers())


@lru_cache
def hints() -> dict[str, str]:
    """AI-written one-line hints (see the AI experiment in the record)."""
    return json.loads((DATA / "hints.json").read_text(encoding="utf-8"))


def safe_hint(answer: str) -> str | None:
    """The hint for ``answer``, or None if it would give the answer away."""
    hint = hints().get(answer)
    if not hint or answer.lower() in hint.lower():
        return None
    return hint
