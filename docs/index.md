# Word Game — Project Record & Programming Research Site

**IS218-003 · Creative Project · Current stage: Review 1 (Plan)**

- Repository: https://github.com/apink634/word-game
- This site: https://apink634.github.io/word-game/
- My career research site: https://apink634.github.io/career-research/

> Research sites are due at Plan, not finished applications. Everything below is a plan unless marked **observed**.

---

## Project and current status

| | |
|---|---|
| **Research question** | What is the smallest word-guessing game I can build that is secure, saves each player's history privately, and is easy to test? |
| **Audience** | Casual players who want a quick daily brain break |
| **Main task** | Play one round: guess a 5-letter word in up to 6 tries |
| **Dream** | A word game with daily puzzles, streaks, themed word packs and friend leaderboards |
| **Promise** | A signed-in player plays one round. The result is saved, the player sees past rounds and win rate on a private dashboard, and they can change their display name and password. |
| **Experiment** | AI-written one-line hints (see below) |
| **Stack** | Python 3.12, Flask, SQLite, Flask-Login, Werkzeug password hashing, Flask-WTF (CSRF), pytest |
| **Why this stack** | Matches the course example, so I have a working reference. Python is my strongest language. SQLite needs no separate server. |
| **Deferred features** | Daily shared puzzle, streaks, leaderboards, themed packs, mobile layout |
| **Setup** | Not yet; no code at Plan stage |
| **Checks** | None run yet. All checks below are **planned**. |

---

## 1 · Plan

### Evidence and assumptions

**Facts (from sources):**
- Passwords should be stored with a slow, salted hash, never in plain text. *(OWASP Password Storage Cheat Sheet)*
- Werkzeug provides `generate_password_hash` and `check_password_hash` for this. *(Werkzeug docs)*
- Flask-WTF adds CSRF protection to forms. *(Flask-WTF docs)*
- Flask-Login manages signed-in user sessions. *(Flask-Login docs)*

**Interpretations (my reading):**
- Keeping game rules separate from Flask will make them the easiest part to test.

**Assumptions (not yet checked):**
- A Wordle-style round is short enough (2–5 minutes) that players will finish it in one sitting.
- A list of a few hundred common 5-letter words is enough for this term.
- Players care about seeing their own history and win rate.

### Two approaches compared

| | A: Word guessing game | B: Flashcard quizzer |
|---|---|---|
| Audience | Casual players | College students |
| Core logic | Fixed rules: score a guess, win/lose | Right/wrong per card |
| Testability | High: same input, same output | High, but content must be checked |
| Content needed | One word list | Questions and answers for every deck |
| Scope risk | Low | Medium: user-made decks would add a whole workflow |
| AI experiment risk | Low: a bad hint doesn't break the game | Higher: a wrong card teaches wrong facts |

**Decision:** Word guessing game.
**Reason:** Small, fixed rules are easiest to finish and test well, and a failed AI experiment does the least damage.
**Tradeoff:** Less directly useful than a study tool, and the idea is familiar rather than original.

### Five stories

1. **Create an account.** As a new player, I want to sign up with an email and password so I can keep my own history.
   - Success: password stored hashed; I'm signed in after sign-up.
   - Failure: duplicate email is rejected; weak or empty password is rejected.
2. **Play a round.** As a signed-in player, I want to guess a 5-letter word in up to 6 tries and see which letters are correct, misplaced or absent.
   - Success: the server scores each guess; the round ends on a win or after 6 guesses.
   - Failure: guesses that aren't 5 letters or aren't in the word list are rejected; the answer is never sent to the browser before the round ends.
3. **Save my result.** As a player, I want each finished round saved so my progress isn't lost.
   - Success: the round is stored with my user ID, word, guesses used and win/loss, and is still there after logging out and back in.
   - Failure: an unfinished round is not saved as a result; a signed-out user can't save.
4. **See my private dashboard.** As a player, I want to see my past rounds and win rate.
   - Success: a new account shows an empty dashboard; my rounds appear newest first.
   - Failure: player B can't see or open player A's rounds, even by changing the URL.
5. **Update my account.** As a player, I want to change my display name and password.
   - Success: the new display name shows on my dashboard; the new password works.
   - Failure: a password change without the correct current password is rejected; after a password change, my old sessions are signed out.

### Architecture sketch

