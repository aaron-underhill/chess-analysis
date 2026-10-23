"""Summary statistics about my games, shared by the dashboard and commands."""

from django.db.models import Count, Q

from .models import Game


def record(games=None):
    """Wins, losses, and draws, plus win rate, for a set of games."""
    games = Game.objects.all() if games is None else games
    totals = games.aggregate(
        games=Count("id"),
        wins=Count("id", filter=Q(result=Game.Result.WIN)),
        losses=Count("id", filter=Q(result=Game.Result.LOSS)),
        draws=Count("id", filter=Q(result=Game.Result.DRAW)),
    )
    totals["win_rate"] = round(100 * totals["wins"] / totals["games"], 1) if totals["games"] else 0.0
    return totals


def opening_stats(games=None, min_games=1):
    """Record for each opening, most-played first."""
    games = Game.objects.all() if games is None else games
    rows = (
        games.exclude(opening_name="")
        .values("opening_name")
        .annotate(
            games=Count("id"),
            wins=Count("id", filter=Q(result=Game.Result.WIN)),
            losses=Count("id", filter=Q(result=Game.Result.LOSS)),
            draws=Count("id", filter=Q(result=Game.Result.DRAW)),
        )
        .filter(games__gte=min_games)
        .order_by("-games", "opening_name")
    )
    return [
        {**row, "win_rate": round(100 * row["wins"] / row["games"], 1)}
        for row in rows
    ]
