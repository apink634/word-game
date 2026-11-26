# Word Chain (Word Game) — Project Record & Programming Research Site

**IS218-003 · Creative Project · Current stage: Review 3 (Integrated build, runs locally)**

- Repository: https://github.com/apink634/word-game
- This site: https://apink634.github.io/word-game/
- My career research site: https://apink634.github.io/career-research/

> Checks are marked **planned** or **observed**. Nothing is marked observed unless it was actually run.

---

## Project and current status

| | |
|---|---|
| **Research question** | What is the smallest word-guessing game I can build that is secure, saves each player's history privately, and is easy to test? |
| **Audience** | Casual players who want a quick daily brain break |
| **Main task** | Play one chain: solve a clue (3 guesses per word); each next word starts with the last letter of the one before. *(Changed at Review 3 from a Wordle-style round; see Review 3.)* |
| **Dream** | A word game with daily puzzles, streaks, themed word packs and friend leaderboards |
| **Promise** | A signed-in player plays one chain. The result (chain length and words) is saved, the player sees past chains, best and average on a private dashboard, and they can change their display name and password. |
| **Experiment** | AI-written one-line hints (see below) |
| **Stack** | Python 3.12, Flask, SQLite, Flask-Login, Werkzeug password hashing, Flask-WTF (CSRF), pytest |
| **Why this stack** | Matches the course example, so I have a working reference. Python is my strongest language. SQLite needs no separate server. |
| **Deferred features** | Daily shared puzzle, streaks, leaderboards, themed packs, mobile layout |
| **Setup** | See the [README](https://github.com/apink634/word-game#readme); runs locally |
| **Checks** | See Review 3: automated tests and my own play tests |

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
   - Success: the server scores each guess; the round ends on a win or after 6 guesses. I can use up to 2 hints; each hint uses up one guess. *(Added after [issue #1](https://github.com/apink634/word-game/issues/1).)*
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
- `rounds`: id, user_id → users.id, word, guesses_used, hints_used, won, finished_at
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
- **How I verified it:** I opened each source above and confirmed it says what this page claims. Claims I couldn't confirm: none

---

## Partner review

| Reviewer | Date | What they tried | Feedback | Issue | Decision |
|---|---|---|---|---|---|
| dhruvi0805 | 2026-11-12 | Read the concept and plan | The game feels too similar to Wordle; suggested clues/abilities, story, themes, connected rounds | [#1](https://github.com/apink634/word-game/issues/1) | **Investigate**, because a mechanic change is worth testing but I need to keep scope small. Planned one change (limited hints as an ability), and deferred the rest to Dream. **Change (2026-11-19):** hints added to story 2 and the `rounds` data sketch. **Verification:** not run. **Reviewer retry:** not yet; issue stays open until a classmate plays a prototype round. |

---

## 2 · Plan/SPEC checkpoint (Review 2)

> Per the Nov 19 clarification, this checkpoint is the plan/SPEC. **No working app exists yet**, and every check below is **planned, not run**.

### What I chose to build

A Flask word-guessing game. A player signs up or signs in, plays one round (5-letter word, 6 guesses, up to 2 hints that each cost a guess), the finished round is saved to SQLite, the player sees past rounds and win rate on a private dashboard, changes their display name or password, and signs out. Game rules live in `game.py` with no Flask or database code, so they're the first thing I'll test.

**Changed since Review 1:** hints became a limited ability after peer review ([issue #1](https://github.com/apink634/word-game/issues/1)), and `rounds` now stores `hints_used`.

### The one check I'll run first when the app is ready

**Duplicate-letter scoring** (a unit test on `game.py`). Answer `CRANE`, guess `EERIE` → **absent, absent, present, absent, correct**. Only one `E` is in the answer, and it's already matched in the last position, so the first two `E`s must be absent. This is the rule simple scoring code usually gets wrong. Status: **planned, not run.**

### Other planned checks

| Story | Check | Type | Status |
|---|---|---|---|
| 1 · Account | Stored password is a hash, not the plain text; a duplicate email is rejected | integration (pytest + Flask test client) | planned |
| 2 · Play | A 4-letter or non-list guess is rejected and doesn't use up a guess; the answer isn't in the page before the round ends | integration | planned |
| 2 · Hints | A third hint is refused; each hint reduces the guesses left by 1 | unit | planned |
| 3 · Save | A finished round is still there after logging out and in; an unfinished round isn't saved | integration | planned |
| 4 · Dashboard | Player B gets a 404 when opening player A's round by URL | integration | planned |
| 5 · Account update | A password change without the correct current password is rejected | integration | planned |

### Changed / Checked / Next

- **Changed:** Moved the record to the Review 2 plan/SPEC stage, added hints to the SPEC after issue #1, and named the first check.
- **Checked:** Nothing run yet; all checks are planned because there's no code.
- **Next:** Build `game.py` with the duplicate-letter test first, then sign up → play → save → sign out.
## 3 · Integrated build (Review 3)

**What's built:** *Word Chain*, a Flask word game that runs locally. Sign up or log in → play a chain (solve a clue in 3 guesses; the next word starts with the last letter of the one you solved) → the finished chain is saved to SQLite → a private history dashboard shows past chains, best and average → change display name or password → log out.

**Run it:** see the [README](https://github.com/apink634/word-game#readme) (`pip install -r requirements.txt`, then `python -m flask --app wordgame run`).

### The big decision this stage: from Wordle-style to Word Chain

I first built the Plan as written: guess a 5-letter word in 6 tries with green, yellow and gray tiles, plus 2 hints. When I played it myself, two problems showed up:
1. **Most real words were rejected**, because the guess list was too small (616 words). I fixed that with a 6,801-word dictionary list.
2. **It still felt too much like Wordle**, which was exactly Dhruvi's feedback in [issue #1](https://github.com/apink634/word-game/issues/1). Adding hints wasn't enough to change that.

So I changed the core mechanic to **Word Chain**, which is one of Dhruvi's own suggestions ("connected rounds"):
- Each word comes from a **clue** (these are the AI-written clues from my experiment). You know the first letter and get **3 guesses**.
- The **next word starts with the last letter** of the one you solved.
- A **hint reveals the last letter and costs a guess**. That keeps the "hints cost a try" idea and adds strategy, because the last letter tells you where the chain goes.
- **Score = chain length.** The chain ends after 3 misses on one word, or when every possible next word has been used.

**What carried over unchanged:** accounts, sessions, CSRF, ownership checks, duplicate-move protection, the dashboard idea, and the Strategy pattern (which now picks each next word).
**What I dropped:** the color-tile scoring. So my Review 2 named check (CRANE / EERIE duplicate letters) no longer applies. The first check is now "every answer can be continued by another answer" (tested).

### How it's built

| File | Job |
|---|---|
| `wordgame/game.py` | Pure chain rules: guesses, the chain rule, 3 misses, hints costing a guess. No Flask, no database. |
| `wordgame/pickers.py` | Pattern experiment: the function picker and the Strategy picker, plus `next_word` for the chain. |
| `wordgame/db.py` | SQLite users and chains (each chain stored as JSON plus a move counter). All queries are parameterized. |
| `wordgame/auth.py` | Sign up, log in and out, display name and password changes, session versioning. |
| `wordgame/play.py` | Play, hint, private history, chain pages, ownership checks. |
| `wordgame/data/` | 108 answer words with AI-written clues; 6,801 accepted guesses (GCIDE dictionary, via the MIT-licensed `english-words` package). |
| `tests/` | 45 pytest tests. CI runs ruff and pytest on every push and PR. |

**Security decisions**
- Passwords are hashed with Werkzeug (scrypt). A wrong password and an unknown email get the same reply.
- CSRF tokens are required on every form (Flask-WTF, kept on in tests too).
- **Session versioning:** changing the password or logging out bumps a version number, so an old or copied session cookie stops working.
- **Duplicate moves and results:** every form carries the move count the player saw. The database only saves the move if the chain is still at that count, so a double click, back button or second tab can't count a guess or a result twice. Only one unfinished chain per player is allowed (unique index).
- **Ownership:** another player's chain returns 404. The current answer is never sent to the page, only its clue and first letter.
- No JavaScript at all, with a strict Content-Security-Policy. Words are picked with the OS's secure random source.

### Review 3 checks

| Check the assignment asks for | How it's tested | Status |
|---|---|---|
| Wrong passwords | Wrong password and unknown email both get 401 and the same message; still logged out | **observed** (automated) |
| Second-user access | User B gets 404 on user A's chain and doesn't see it in their history; B's moves only change B's chain | **observed** (automated) |
| Stale sessions | After a password change, the other device is logged out; after logout, a copied cookie is rejected; the old password fails | **observed** (automated) |
| Duplicate result requests | Re-sending a solving guess counts once; re-sending the final move records one result; double-clicking "new chain" makes one chain | **observed** (automated) |
| Persistence | History is still there after the app restarts on the same database | **observed** (automated) |
| Chain rules | Next word follows the last letter, no reused words, 3 misses end it, hint costs a guess, every answer can be continued | **observed** (automated) |
| Tests on my own laptop (Windows, Python 3.14) | `python -m pytest -q` passed (44 tests on the first version) | **observed** 2026-11-26 |
| My play test of the first version | Real words rejected and too much like Wordle, which led to the bigger word list and the switch to Word Chain | **observed** 2026-11-26 |
| My play test of Word Chain, keyboard only | `python -m pytest -q` → 45 passed; I played a chain of 4 with the keyboard. It felt different from Wordle, which was the goal of the change. | **observed** 2026-11-26 |

### Pattern experiment result

**Problem:** how the game picks words: the first word, and now each next word in the chain.

| | Function `pick_word` | Strategy (`RandomPicker`, `DailyPicker`) |
|---|---|---|
| Code lines | 2 | 15 (protocol 2, random 5, daily 6, chooser 2) |
| Testing | Easy with a seeded `Random` | Just as easy: a seeded `Random` or a fixed date |
| Adding a daily chain | Needs a second function plus an `if` wherever a word is picked (first word **and** every next word) | One new class. `play.py` and `next_word` just call `picker.pick(...)` |

**Result:** the function is simpler for random-only. But Word Chain picks a word at every link, and I added a daily option, so the Strategy version kept the routes unchanged. The app uses it (set `WORDGAME_PICKER=daily` for one shared chain per day). Both versions stay in `pickers.py` for comparison.

### AI experiment result (clues)

**Setup:** an AI assistant (Claude) wrote a one-line clue for each answer word (`wordgame/data/hints.json`). In Word Chain, these clues are now the main way you find each word. An automated rule hides any clue that contains its own answer, and the game then shows a "5-letter word ending in …" clue instead.

**Automated check (observed):** 1 clue gives the answer away. TOAST's clue mentions a "toaster", and the game refuses to show it (tested).

**My judgment of 20 clues (2026-11-26):**

| # | Word | AI clue | Automated flag | My judgment |
|---|---|---|---|---|
| 1 | APPLE | A crunchy fruit that keeps the doctor away in an old saying. |  | helpful |
| 2 | BRAIN | The organ you're using to solve this puzzle. |  | helpful |
| 3 | CHAIR | Furniture with four legs and a back, made for sitting. |  | gives it away |
| 4 | CRANE | A tall bird on long legs, or a machine that lifts heavy loads. |  | helpful |
| 5 | DREAM | A story your mind tells while you sleep. |  | helpful |
| 6 | EAGLE | A large bird of prey and a U.S. national symbol. |  | gives it away |
| 7 | FROST | Thin ice that forms on grass on cold mornings. |  | helpful |
| 8 | HEART | It pumps blood through your body. |  | gives it away |
| 9 | KNIFE | A kitchen tool with a sharp blade. |  | gives it away |
| 10 | LIGHT | What a lamp gives off; the opposite of dark. |  | gives it away |
| 11 | MOUSE | A small rodent, or the thing you click with. |  | helpful |
| 12 | NIGHT | The dark hours between sunset and sunrise. |  | helpful |
| 13 | OLIVE | A small green or black fruit pressed for oil. |  | helpful |
| 14 | QUEEN | A female ruler, or the most powerful chess piece. |  | helpful |
| 15 | RADIO | A device for listening to broadcasts and stations. |  | helpful |
| 16 | ROBOT | A machine that can carry out tasks on its own. |  | helpful |
| 17 | SPACE | Where astronauts and stars are. |  | helpful |
| 18 | TABLE | Furniture with a flat top where you eat. |  | helpful |
| 19 | TOAST | Bread browned in a toaster, or a speech before a drink. | **gives it away** (contains the word) | helpful |
| 20 | WORLD | All the countries and people on the planet. |  | helpful |


**Result:** 15 helpful, **5 give it away** (CHAIR, EAGLE, HEART, KNIFE, LIGHT), 0 wrong.
- **That's over my stopping line** (more than 4 of 20), so the first-attempt AI clues don't pass. Next step from the Plan: one stricter prompt ("describe it indirectly; don't name its main use or most famous fact"), or hand-written clues if that fails.
- **The automated rule and I disagreed once:** I judged TOAST helpful, but the rule hides it because it mentions "toaster". The rule catches word leaks; only a person catches clues that are simply too obvious.
- **In Word Chain this matters less than before:** a too-easy clue makes one link easy, but the chain still depends on every other word. I haven't judged the 58 clues added for Word Chain yet.

### Peer feedback loop (issue #1)

Issue (too similar to Wordle) → decision at Review 2: **Investigate** (try limited hints) → **verification by me at Review 3:** with hints, it still felt like Wordle → **new decision: Accept** → **change:** core mechanic rebuilt as Word Chain, using Dhruvi's "connected rounds" idea → **reviewer retry:** not yet; Dhruvi plays one chain and says whether it now feels different.

### Presentation

A plain, readable page: the chain so far shown as word badges, then the next word as a pattern like `E _ _ _ _`, with the clue under it. The "How to play" box is open until you start. There's no JavaScript, so everything works with Tab and Enter. The research site stays one record page, cross-linked to my career site.

### AI assistance (Review 3)

Claude wrote most of the code and tests from my SPEC and wrote the clues. I chose the game, judged the first version by playing it, decided to switch to Word Chain and chose the rules, judged 20 clues, and ran the tests on my laptop.

### Changed / Checked / Next

- **Changed:** Built the full game; after my play test, enlarged the word list and switched the mechanic to Word Chain (issue #1); ran the pattern and AI experiments.
- **Checked:** 45 automated tests (wrong passwords, second user, stale sessions, duplicate results, persistence, chain rules); my play tests of both versions (Word Chain: a chain of 4, keyboard only); AI clues: 15/20 helpful.
- **Next:** Dhruvi retries for issue #1; rewrite the 5 too-easy clues and judge the new ones.

## 4 · Improve and hand off — *not due yet*
