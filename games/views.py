import hmac
from datetime import timedelta

import requests
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from . import charts, stats
from .importer import import_games
from .models import Game, ImportRun

# An opening needs this many games (as that color) before it can be called
# my best or toughest, so a lucky 3-0 doesn't top the list. With a small
# filtered set, like only rapid games, the bar drops so there's still an answer.
INSIGHT_MIN_GAMES = 10
INSIGHT_MIN_GAMES_SMALL = 3

# The Refresh button can run at most once in this window, so repeated
# clicks don't hammer Chess.com's API.
REFRESH_COOLDOWN = timedelta(minutes=5)


def filtered_games(request):
    """All games, or only one time control if ?speed= is a valid choice."""
    speed = request.GET.get("speed", "")
    if speed in Game.Speed.values:
        return speed, Game.objects.filter(speed=speed)
    return "", Game.objects.all()


def best_and_toughest(games, min_games):
    """My best and toughest opening in a set of games (usually one color).

    Best is the highest win rate; toughest is the lowest. Ties go to the
    opening played more often. Returns (None, None) if fewer than two
    openings have enough games to compare.
    """
    rows = stats.opening_stats(games, min_games=min_games)
    if len(rows) < 2:
        return None, None
    best = max(rows, key=lambda r: (r["win_rate"], r["games"]))
    toughest = min(rows, key=lambda r: (r["win_rate"], -r["games"]))
    return best, toughest


def summary(games):
    """Every stat shown on the dashboard, for a set of games.

    Used by both the dashboard page and the JSON API, so they always agree.
    """
    big = games.count() >= 200
    table_min = 5 if big else 2  # fewer games, lower bar
    insight_min = INSIGHT_MIN_GAMES if big else INSIGHT_MIN_GAMES_SMALL

    as_white = games.filter(color=Game.Color.WHITE)
    as_black = games.filter(color=Game.Color.BLACK)
    best_white, toughest_white = best_and_toughest(as_white, insight_min)
    best_black, toughest_black = best_and_toughest(as_black, insight_min)
    return {
        "totals": stats.record(games),
        "white_openings": stats.opening_stats(as_white, table_min)[:8],
        "black_openings": stats.opening_stats(as_black, table_min)[:8],
        "best_white": best_white,
        "toughest_white": toughest_white,
        "best_black": best_black,
        "toughest_black": toughest_black,
        "insight_min_games": insight_min,
        "win_endings": stats.endings(games, Game.Result.WIN),
        "loss_endings": stats.endings(games, Game.Result.LOSS),
    }


def dashboard(request):
    """The main page: my record, ratings, openings, and recent games."""
    speed, games = filtered_games(request)
    context = {
        **summary(games),
        "speed": speed,
        "speeds": stats.record_by_speed(),
        "ratings": stats.current_ratings(),
        "rating_chart": charts.rating_chart(stats.rating_history(games)),
        "recent_games": games[:10],
        "last_import": ImportRun.objects.first(),
    }
    context["insight_sides"] = [
        ("White", context["best_white"], context["toughest_white"]),
        ("Black", context["best_black"], context["toughest_black"]),
    ]
    return render(request, "games/dashboard.html", context)


@require_GET
def api_stats(request):
    """GET /api/stats/ — the dashboard's stats as JSON. Accepts ?speed= too."""
    speed, games = filtered_games(request)
    data = {
        "speed": speed or "all",
        **summary(games),
        "by_speed": stats.record_by_speed(),
        "current_ratings": stats.current_ratings(),
        "rating_history": stats.rating_history(games),
    }
    return JsonResponse(data)


@require_POST
def refresh(request):
    """The Refresh button: import new games now, unless it ran very recently."""
    last = ImportRun.objects.first()
    if last and timezone.now() - last.finished_at < REFRESH_COOLDOWN:
        messages.info(request, "Games were just updated. Try again in a few minutes.")
    else:
        try:
            run = import_games(settings.CHESSCOM_USERNAME, source=ImportRun.Source.REFRESH)
            messages.success(request, f"Imported {run.new_games} new game(s).")
        except requests.RequestException:
            messages.error(request, "Couldn't reach Chess.com. Try again later.")
    return redirect("games:dashboard")


@require_GET
def cron_import(request):
    """The daily import, called by Vercel Cron.

    Vercel sends "Authorization: Bearer <CRON_SECRET>", so only Vercel can
    trigger it. Without a CRON_SECRET configured, the endpoint stays closed.
    """
    expected = f"Bearer {settings.CRON_SECRET}"
    given = request.headers.get("Authorization", "")
    if not settings.CRON_SECRET or not hmac.compare_digest(given, expected):
        return HttpResponseForbidden("Not allowed")

    run = import_games(settings.CHESSCOM_USERNAME, source=ImportRun.Source.CRON)
    return JsonResponse({"months_checked": run.months_checked, "new_games": run.new_games})
