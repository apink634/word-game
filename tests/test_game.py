"""Unit tests for the Word Chain rules, word data and the pattern experiment."""

import random
from datetime import date

import pytest

from wordgame import game, words
from wordgame.game import GUESSES_PER_LINK, ChainState, InvalidGuess
from wordgame.pickers import DailyPicker, RandomPicker, choose_picker, next_word, pick_word

# --- guesses ------------------------------------------------------------------


@pytest.mark.parametrize("bad", ["", "cat", "planet", "cr4ne", "héllo"])
def test_malformed_guesses_are_rejected(bad):
    with pytest.raises(InvalidGuess):
        game.normalize(bad, words.allowed(), "c")


def test_guess_must_start_with_the_links_first_letter():
    with pytest.raises(InvalidGuess, match="starts with E"):
        game.normalize("crane", words.allowed(), "e")


def test_guess_must_be_a_real_word():
    with pytest.raises(InvalidGuess, match="dictionary"):
        game.normalize("czzzz", words.allowed(), "c")


def test_valid_guess_is_cleaned():
    assert game.normalize("  CrAnE ", words.allowed(), "c") == "crane"


def test_common_real_words_are_accepted_as_guesses():
    # Found in Ann's first browser play test: real words were rejected.
    for word in ["plane", "stamp", "crate", "slate", "flint", "grove", "spice", "tribe"]:
        assert game.normalize(word, words.allowed(), word[0]) == word
    assert len(words.allowed()) > 5000


# --- the chain ----------------------------------------------------------------


def test_solving_a_link_and_continuing_the_chain():
    state = ChainState.start("apple")
    assert state.guess("apple") is True
    assert state.length == 1 and state.next_letter() == "e"
    state.add_link("eagle")
    assert state.current.word == "eagle" and not state.ended


def test_next_word_must_follow_the_chain_rule():
    state = ChainState.start("apple")
    state.guess("apple")
    with pytest.raises(ValueError):
        state.add_link("tiger")  # doesn't start with E
    with pytest.raises(ValueError):
        state.add_link("apple")  # can't reuse a word (and wrong letter)


def test_three_misses_end_the_chain():
    state = ChainState.start("apple")
    state.guess("apple")
    state.add_link("eagle")
    for word in ["earth", "eight"][: GUESSES_PER_LINK - 1]:
        assert state.guess(word) is False
        assert not state.ended
    state.guess("enemy")
    assert state.ended and state.length == 1
    with pytest.raises(InvalidGuess):
        state.guess("eagle")


def test_hint_shows_last_letter_and_costs_a_guess():
    state = ChainState.start("apple")
    assert state.use_hint() == "e"
    assert state.current.tries_left == GUESSES_PER_LINK - 1
    assert not state.can_hint()  # one hint per word
    with pytest.raises(InvalidGuess):
        state.use_hint()


def test_hint_never_uses_the_last_guess():
    state = ChainState.start("apple")
    state.guess("angel")
    state.guess("arrow")
    assert state.current.tries_left == 1 and not state.can_hint()


def test_chain_completes_when_no_next_word_is_left():
    state = ChainState.start("apple")
    state.guess("apple")
    state.add_link(None)
    assert state.ended and state.length == 1


def test_moves_count_every_guess_and_hint():
    state = ChainState.start("apple")
    state.use_hint()
    state.guess("angel")
    state.guess("apple")
    assert state.moves == 3


def test_state_round_trips_through_json():
    state = ChainState.start("apple")
    state.guess("apple")
    state.add_link("eagle")
    state.use_hint()
    assert ChainState.from_dict(state.as_dict()) == state


# --- word data ----------------------------------------------------------------


def test_word_data_is_consistent():
    answers = words.answers()
    assert len(answers) >= 100
    assert all(len(w) == 5 and w.isalpha() for w in answers)
    assert set(answers) <= words.allowed()
    assert set(words.hints()) == set(answers)


def test_every_answer_can_be_continued_by_another_answer():
    starts = {w[0] for w in words.answers()}
    stuck = [w for w in words.answers() if w[-1] not in starts]
    assert stuck == []


def test_clue_that_contains_the_answer_is_never_shown():
    # Found in the AI experiment: the clue for TOAST mentions a "toaster".
    assert "toast" in words.hints()["toast"].lower()
    assert words.safe_hint("toast") is None
    assert words.safe_hint("crane") is not None


# --- pattern experiment: function vs Strategy ---------------------------------

WORDS = ["apple", "beach", "crane"]


def test_function_picker_is_repeatable_with_a_seed():
    assert pick_word(WORDS, random.Random(7)) == pick_word(WORDS, random.Random(7))


def test_strategy_random_picker_is_repeatable_with_a_seed():
    assert RandomPicker(random.Random(7)).pick(WORDS) == pick_word(WORDS, random.Random(7))


def test_strategy_daily_picker_gives_one_choice_per_day():
    day = date(2026, 11, 30)
    assert DailyPicker(day).pick(WORDS) == DailyPicker(day).pick(WORDS)
    picks = {DailyPicker(date(2026, 11, d)).pick(WORDS) for d in range(1, 4)}
    assert picks == set(WORDS)


def test_next_word_uses_any_strategy_and_skips_used_words():
    answers = ["eagle", "earth", "eight", "tiger"]
    assert next_word(DailyPicker(date(2026, 1, 1)), answers, "e", {"eagle"}) in {"earth", "eight"}
    assert next_word(RandomPicker(), answers, "e", {"eagle", "earth", "eight"}) is None


def test_settings_choose_the_strategy():
    assert isinstance(choose_picker("daily"), DailyPicker)
    assert isinstance(choose_picker("random"), RandomPicker)
