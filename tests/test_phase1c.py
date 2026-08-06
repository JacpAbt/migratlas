"""The homogeneity fit, extracted so the report and the ledger cannot disagree about it.

`composition` printed the airspeed trend and `findings.py` published a different, typed one. They
are the same fit now, which is only worth doing if the fit itself is tested -- phase1c had no tests
at all, so the refactor that unified them was unguarded in both directions.
"""

import numpy as np
import polars as pl
import pytest

from migratlas.reports.phase1 import MIN_YEARS
from migratlas.reports.phase1_robustness import FLEET_MIDPOINT_YEAR
from migratlas.reports.phase1c import SpeedTrend, _speed_trend


def _station(name: str, *, slope: float, years: int = MIN_YEARS + 5) -> pl.DataFrame:
    """One station whose speed rises by `slope` m/s per year, straddling the fleet break."""
    span = np.arange(FLEET_MIDPOINT_YEAR - years // 2, FLEET_MIDPOINT_YEAR + years - years // 2)
    return pl.DataFrame(
        {
            "station_id": [name] * span.size,
            "year": span,
            "airspeed": 9.0 + slope * (span - span[0]),
        }
    )


def test_the_trend_is_per_decade_not_per_year() -> None:
    """The factor of ten is the whole difference between a plausible number and a wrong one."""
    trend = _speed_trend(_station("KABC", slope=0.05), "airspeed")
    assert trend is not None
    assert trend.mean == pytest.approx(0.5)


def test_a_station_short_of_the_minimum_does_not_enter_the_fit() -> None:
    """15 years is the same floor Phase 1a uses, and a shorter series is not a trend."""
    assert _speed_trend(_station("KABC", slope=0.05, years=MIN_YEARS - 1), "airspeed") is None


def test_stations_are_averaged_rather_than_pooled() -> None:
    """Each station gets one slope and the slopes are averaged.

    Pooling the rows instead would let a station with more years carry the answer, which is the
    weighting Phase 1a rejected.
    """
    frame = pl.concat([_station("KABC", slope=0.0), _station("KXYZ", slope=0.10, years=30)])
    trend = _speed_trend(frame, "airspeed")
    assert trend is not None
    assert trend.mean == pytest.approx(0.5)
    assert trend.stations == 2


def test_the_level_is_reported_beside_the_drift() -> None:
    """Two questions -- is the mixture birds, and is it changing -- and both are needed."""
    trend = _speed_trend(_station("KABC", slope=0.0), "airspeed")
    assert trend is not None
    assert trend.level == pytest.approx(9.0)


def test_flat_means_the_interval_covers_zero() -> None:
    """The condition `findings.py` publishes the composition claim on, so it is not a phrasing."""
    assert SpeedTrend(mean=-0.06, ci95=0.08, level=8.65, stations=78).flat
    assert not SpeedTrend(mean=0.50, ci95=0.13, level=8.65, stations=78).flat


def test_a_trend_exactly_at_its_interval_is_not_called_flat() -> None:
    """A boundary worth pinning: the claim is that the drift is *indistinguishable* from zero."""
    assert not SpeedTrend(mean=0.2, ci95=0.2, level=9.0, stations=10).flat
