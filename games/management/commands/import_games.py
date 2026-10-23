"""python manage.py import_games <username>

Downloads a player's Chess.com games and saves any that aren't stored yet.
The first run imports everything. Later runs only check the months since the
newest stored game, so they're quick and never create duplicates.
"""

import requests
from django.core.management.base import BaseCommand, CommandError

from games.importer import import_games
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
        try:
            run = import_games(username, check_all=all)
        except requests.RequestException as error:
            raise CommandError(f"Couldn't reach Chess.com: {error}")

        self.stdout.write(self.style.SUCCESS(
            f"Checked {run.months_checked} month(s). Imported {run.new_games} new game(s)"
            + (f", skipped {run.skipped} variant game(s)." if run.skipped else ".")
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
