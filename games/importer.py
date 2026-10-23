"""Import a player's Chess.com games into the database.

Shared by the import_games command, the daily cron, and the Refresh button,
so all three behave the same way: only new games are saved, and after the
first import only recent months are checked.
"""

import requests

from . import chesscom
from .models import Game, ImportRun


def import_games(username, source=ImportRun.Source.COMMAND, check_all=False, session=None):
    """Download and save any games not already stored. Returns the ImportRun.

    Raises requests.RequestException if Chess.com can't be reached.
    """
    session = session or requests.Session()
    archives = chesscom.archive_urls(username, session)

    # Only look at months on or after the newest game already stored.
    newest = Game.objects.filter(platform=Game.Platform.CHESS_COM).first()
    if newest and not check_all:
        start = (newest.played_at.year, newest.played_at.month)
        archives = [url for url in archives if chesscom.archive_month(url) >= start]

    known_ids = set(
        Game.objects.filter(platform=Game.Platform.CHESS_COM).values_list("game_id", flat=True)
    )
    new_games, skipped = [], 0
    for url in archives:
        for raw in chesscom.month_games(url, session):
            fields = chesscom.parse_game(raw, username)
            if fields is None:
                skipped += 1
            elif fields["game_id"] not in known_ids:
                new_games.append(Game(**fields))
                known_ids.add(fields["game_id"])

    Game.objects.bulk_create(new_games, batch_size=500)
    run = ImportRun.objects.create(
        source=source, months_checked=len(archives), new_games=len(new_games)
    )
    run.skipped = skipped  # reported by the command, not stored
    return run
