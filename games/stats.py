"""Summary statistics about my games, shared by the dashboard and commands.

Each function takes an optional queryset, so the same stats work for all
games or for a filtered set (for example, only blitz games).
"""

from django.db.models import Count, Q

from .models import Game


def _all(games):
    return Game.objects.all() if games is None else games


def _with_win_rate(row):
    row["win_rate"] = round(100 * row["wins"] / row["games"], 1) if row["games"] else 0.0
    return row


RESULT_COUNTS = {
    "games": Count("id"),
    "wins": Count("id", filter=Q(result=Game.Result.WIN)),
    "losses": Count("id", filter=Q(result=Game.Result.LOSS)),
    "draws": Count("id", filter=Q(result=Game.Result.DRAW)),
}


def record(games=None):
    """Wins, losses, and draws, plus win rate, for a set of games."""
    return _with_win_rate(_all(games).aggregate(**RESULT_COUNTS))


def opening_stats(games=None, min_games=1):
    """Record for each opening, most-played first."""
    rows = (
        _all(games)
        .exclude(opening_name="")
        .values("opening_name", "eco")
        .annotate(**RESULT_COUNTS)
        .filter(games__gte=min_games)
        .order_by("-games", "opening_name")
    )
    # One row per opening name, even if Chess.com tagged it with more than
    # one ECO code.
    merged = {}
    for row in rows:
        name = row["opening_name"]
        if name in merged:
            for key in ("games", "wins", "losses", "draws"):
                merged[name][key] += row[key]
        else:
            merged[name] = dict(row)
    result = sorted(merged.values(), key=lambda r: (-r["games"], r["opening_name"]))
    return [_with_win_rate(row) for row in result]


def record_by_speed(games=None):
    """Record for each time control (bullet, blitz, rapid, daily)."""
    rows = _all(games).values("speed").annotate(**RESULT_COUNTS).order_by("-games")
    labels = dict(Game.Speed.choices)
    return [_with_win_rate({**row, "label": labels.get(row["speed"], row["speed"])}) for row in rows]


def endings(games=None, result=Game.Result.LOSS):
    """How games with a given result ended, most common first."""
    return list(
        _all(games)
        .filter(result=result)
        .exclude(termination="")
        .values("termination")
        .annotate(games=Count("id"))
        .order_by("-games")
    )


def current_ratings(games=None):
    """My most recent rating in each time control."""
    ratings = []
    for speed, label in Game.Speed.choices:
        latest = _all(games).filter(speed=speed, my_rating__isnull=False).first()
        if latest:
            ratings.append({"speed": speed, "label": label, "rating": latest.my_rating})
    return ratings


def rating_history(games=None):
    """My rating over time for each time control, one point per day.

    Uses the last game of each day, which keeps the chart readable even
    with thousands of games.
    """
    history = {}
    rows = (
        _all(games)
        .filter(my_rating__isnull=False)
        .order_by("played_at")
        .values_list("speed", "played_at", "my_rating")
    )
    for speed, played_at, rating in rows:
        day = played_at.date().isoformat()
        history.setdefault(speed, {})[day] = rating  # later games overwrite earlier ones
    labels = dict(Game.Speed.choices)
    return [
        {"speed": speed, "label": labels.get(speed, speed),
         "points": [{"date": day, "rating": rating} for day, rating in days.items()]}
        for speed, days in history.items()
    ]
