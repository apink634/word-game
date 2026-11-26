# Word Chain (Word Game)

A small, secure word game for IS218-003. Solve a clue to find a 5-letter word (3 guesses), and then the next word starts with the last letter of that one. Keep the chain going as long as you can. A hint shows a word's last letter but costs a guess. Finished chains are saved to your private history.

**Project record:** https://apink634.github.io/word-game/ ([source](docs/index.md))

## Run it locally

Needs Python 3.12 or newer.

```bash
pip install -r requirements.txt
python -m flask --app wordgame run
```

Open http://127.0.0.1:5000, create an account and play.

Optional settings (environment variables):

| Variable | Default | Purpose |
|---|---|---|
| `WORDGAME_SECRET_KEY` | random each start | Set it so logins survive a restart |
| `WORDGAME_DATABASE` | `instance/wordchain.sqlite3` | Where the SQLite file lives |
| `WORDGAME_PICKER` | `random` | `daily` gives everyone the same chain each day |
| `WORDGAME_SECURE_COOKIES` | off | Set to `1` when served over HTTPS |

## Check it

```bash
python -m pytest -q
ruff check wordgame tests
ruff format --check wordgame tests
```

## Layout

- `wordgame/game.py`: pure chain rules (no web, no database)
- `wordgame/pickers.py`: the pattern experiment (function vs Strategy)
- `wordgame/db.py`: SQLite storage
- `wordgame/auth.py`: accounts, sessions and password changes
- `wordgame/play.py`: play, hints and private history
- `wordgame/data/`: word lists and AI-written hints. The accepted-guess list is the 5-letter words from GCIDE (GNU Collaborative International Dictionary of English), taken from the MIT-licensed [`english-words`](https://pypi.org/project/english-words/) package.
- `tests/`: pytest
