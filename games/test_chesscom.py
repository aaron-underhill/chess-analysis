from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from . import chesscom
from .models import Game
from .stats import opening_stats, record

ECO_URL = "https://www.chess.com/openings/Sicilian-Defense-Bowdler-Attack"


def raw_game(white="AaronDaGG", black="opponent1", white_result="win",
             black_result="resigned", uuid="g1", end_time=1792454400, **extra):
    """A game shaped like Chess.com's API response."""
    game = {
        "url": f"https://www.chess.com/game/live/{uuid}",
        "uuid": uuid,
        "pgn": f'[Event "Live Chess"]\n[ECO "B20"]\n[ECOUrl "{ECO_URL}"]\n\n1. e4 c5 2. Bc4 *',
        "time_control": "600",
        "end_time": end_time,
        "rated": True,
        "time_class": "rapid",
        "rules": "chess",
        "white": {"username": white, "rating": 1200, "result": white_result},
        "black": {"username": black, "rating": 1150, "result": black_result},
    }
    game.update(extra)
    return game


class ParseGameTests(SimpleTestCase):
    def test_win_as_white(self):
        fields = chesscom.parse_game(raw_game(), "AaronDaGG")
        self.assertEqual(fields["color"], "white")
        self.assertEqual(fields["result"], "win")
        self.assertEqual(fields["termination"], "resignation")
        self.assertEqual(fields["opponent"], "opponent1")
        self.assertEqual((fields["my_rating"], fields["opponent_rating"]), (1200, 1150))

    def test_loss_as_black_by_checkmate(self):
        raw = raw_game(white="opponent1", black="AaronDaGG",
                       white_result="win", black_result="checkmated")
        fields = chesscom.parse_game(raw, "AaronDaGG")
        self.assertEqual((fields["color"], fields["result"]), ("black", "loss"))
        self.assertEqual(fields["termination"], "checkmate")

    def test_draw(self):
        raw = raw_game(white_result="repetition", black_result="repetition")
        fields = chesscom.parse_game(raw, "AaronDaGG")
        self.assertEqual((fields["result"], fields["termination"]), ("draw", "repetition"))

    def test_username_match_ignores_case(self):
        fields = chesscom.parse_game(raw_game(white="aarondagg"), "AaronDaGG")
        self.assertEqual(fields["color"], "white")

    def test_opening_comes_from_pgn(self):
        fields = chesscom.parse_game(raw_game(), "AaronDaGG")
        self.assertEqual(fields["eco"], "B20")
        self.assertEqual(fields["opening_name"], "Sicilian Defense Bowdler Attack")

    def test_variants_are_skipped(self):
        self.assertIsNone(chesscom.parse_game(raw_game(rules="chess960"), "AaronDaGG"))

    def test_games_without_the_player_are_skipped(self):
        self.assertIsNone(chesscom.parse_game(raw_game(white="someone_else"), "AaronDaGG"))

    def test_opening_name_drops_move_list(self):
        url = "https://www.chess.com/openings/Italian-Game-Two-Knights-Defense-4.d3"
        self.assertEqual(chesscom.opening_name_from_url(url), "Italian Game Two Knights Defense")

    def test_archive_month(self):
        url = "https://api.chess.com/pub/player/aarondagg/games/2026/09"
        self.assertEqual(chesscom.archive_month(url), (2026, 9))


ARCHIVES = [
    "https://api.chess.com/pub/player/aarondagg/games/2026/09",
    "https://api.chess.com/pub/player/aarondagg/games/2026/10",
]


class ImportCommandTests(TestCase):
    def run_import(self, months, *args):
        """Run the command with Chess.com replaced by fake monthly archives."""
        with mock.patch.object(chesscom, "archive_urls", return_value=list(months)), \
             mock.patch.object(chesscom, "month_games", side_effect=lambda url, s=None: months[url]):
            out = StringIO()
            call_command("import_games", "AaronDaGG", *args, stdout=out)
            return out.getvalue()

    def test_imports_every_game(self):
        months = {
            ARCHIVES[0]: [raw_game(uuid="a", end_time=1789430400)],
            ARCHIVES[1]: [raw_game(uuid="b", end_time=1791504000),
                          raw_game(uuid="c", end_time=1791590400, rules="chess960")],
        }
        output = self.run_import(months)
        self.assertEqual(Game.objects.count(), 2)
        self.assertIn("Imported 2 new game(s), skipped 1 variant game(s).", output)

    def test_running_twice_adds_only_new_games(self):
        months = {ARCHIVES[0]: [], ARCHIVES[1]: [raw_game(uuid="a", end_time=1791504000)]}
        self.run_import(months)
        months[ARCHIVES[1]].append(raw_game(uuid="b", end_time=1791590400))
        output = self.run_import(months)
        self.assertEqual(Game.objects.count(), 2)
        self.assertIn("Imported 1 new game(s).", output)

    def test_later_runs_skip_older_months(self):
        months = {ARCHIVES[0]: [], ARCHIVES[1]: [raw_game(uuid="a", end_time=1791504000)]}
        self.run_import(months)
        output = self.run_import(months)
        self.assertIn("Checked 1 month(s)", output)


class StatsTests(TestCase):
    def setUp(self):
        for uuid, white_result, black_result in [
            ("w1", "win", "resigned"),
            ("w2", "win", "timeout"),
            ("l1", "checkmated", "win"),
            ("d1", "agreed", "agreed"),
        ]:
            Game.objects.create(**chesscom.parse_game(
                raw_game(uuid=uuid, white_result=white_result, black_result=black_result),
                "AaronDaGG",
            ))

    def test_record(self):
        self.assertEqual(
            record(),
            {"games": 4, "wins": 2, "losses": 1, "draws": 1, "win_rate": 50.0},
        )

    def test_opening_stats(self):
        [row] = opening_stats()
        self.assertEqual(row["opening_name"], "Sicilian Defense Bowdler Attack")
        self.assertEqual((row["games"], row["wins"], row["win_rate"]), (4, 2, 50.0))
