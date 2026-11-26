"""Pattern experiment: how the game picks the next answer word.

Approach 1 is a plain function. Approach 2 is the Strategy pattern. Both are
kept so they can be compared; the app uses whichever ``choose_picker`` returns.
In Word Chain, the picker chooses from the words that can legally come next
(they start with the right letter and haven't been used yet).
See docs/index.md, "Pattern experiment result".
"""

import random
from datetime import date
from typing import Protocol

# --- Approach 1: function ------------------------------------------------------


def pick_word(words: list[str], rng: random.Random) -> str:
    """Pick a random word. Tests pass a seeded Random for a fixed result."""
    return rng.choice(words)


# --- Approach 2: Strategy pattern ---------------------------------------------


class WordPicker(Protocol):
    """Anything that can choose a word from a list of candidates."""

    def pick(self, words: list[str]) -> str:
        """Return one word from ``words``."""


class RandomPicker:
    """A different random word each time."""

    def __init__(self, rng: random.Random | None = None) -> None:
        # SystemRandom uses the OS's secure source, so players can't predict the answer.
        self.rng = rng or random.SystemRandom()

    def pick(self, words: list[str]) -> str:
        return self.rng.choice(words)


class DailyPicker:
    """The same choices for everyone on a given day: a daily chain."""

    def __init__(self, today: date | None = None) -> None:
        self.today = today

    def pick(self, words: list[str]) -> str:
        day = self.today or date.today()
        ordered = sorted(words)
        return ordered[day.toordinal() % len(ordered)]


def choose_picker(mode: str) -> WordPicker:
    """Pick the strategy from settings ("random" or "daily")."""
    return DailyPicker() if mode == "daily" else RandomPicker()


def next_word(picker: WordPicker, answers: list[str], letter: str, used: set[str]) -> str | None:
    """The next chain word: starts with ``letter`` and isn't used yet; None if none left."""
    candidates = [w for w in answers if w[0] == letter and w not in used]
    return picker.pick(candidates) if candidates else None
