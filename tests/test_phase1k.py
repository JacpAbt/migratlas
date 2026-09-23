"""The shape guard that decides what `flight-advance` is allowed to say.

Phase 1j registered prediction 6 -- neither the flight-period duration nor the standard deviation
around the mean flight date carries a trend distinguishable from zero -- together with its
consequence: a trend withdraws the comparison to the radar rather than caveating it. The guard
therefore decides a published sentence, so it is tested on constructed series and not only on the
archive, which no test may reach.
"""

import numpy as np
import polars as pl
import pytest

from migratlas.reports import phase1k


def _series(slope: float, *, years: int = 20) -> pl.DataFrame:
    """A shape series per unit with a known slope in days per year and a small fixed wobble."""
    rng = np.random.default_rng(7)
    rows = [
        {
            "site": unit,
            "taxon_label": "constructed",
            "brood": 0,
            "year": 1995 + offset,
            "sd_days": 10.0 + slope * offset + float(rng.normal(0.0, 0.05)),
            "duration_days": 40.0 + slope * offset + float(rng.normal(0.0, 0.05)),
        }
        for unit in range(12)
        for offset in range(years)
    ]
    return pl.DataFrame(rows)


def test_a_flat_shape_series_reads_as_flat() -> None:
    trends = phase1k.shape_trends(_series(0.0))
    assert trends, "nothing was fitted, so the guard would pass by being absent"
    assert all(trend.flat for trend in trends), [trend.label for trend in trends]


def test_a_trending_shape_series_does_not_read_as_flat() -> None:
    trends = phase1k.shape_trends(_series(0.1))
    assert trends
    assert not any(trend.flat for trend in trends), [trend.label for trend in trends]
    for trend in trends:
        assert trend.median == pytest.approx(1.0, abs=0.1), trend.label


def test_a_unit_short_of_the_floor_does_not_enter() -> None:
    assert phase1k.shape_trends(_series(0.0, years=phase1k.FLIGHT_MIN_YEARS - 1)) == ()


def test_both_quantities_are_reported_over_both_windows() -> None:
    trends = phase1k.shape_trends(_series(0.0))
    assert {(trend.quantity, trend.since) for trend in trends} == {
        ("sd_days", None),
        ("sd_days", phase1k.FLIGHT_SHAPE_WINDOW),
        ("duration_days", None),
        ("duration_days", phase1k.FLIGHT_SHAPE_WINDOW),
    }
