"""The wind-support arithmetic, tested on frames written by hand rather than against the lake.

`support_series` was split out of `wind_support` when the season became an argument, because
Phase 3f needs the same term in spring. Two of its properties are the kind that fail silently:
a heading averaged the wrong way still returns a number, and a projection with its sign flipped
still returns a number. Both would turn a tailwind into a headwind in a published coefficient.
"""

from datetime import UTC, date, datetime

import polars as pl

from migratlas.reports.phase2a_timing import support_series

U = "wind_u_925hPa"
V = "wind_v_925hPa"


def _nights(*bearings_and_weights: tuple[float, float], day: int = 15) -> pl.DataFrame:
    """One station, one year, one night per bearing, all on distinct dates."""
    return pl.DataFrame(
        {
            "station_id": ["KAAA"] * len(bearings_and_weights),
            "timestamp": [
                datetime(2010, 9, day + index, tzinfo=UTC)
                for index in range(len(bearings_and_weights))
            ],
            "direction_deg": [bearing for bearing, _ in bearings_and_weights],
            "magnitude": [weight for _, weight in bearings_and_weights],
        }
    )


def _winds(u: float, v: float, *, days: int = 2, day: int = 15) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "station_id": ["KAAA"] * days,
            "date": [date(2010, 9, day + index) for index in range(days)],
            U: [u] * days,
            V: [v] * days,
        }
    )


def test_the_heading_is_a_circular_mean_not_an_arithmetic_one() -> None:
    """350 degrees and 10 degrees must average to north. Averaged as numbers they give south.

    This is the discriminating case: a due-north wind scored against a north heading supports
    at +10, and against the arithmetic mean of the two bearings -- 180, due south -- it would
    score -10. The sign of a published coefficient rests on this.
    """
    support = support_series(_nights((350.0, 1.0), (10.0, 1.0)), _winds(0.0, 10.0))
    assert support.height == 1
    assert support["support"][0] == 10.0


def test_support_is_a_projection_so_its_sign_says_whether_the_wind_helped() -> None:
    north = _nights((0.0, 1.0))
    tail = support_series(north, _winds(0.0, 8.0, days=1))["support"][0]
    head = support_series(north, _winds(0.0, -8.0, days=1))["support"][0]
    cross = support_series(north, _winds(8.0, 0.0, days=1))["support"][0]

    assert tail == 8.0
    assert head == -8.0
    # A pure crosswind neither helps nor hinders along the heading, which is what makes this a
    # support term rather than a wind-speed term.
    assert cross == 0.0


def test_the_traffic_weights_decide_the_heading() -> None:
    """A heavy night and a light night disagreeing pulls the heading toward the heavy one.

    The weight is reflectivity traffic, so the heading is where the mass went, not where the
    median night went. A station with one big northward night and one small eastward one heads
    north.
    """
    support = support_series(_nights((0.0, 100.0), (90.0, 1.0)), _winds(0.0, 10.0))
    # Almost all of a northward wind is recovered: the eastward night barely tilts the heading.
    assert support["support"][0] > 9.9


def test_the_season_window_is_the_callers_job_and_an_empty_panel_reports() -> None:
    """`wind_support` filters by season before calling this, so an out-of-season panel arrives
    empty -- and an empty panel must report rather than raise, because a station with no usable
    nights in a season is a coverage fact and not an error."""
    empty = _nights((0.0, 1.0)).clear()
    assert support_series(empty, _winds(0.0, 10.0)).is_empty()


def test_a_wind_frame_without_its_components_returns_empty_rather_than_guessing() -> None:
    """The pivot names columns after the NARR level. If the level ever changes and the column
    name does not, the honest answer is no rows -- not a nearest available column."""
    wrong = _winds(0.0, 10.0).rename({U: "wind_u_850hPa", V: "wind_v_850hPa"})
    assert support_series(_nights((0.0, 1.0)), wrong).is_empty()


def test_support_averages_over_the_nights_of_a_station_year() -> None:
    nights = _nights((0.0, 1.0), (0.0, 1.0))
    winds = pl.DataFrame(
        {
            "station_id": ["KAAA", "KAAA"],
            "date": [date(2010, 9, 15), date(2010, 9, 16)],
            U: [0.0, 0.0],
            V: [4.0, 6.0],
        }
    )
    assert support_series(nights, winds)["support"][0] == 5.0
