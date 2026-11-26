"""Pure game rules for Word Chain: no Flask, no database.

Each link shows a clue and the answer's first letter. The player has 3 guesses.
The next answer starts with the last letter of the one just solved, so the
words form a chain (APPLE -> EAGLE -> EARTH -> H...). Missing a link 3 times
ends the chain; the score is how many links were solved.

A hint reveals the answer's last letter (so you can see where the chain goes
next) and costs one guess, the "hints cost a try" idea from issue #1.
"""

from dataclasses import dataclass, field

WORD_LENGTH = 5
GUESSES_PER_LINK = 3


class InvalidGuess(ValueError):
    """The guess can't be judged; it must not use up a guess."""


def normalize(guess: str, allowed: set[str] | frozenset[str], first_letter: str) -> str:
    """Clean a submitted guess, or raise InvalidGuess with a reason to show."""
    word = (guess or "").strip().lower()
    if len(word) != WORD_LENGTH or not word.isalpha() or not word.isascii():
        raise InvalidGuess(f"Enter a {WORD_LENGTH}-letter word using A–Z.")
    if not word.startswith(first_letter):
        raise InvalidGuess(f"This link's word starts with {first_letter.upper()}.")
    if word not in allowed:
        raise InvalidGuess(f"“{word.upper()}” isn't in the dictionary. Try another real word.")
    return word


@dataclass
class Link:
    """One word in the chain and what the player did on it."""

    word: str
    guesses: list[str] = field(default_factory=list)
    hinted: bool = False

    @property
    def solved(self) -> bool:
        return bool(self.guesses) and self.guesses[-1] == self.word

    @property
    def tries_used(self) -> int:
        return len(self.guesses) + int(self.hinted)

    @property
    def failed(self) -> bool:
        return not self.solved and self.tries_used >= GUESSES_PER_LINK

    @property
    def tries_left(self) -> int:
        return max(GUESSES_PER_LINK - self.tries_used, 0)

    def as_dict(self) -> dict:
        return {"word": self.word, "guesses": self.guesses, "hinted": self.hinted}


@dataclass
class ChainState:
    """A whole chain. ``links[-1]`` is the link being played."""

    links: list[Link]
    ended: bool = False

    @classmethod
    def start(cls, first_word: str) -> "ChainState":
        return cls(links=[Link(first_word)])

    @classmethod
    def from_dict(cls, data: dict) -> "ChainState":
        return cls(links=[Link(**link) for link in data["links"]], ended=data["ended"])

    def as_dict(self) -> dict:
        return {"links": [link.as_dict() for link in self.links], "ended": self.ended}

    @property
    def current(self) -> Link:
        return self.links[-1]

    @property
    def length(self) -> int:
        """The score: how many links were solved."""
        return sum(link.solved for link in self.links)

    @property
    def moves(self) -> int:
        """Every guess and hint so far; used to spot repeated form submissions."""
        return sum(link.tries_used for link in self.links)

    @property
    def used_words(self) -> set[str]:
        return {link.word for link in self.links}

    def next_letter(self) -> str:
        return self.current.word[-1]

    def can_hint(self) -> bool:
        link = self.current
        return not self.ended and not link.hinted and link.tries_left > 1

    def guess(self, word: str) -> bool:
        """Record a valid guess; True if it solved the current link."""
        if self.ended:
            raise InvalidGuess("This chain is already over.")
        self.current.guesses.append(word)
        if self.current.failed:
            self.ended = True
        return self.current.solved

    def use_hint(self) -> str:
        """Reveal the current answer's last letter; costs one guess."""
        if not self.can_hint():
            raise InvalidGuess("No hint available for this link.")
        self.current.hinted = True
        return self.current.word[-1]

    def add_link(self, word: str | None) -> None:
        """Continue the chain with ``word``, or finish it if no word is left."""
        if word is None:
            self.ended = True  # every possible next word has been used
            return
        if word[0] != self.next_letter() or word in self.used_words:
            raise ValueError("next word must start with the last letter and be new")
        self.links.append(Link(word))
