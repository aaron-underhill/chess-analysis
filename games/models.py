from django.db import models


class Game(models.Model):
    """One chess game I played, imported from Lichess or Chess.com.

    Every field is stored from my point of view: `color` is the side I
    played, and `result` is whether I won, lost, or drew.
    """

    class Platform(models.TextChoices):
        LICHESS = "lichess", "Lichess"
        CHESS_COM = "chesscom", "Chess.com"

    class Color(models.TextChoices):
        WHITE = "white", "White"
        BLACK = "black", "Black"

    class Result(models.TextChoices):
        WIN = "win", "Win"
        LOSS = "loss", "Loss"
        DRAW = "draw", "Draw"

    class Speed(models.TextChoices):
        BULLET = "bullet", "Bullet"
        BLITZ = "blitz", "Blitz"
        RAPID = "rapid", "Rapid"
        CLASSICAL = "classical", "Classical"
        DAILY = "daily", "Daily"

    # Where the game came from. The platform's own game ID lets the importer
    # skip games it has already saved.
    platform = models.CharField(max_length=10, choices=Platform.choices)
    game_id = models.CharField(max_length=64)
    url = models.URLField(blank=True)

    played_at = models.DateTimeField()
    time_control = models.CharField(max_length=20, blank=True)  # e.g. "600+5"
    speed = models.CharField(max_length=10, choices=Speed.choices)

    color = models.CharField(max_length=5, choices=Color.choices)
    result = models.CharField(max_length=4, choices=Result.choices)
    termination = models.CharField(max_length=30, blank=True)  # e.g. "checkmate"

    opponent = models.CharField(max_length=64)
    my_rating = models.PositiveIntegerField(null=True, blank=True)
    opponent_rating = models.PositiveIntegerField(null=True, blank=True)

    # Opening info, using the standard ECO code (like "B20") and its name.
    eco = models.CharField(max_length=3, blank=True)
    opening_name = models.CharField(max_length=200, blank=True)

    # The full game in PGN, the standard text format for chess games.
    # Stockfish analysis in phase 2 reads the moves from here.
    pgn = models.TextField()

    # Set to True once Stockfish has analyzed the game, so each game is
    # only ever analyzed once.
    analyzed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-played_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["platform", "game_id"], name="unique_game_per_platform"
            ),
        ]

    def __str__(self):
        return f"{self.played_at:%Y-%m-%d} vs {self.opponent} ({self.result}, {self.color})"
