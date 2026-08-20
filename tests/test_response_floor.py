"""The response floor's arithmetic, on data whose true reliability is known by construction.

The whole diagnostic rests on one estimator: split-half plus Spearman-Brown, recovering the share
of a pooled series that is shared signal. A test that only checked it returns a number between zero
and one would be checking nothing, so these build stations out of a known signal plus known
independent noise and ask whether the estimator finds the reliability that was put in.
"""

import numpy as np
import pytest

from migratlas.constants import EARTH_KM
from migratlas.reports.response_floor import (
    great_circle_km,
    pooled_series,
    region_of,
    split_half_reliability,
)

YEARS = list(range(1995, 2026))


def _stations(
    count: int, signal_sd: float, noise_sd: float, seed: int = 3
) -> list[dict[int, float]]:
    """Stations sharing one year-to-year signal, each with its own independent error."""
    rng = np.random.default_rng(seed)
    signal = rng.normal(0.0, signal_sd, size=len(YEARS))
    return [
        dict(zip(YEARS, signal + rng.normal(0.0, noise_sd, size=len(YEARS)), strict=True))
        for _ in range(count)
    ]


def test_a_shared_signal_with_no_noise_is_perfectly_reliable() -> None:
    """Every station reporting the same thing must come back at reliability one."""
    rng = np.random.default_rng(0)
    reliability = split_half_reliability(_stations(12, signal_sd=3.0, noise_sd=0.0), rng)
    assert reliability == pytest.approx(1.0, abs=0.01)


def test_pure_noise_is_centred_on_nothing_but_can_draw_high() -> None:
    """Both halves of this matter, and the second is why the module reports a bar.

    Stations moving independently must not *systematically* look predictable, or the estimator would
    license a hunt for drivers that cannot exist. Averaged over many realisations it does not: the
    mean sits near zero. But its spread is wide -- a single noise-only draw reached 0.33 when this
    test first ran with a bar of 0.2, and across two hundred draws the 95th percentile is near 0.4.
    So one region's reliability means little without `null_reliability` beside it, which is exactly
    what that function exists for.
    """
    values = [
        split_half_reliability(
            _stations(12, signal_sd=0.0, noise_sd=3.0, seed=seed),
            np.random.default_rng(500 + seed),
            splits=40,
        )
        for seed in range(60)
    ]
    finite = np.array([v for v in values if np.isfinite(v)])
    assert abs(float(finite.mean())) < 0.15, "pure noise must not look reliable on average"
    assert float(np.percentile(finite, 95)) > 0.2, (
        "the spread is the reason a bar is reported; if this ever fails the bar may be dropped"
    )


def test_the_estimator_recovers_a_reliability_it_was_given() -> None:
    """Signal and noise in a known ratio, and the answer has to land near the truth.

    With a shared signal of sd `s` and independent per-station error of sd `e` over `n` stations,
    the pooled series has signal variance `s^2` and error variance `e^2/n`, so the true reliability
    is `s^2 / (s^2 + e^2/n)`. Twelve stations, signal 2, noise 4: 4 / (4 + 16/12) = 0.75.
    """
    rng = np.random.default_rng(2)
    reliability = split_half_reliability(_stations(12, signal_sd=2.0, noise_sd=4.0), rng)
    assert reliability == pytest.approx(0.75, abs=0.12)


def test_more_stations_raise_the_ceiling_on_the_same_signal() -> None:
    """The whole reason for pooling: averaging cancels independent error and keeps shared signal."""
    rng = np.random.default_rng(4)
    few = split_half_reliability(_stations(4, signal_sd=1.0, noise_sd=4.0, seed=7), rng)
    many = split_half_reliability(_stations(20, signal_sd=1.0, noise_sd=4.0, seed=7), rng)
    assert many > few


def test_the_pooled_series_ignores_years_nobody_reported() -> None:
    """A gap must be a gap, not a zero -- a zero would read as an unusually early migration."""
    members = [{2000: 250.0, 2001: 252.0}, {2000: 254.0}]
    series = pooled_series(members, [2000, 2001, 2002])
    assert series[0] == pytest.approx(252.0)
    assert series[1] == pytest.approx(252.0)
    assert np.isnan(series[2])


def test_a_station_maps_to_its_flyway_and_band() -> None:
    """phase1's own vocabulary, so this pins the crossing rather than a partition of my own."""
    assert region_of(40.0, -96.0) == "central 37-42N"
    assert region_of(45.0, -75.0) == "eastern 42-50N"
    assert region_of(35.0, -120.0) == "western 32-37N"
    # Outside the banded latitudes entirely: no region rather than the nearest one.
    assert region_of(60.0, -96.0) is None
    assert region_of(20.0, -96.0) is None


def test_the_distance_is_a_great_circle_and_shares_its_radius() -> None:
    """The scalar twin of phase1h's polars haversine. One degree of latitude is about 111 km."""
    assert great_circle_km(40.0, -96.0, 41.0, -96.0) == pytest.approx(111.2, abs=0.5)
    assert great_circle_km(40.0, -96.0, 40.0, -96.0) == 0.0
    # A quarter of the way round the planet along a meridian.
    assert great_circle_km(0.0, 0.0, 90.0, 0.0) == pytest.approx(np.pi / 2 * EARTH_KM, rel=1e-6)
