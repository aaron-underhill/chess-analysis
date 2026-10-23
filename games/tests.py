from datetime import datetime, timezone

from django.db import IntegrityError
from django.test import TestCase

from .models import Game


def make_game(**overrides):
    """Create a game with sensible defaults; tests override what they care about."""
    fields = {
        "platform": Game.Platform.LICHESS,
        "game_id": "abc123",
        "played_at": datetime(2026, 10, 20, 18, 30, tzinfo=timezone.utc),
        "speed": Game.Speed.BLITZ,
        "color": Game.Color.WHITE,
        "result": Game.Result.WIN,
        "opponent": "some_player",
        "pgn": "1. e4 e5 2. Nf3 Nc6 *",
    }
    fields.update(overrides)
    return Game.objects.create(**fields)


class GameModelTests(TestCase):
    def test_new_games_start_unanalyzed(self):
        game = make_game()
        self.assertFalse(game.analyzed)

    def test_same_game_cannot_be_saved_twice(self):
        make_game(game_id="dup")
        with self.assertRaises(IntegrityError):
            make_game(game_id="dup")

    def test_same_id_on_different_platforms_is_allowed(self):
        make_game(game_id="42", platform=Game.Platform.LICHESS)
        make_game(game_id="42", platform=Game.Platform.CHESS_COM)
        self.assertEqual(Game.objects.count(), 2)

    def test_newest_games_come_first(self):
        old = make_game(game_id="old", played_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
        new = make_game(game_id="new", played_at=datetime(2026, 6, 1, tzinfo=timezone.utc))
        self.assertEqual(list(Game.objects.all()), [new, old])

    def test_readable_name(self):
        game = make_game(opponent="magnus", result=Game.Result.LOSS, color=Game.Color.BLACK)
        self.assertEqual(str(game), "2026-10-20 vs magnus (loss, black)")