```
Browser (HTML forms)
      │
      ▼
routes.py ──────── handles requests, checks login and ownership
   │      │
   │      ▼
   │   auth.py ─── sign up, log in, log out, password change
   │
   ▼
game.py ────────── pure game rules: score a guess, decide win/lose
   │                (no database, no Flask, so it's easy to test)
   ▼
db.py ──────────── saves and loads users and rounds (SQLite)

tests/ ─────────── pytest: game rules, auth, ownership, persistence
```

**Where the core rules live:** `game.py`. It takes a guess and an answer and returns the result. It knows nothing about the web or the database.

**Data sketch:**
- `users`: id, email (unique), display_name, password_hash, created_at
- `rounds`: id, user_id → users.id, word, guesses_used, won, finished_at
- `words.txt`: allowed 5-letter words (a file, not a table)

### Pattern experiment (planned)

- **Design problem:** how the game picks the answer word. Later I may want a daily word instead of a random one.
- **Approach 1, function-based:** a plain function `pick_word(words, rng)`.
- **Approach 2, Strategy pattern:** a `WordPicker` interface with `RandomPicker` and `DailyPicker` classes.
- **Planned comparison:** lines of code, how easy each is to test with a fixed seed or date, and how much code changes when I add the daily option.
- **Prediction:** the function will be simpler for now; the Strategy pattern only pays off if I actually add the daily word.

### AI experiment (planned)

- **Idea:** use AI to write a one-line hint for each answer word.
- **Prediction:** most hints will be fine, but some will give the answer away or be wrong.
- **How I'll check it:** generate hints for 20 words and judge each one: helpful, gives the answer away, or wrong.
- **Stopping point:** if more than 4 of 20 hints are bad after two rounds of prompt changes, stop.
- **Fallback:** hand-written hints for a fixed list of 50 words.
- **Status:** planned, not attempted.

### Investigating after peer review: make the mechanic less like Wordle

A reviewer said the game feels too close to Wordle ([issue #1](https://github.com/apink634/word-game/issues/1)). I'll test **one** change that fits my existing AI hint experiment:

- **Change:** hints become a limited ability. A player gets 2 hints per round and chooses when to use them, and each hint costs one guess.
- **Why this one:** it reuses the hint work I already planned, adds a real decision for the player, and doesn't add a new workflow to the promise.
- **Check (planned):** a classmate plays a paper or prototype round and says whether it feels different from Wordle.
- **Deferred to Dream:** story progression, themed word sets, connected rounds and timed streaks. These are good ideas but would add scope.

---

## Sources

| Source | Date checked | What I used it for |
|---|---|---|
| [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html) | 2026-11-12 | Why passwords must be hashed |
| [Werkzeug security utilities](https://werkzeug.palletsprojects.com/en/stable/utils/#module-werkzeug.security) | 2026-11-12 | Password hashing functions |
| [Flask-Login docs](https://flask-login.readthedocs.io/) | 2026-11-12 | User sessions |
| [Flask-WTF CSRF docs](https://flask-wtf.readthedocs.io/en/stable/csrf/) | 2026-11-12 | CSRF protection on forms |
| [Flask docs](https://flask.palletsprojects.com/) | 2026-11-12 | App structure |
| [Course example game](https://kaw393939.github.io/is218-studio/examples/full-game.html) | 2026-11-12 | Reference stack and features |

---

## AI assistance

- **Tool:** Claude (Anthropic)
- **What it helped with:** drafting the concept comparison, the five stories, the architecture sketch and the structure of this record.
- **What I changed:** changed game to be less similar to wordle
- **How I verified it:** I opened each source above and confirmed it says what this page claims (fill in dates once done). Claims I couldn't confirm: none

---

## Partner review

| Reviewer | Date | What they tried | Feedback | Issue | Decision |
|---|---|---|---|---|---|
| dhruvi0805 | 2026-11-12 | Read the concept and plan | The game feels too similar to Wordle; suggested clues/abilities, story, themes, connected rounds | [#1](https://github.com/apink634/word-game/issues/1) | **Investigate**, because a mechanic change is worth testing but I need to keep scope small. Planned one change (limited hints as an ability), and deferred the rest to Dream. Issue stays open until I test it. |

---

## 2 · First working slice — *not due yet*
## 3 · Integrated build — *not due yet*
## 4 · Improve and hand off — *not due yet*
