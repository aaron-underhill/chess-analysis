# Chess Analysis

A Django web app that imports my online chess games and shows where I win, where I lose, and why: my most common openings, how each one goes for me, and (with Stockfish) the moves where games slip away.

> Work in progress. Built in stages; this README grows with each one.

## Plan

**Phase 1: Django core**
- [x] Project setup and `Game` model, with tests running on every push
- [ ] Import games from the Lichess / Chess.com public APIs (only new games each run)
- [ ] Dashboard: most common openings and win rate for each, results as White vs. Black, rating over time
- [ ] REST API endpoint for the stats
- [ ] Deploy live

**Phase 2: Stockfish analysis**
- [ ] Analyze each game once with Stockfish and store every move's evaluation
- [ ] Flag blunders and mistakes, and show which openings and game phases they come from

## How it's built

- **Django** for the database models, pages, and admin
- **python-chess** to read games (PGN) and talk to Stockfish
- **SQLite** locally
- **GitHub Actions** runs the test suite on every push

Each game is stored once, keyed by its platform and game ID, so re-running the importer only adds new games. Stockfish analysis will work the same way: each game is analyzed once and the results are saved, so pages never wait on the engine.

## Running locally

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser  # to log in to the admin
python manage.py runserver
```

Then open http://127.0.0.1:8000/admin.

Run the tests with:

```bash
python manage.py test
```
