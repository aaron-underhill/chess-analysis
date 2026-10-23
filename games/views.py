from django.shortcuts import render

from . import charts, stats
from .models import Game

# An opening needs this many games before it counts as a "best" or "worst"
# opening, so a lucky 3-0 doesn't top the list.
INSIGHT_MIN_GAMES = 20


def dashboard(request):
    """The main page: my record, ratings, openings, and recent games.

    An optional ?speed=blitz (or bullet, rapid, daily) narrows every stat
    to that time control.
    """
    speed = request.GET.get("speed", "")
    games = Game.objects.all()
    if speed in Game.Speed.values:
        games = games.filter(speed=speed)
    else:
        speed = ""

    total = games.count()
    # With fewer games, show openings played fewer times.
    min_games = 5 if total >= 200 else 2

    openings = stats.opening_stats(games, min_games=INSIGHT_MIN_GAMES)
    context = {
        "speed": speed,
        "speeds": stats.record_by_speed(),
        "totals": stats.record(games),
        "ratings": stats.current_ratings(),
        "white_openings": stats.opening_stats(games.filter(color=Game.Color.WHITE), min_games)[:8],
        "black_openings": stats.opening_stats(games.filter(color=Game.Color.BLACK), min_games)[:8],
        "best_opening": max(openings, key=lambda r: r["win_rate"], default=None),
        "worst_opening": min(openings, key=lambda r: r["win_rate"], default=None),
        "loss_endings": stats.endings(games, Game.Result.LOSS),
        "win_endings": stats.endings(games, Game.Result.WIN),
        "rating_chart": charts.rating_chart(stats.rating_history(games)),
        "recent_games": games[:10],
    }
    return render(request, "games/dashboard.html", context)
