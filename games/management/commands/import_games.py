"""python manage.py import_games <username>

Downloads a player's Chess.com games and saves any that aren't stored yet.
The first run imports everything. Later runs only check the months since the
newest stored game, so they're quick and never create duplicates.
"""

import requests
from django.core.management.base import BaseCommand, CommandError

from games import chesscom
from games.models import Game
from games.stats import opening_stats, record


class Command(BaseCommand):
    help = "Import games from Chess.com for a player."

    def add_arguments(self, parser):
        parser.add_argument("username", help="Chess.com username")
        parser.add_argument(
            "--all",
            action="store_true",
            help="Re-check every month, not just the months since the newest stored game.",
        )

    def handle(self, *args, username, all, **options):
        session = requests.Session()
        try:
            archives = chesscom.archive_urls(username, session)
        except requests.RequestException as error:
            raise CommandError(f"Couldn't reach Chess.com: {error}")

        if not archives:
            self.stdout.write(f"No games found for {username}.")
            return

        # Only look at months on or after the newest game already stored.
        newest = Game.objects.filter(platform=Game.Platform.CHESS_COM).first()
        if newest and not all:
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

        Game.objects.bulk_create(new_games)

        self.stdout.write(self.style.SUCCESS(
            f"Checked {len(archives)} month(s). Imported {len(new_games)} new game(s)"
            + (f", skipped {skipped} variant game(s)." if skipped else ".")
        ))
        self.print_summary()

    def print_summary(self):
        totals = record()
        self.stdout.write(
            f"Stored games: {totals['games']} "
            f"({totals['wins']} W / {totals['losses']} L / {totals['draws']} D, "
            f"{totals['win_rate']}% wins)"
        )
        top = opening_stats()[:5]
        if top:
            self.stdout.write("Most played openings:")
            for row in top:
                self.stdout.write(
                    f"  {row['games']:>4}  {row['win_rate']:>5}%  {row['opening_name']}"
                )
