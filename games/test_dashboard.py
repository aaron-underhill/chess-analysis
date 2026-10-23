from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from . import chesscom
from .charts import rating_chart
from .models import Game
from .stats import current_ratings, endings, rating_history, record_by_speed
from .test_chesscom import raw_game

# Timestamps in October 2026.
OCT_20, OCT_21 = 1792454400, 1792540800


def add_game(uuid, end_time=OCT_20, my_rating=None, **kwargs):
    """Save a game built from Chess.com-shaped data, optionally with my rating."""
    fields = chesscom.parse_game(raw_game(uuid=uuid, end_time=end_time, **kwargs), "AaronDaGG")
    if my_rating is not None:
        fields["my_rating"] = my_rating
    return Game.objects.create(**fields)


class DashboardViewTests(TestCase):
    def test_empty_database_shows_import_hint(self):
        response = self.client.get(reverse("games:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No games yet")

    def test_shows_record_and_openings(self):
        add_game("a")
        add_game("b", white_result="checkmated", black_result="win")
        response = self.client.get(reverse("games:dashboard"))
        self.assertContains(response, "1 W &middot; 1 L &middot; 0 D")
        self.assertContains(response, "Sicilian Defense Bowdler Attack")
        self.assertContains(response, "<svg", html=False)

    def test_speed_filter_narrows_the_stats(self):
        add_game("blitz1", time_class="blitz")
        add_game("rapid1", time_class="rapid")
        add_game("rapid2", time_class="rapid")
        response = self.client.get(reverse("games:dashboard"), {"speed": "rapid"})
        self.assertEqual(response.context["totals"]["games"], 2)

    def test_unknown_speed_shows_all_games(self):
        add_game("a")
        response = self.client.get(reverse("games:dashboard"), {"speed": "nonsense"})
        self.assertEqual(response.context["speed"], "")
        self.assertEqual(response.context["totals"]["games"], 1)


class DashboardStatsTests(TestCase):
    def test_record_by_speed(self):
        add_game("a", time_class="blitz")
        add_game("b", time_class="blitz", white_result="checkmated", black_result="win")
        add_game("c", time_class="rapid")
        rows = {row["speed"]: row for row in record_by_speed()}
        self.assertEqual((rows["blitz"]["games"], rows["blitz"]["win_rate"]), (2, 50.0))
        self.assertEqual(rows["rapid"]["label"], "Rapid")

    def test_endings_counts_how_losses_happen(self):
        add_game("a", white_result="checkmated", black_result="win")
        add_game("b", white_result="timeout", black_result="win")
        add_game("c", white_result="timeout", black_result="win")
        self.assertEqual(
            endings(result="loss"),
            [{"termination": "time", "games": 2}, {"termination": "checkmate", "games": 1}],
        )

    def test_current_rating_is_from_the_newest_game(self):
        add_game("old", end_time=OCT_20, my_rating=1400)
        add_game("new", end_time=OCT_21, my_rating=1450)
        [rapid] = [r for r in current_ratings() if r["speed"] == "rapid"]
        self.assertEqual(rapid["rating"], 1450)

    def test_rating_history_keeps_last_game_of_each_day(self):
        add_game("morning", end_time=OCT_20, my_rating=1400)
        add_game("night", end_time=OCT_20 + 3600, my_rating=1410)
        [series] = rating_history()
        self.assertEqual(series["points"], [{"date": "2026-10-20", "rating": 1410}])


class RatingChartTests(SimpleTestCase):
    HISTORY = [{
        "speed": "blitz", "label": "Blitz",
        "points": [{"date": "2026-01-01", "rating": 1400}, {"date": "2026-12-31", "rating": 1600}],
    }]

    def test_no_history_means_no_chart(self):
        self.assertIsNone(rating_chart([]))

    def test_line_spans_the_plot(self):
        chart = rating_chart(self.HISTORY)
        [line] = chart["lines"]
        self.assertTrue(line["path"].startswith(f"M{chart['left']:.1f},"))
        self.assertIn(f"L{chart['right']:.1f},", line["path"])
        self.assertEqual(line["latest"], 1600)

    def test_axis_labels_cover_the_ratings(self):
        labels = [t["label"] for t in rating_chart(self.HISTORY)["y_ticks"]]
        self.assertLessEqual(labels[0], 1400)
        self.assertGreaterEqual(labels[-1], 1600)

    def test_single_game_is_drawn_as_a_dot(self):
        history = [{"speed": "rapid", "label": "Rapid", "points": [{"date": "2026-10-20", "rating": 1500}]}]
        [line] = rating_chart(history)["lines"]
        self.assertIsNotNone(line["dot"])
