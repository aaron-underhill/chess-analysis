"""Build the rating chart as plain SVG, with no JavaScript library.

The view calls rating_chart() with the output of stats.rating_history(),
and the template draws the result inside an <svg>. Coordinates are in a
fixed viewBox, so the chart scales to any screen width.
"""

from datetime import date

WIDTH, HEIGHT = 1000, 300
LEFT, RIGHT, TOP, BOTTOM = 52, 16, 12, 30


def _nice_step(span, target_ticks=5):
    """A round step (like 50, 100, 200) that gives about target_ticks gridlines."""
    raw = max(span / target_ticks, 1)
    for step in (10, 25, 50, 100, 200, 250, 500, 1000):
        if step >= raw:
            return step
    return 1000


def rating_chart(history):
    """Turn rating history into SVG paths, gridlines, and axis labels."""
    points = [
        (date.fromisoformat(p["date"]).toordinal(), p["rating"])
        for series in history
        for p in series["points"]
    ]
    if not points:
        return None

    days = [d for d, _ in points]
    ratings = [r for _, r in points]
    first_day, last_day = min(days), max(days)
    step = _nice_step(max(ratings) - min(ratings))
    low = (min(ratings) // step) * step
    high = -(-max(ratings) // step) * step  # round up
    if high == low:
        high = low + step

    plot_w, plot_h = WIDTH - LEFT - RIGHT, HEIGHT - TOP - BOTTOM

    def x(day):
        if last_day == first_day:
            return LEFT + plot_w / 2
        return LEFT + (day - first_day) / (last_day - first_day) * plot_w

    def y(rating):
        return TOP + (high - rating) / (high - low) * plot_h

    lines = []
    for series in history:
        coords = [
            (x(date.fromisoformat(p["date"]).toordinal()), y(p["rating"]))
            for p in series["points"]
        ]
        lines.append({
            "speed": series["speed"],
            "label": series["label"],
            "path": "M" + " L".join(f"{cx:.1f},{cy:.1f}" for cx, cy in coords),
            "dot": coords[-1] if len(coords) == 1 else None,
            "latest": series["points"][-1]["rating"],
        })

    y_ticks = [{"y": round(y(r), 1), "label": r} for r in range(low, high + 1, step)]

    # About six date labels, evenly spaced across the range.
    count = 6 if last_day > first_day else 1
    x_ticks = []
    for i in range(count):
        day = first_day + round(i * (last_day - first_day) / max(count - 1, 1))
        x_ticks.append({"x": round(x(day), 1), "label": date.fromordinal(day).strftime("%b %Y")})

    return {
        "width": WIDTH,
        "height": HEIGHT,
        "left": LEFT,
        "right": WIDTH - RIGHT,
        "bottom": HEIGHT - BOTTOM,
        "lines": lines,
        "y_ticks": y_ticks,
        "x_ticks": x_ticks,
    }
