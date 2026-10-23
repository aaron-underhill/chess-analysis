"""Download games from Chess.com's public API and turn them into Game fields.

Chess.com publishes every player's games for free, no login needed:

  /pub/player/{username}/games/archives  ->  a list of monthly archive URLs
  /pub/player/{username}/games/{YYYY}/{MM} ->  every game played that month

Docs: https://www.chess.com/news/view/published-data-api
"""

import re
from datetime import datetime, timezone

import requests

API_BASE = "https://api.chess.com/pub"

# Chess.com asks API users to identify themselves with a User-Agent.
HEADERS = {"User-Agent": "chess-analysis/0.1 (https://github.com/aaron-underhill/chess-analysis)"}

# Chess.com reports each side's outcome with a code. These codes mean a draw.
DRAW_CODES = {"agreed", "repetition", "stalemate", "insufficient", "50move", "timevsinsufficient"}

# How the game ended, from the losing side's code (or the draw code).
TERMINATIONS = {
    "checkmated": "checkmate",
    "resigned": "resignation",
    "timeout": "time",
    "abandoned": "abandoned",
    "agreed": "draw agreed",
    "repetition": "repetition",
    "stalemate": "stalemate",
    "insufficient": "insufficient material",
    "50move": "50-move rule",
    "timevsinsufficient": "time vs. insufficient material",
}

PGN_HEADER = re.compile(r'^\[(\w+) "(.*)"\]$', re.MULTILINE)


def get_json(url, session=None):
    """GET a Chess.com API URL and return the parsed JSON."""
    response = (session or requests).get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.json()


def archive_urls(username, session=None):
    """Monthly archive URLs for a player, oldest first."""
    data = get_json(f"{API_BASE}/player/{username.lower()}/games/archives", session)
    return data.get("archives", [])


def month_games(archive_url, session=None):
    """Every raw game in one monthly archive."""
    return get_json(archive_url, session).get("games", [])


def archive_month(archive_url):
    """The (year, month) an archive URL covers, e.g. .../games/2026/10 -> (2026, 10)."""
    year, month = archive_url.rstrip("/").split("/")[-2:]
    return int(year), int(month)


def pgn_headers(pgn):
    """The [Key "Value"] tags at the top of a PGN, as a dict."""
    return dict(PGN_HEADER.findall(pgn or ""))


def opening_name_from_url(eco_url):
    """Chess.com names openings in a URL slug. Turn it into readable text.

    ".../openings/Sicilian-Defense-Bowdler-Attack" -> "Sicilian Defense Bowdler Attack"
    Some slugs continue with the moves played ("...-3.Nf3"); those are dropped.
    """
    if not eco_url:
        return ""
    slug = eco_url.rstrip("/").split("/")[-1]
    slug = re.split(r"-\d+\.", slug)[0]  # cut at the first move number like "-3."
    return slug.replace("-", " ").strip()


def parse_game(raw, username):
    """Convert one raw Chess.com game into Game model fields.

    Returns None for games the app doesn't analyze (variants like Chess960,
    or games that somehow don't include the player).
    """
    if raw.get("rules", "chess") != "chess":
        return None

    me = username.lower()
    white, black = raw.get("white", {}), raw.get("black", {})
    if white.get("username", "").lower() == me:
        color, mine, theirs = "white", white, black
    elif black.get("username", "").lower() == me:
        color, mine, theirs = "black", black, white
    else:
        return None

    my_code, their_code = mine.get("result", ""), theirs.get("result", "")
    if my_code == "win":
        result, ending = "win", their_code
    elif my_code in DRAW_CODES:
        result, ending = "draw", my_code
    else:
        result, ending = "loss", my_code

    headers = pgn_headers(raw.get("pgn", ""))
    eco_url = headers.get("ECOUrl") or raw.get("eco", "")
    game_url = raw.get("url", "")

    return {
        "platform": "chesscom",
        "game_id": raw.get("uuid") or game_url.rstrip("/").split("/")[-1],
        "url": game_url,
        "played_at": datetime.fromtimestamp(raw["end_time"], tz=timezone.utc),
        "time_control": raw.get("time_control", ""),
        "speed": raw.get("time_class", ""),
        "color": color,
        "result": result,
        "termination": TERMINATIONS.get(ending, ending),
        "opponent": theirs.get("username", ""),
        "my_rating": mine.get("rating"),
        "opponent_rating": theirs.get("rating"),
        "eco": headers.get("ECO", "")[:3],
        "opening_name": opening_name_from_url(eco_url)[:200],
        "pgn": raw.get("pgn", ""),
    }
