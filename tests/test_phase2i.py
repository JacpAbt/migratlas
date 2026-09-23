"""Phase 2i's pieces, on a panel whose front speed is built in.

A passage date is written as a departure plus a travel time, so the latitude gradient the module
fits has a known answer: a front crossing the band at `v` degrees a day puts `-1/v` days in every
degree. A failure here reads as a result -- a recovered speed that is not the one constructed means
the gradient is not measuring the front.
"""

import numpy as np
import polars as pl
import pytest

from migratlas.reports import phase2i

YEARS = tuple(range(1995, 2026))
LATITUDES = tuple(float(x) for x in range(30, 51))
"""Twenty-one, so a full year clears `MIN_PANEL` and the floor is tested by removing some."""


def _panel(
    *,
    speed: float = 2.0,
    speed_after_2012: float | None = None,
    departure_shift_per_year: float = 0.0,
    noise: float = 0.0,
    drop_station_year: tuple[str, int] | None = None,
) -> pl.DataFrame:
    """Passage dates built as departure + travel, with the front's speed chosen per era.

    `speed` is degrees of latitude a day. In autumn the birds move south, so a station one degree
    further north is passed `1/speed` days earlier and the fitted slope is negative.
    """
    rng = np.random.default_rng(7)
    source = 55.0
    rows: list[dict[str, object]] = []
    for year in YEARS:
        v = speed if speed_after_2012 is None or year < 2012 else speed_after_2012
        departure = 240.0 + departure_shift_per_year * (year - YEARS[0])
        for latitude in LATITUDES:
            station = f"K{int(latitude):02d}"
            if drop_station_year == (station, year):
                continue
            date = departure + (source - latitude) / v
            if noise:
                date += float(rng.normal(0.0, noise))
            rows.append(
                {
                    "station_id": station,
                    "year": year,
                    "q50_doy": date,
                    "station_latitude": latitude,
                    "station_longitude": -90.0,
                }
            )
    return pl.DataFrame(rows)


def _mean_latitude(panel: pl.DataFrame) -> float:
    return float(np.mean(panel["station_latitude"].to_numpy()))


def test_the_gradient_recovers_the_front_speed_that_was_built_in() -> None:
    panel = _panel(speed=2.0)
    mean_latitude = _mean_latitude(panel)
    fits = phase2i.year_fits(panel, mean_latitude)
    assert len(fits) == len(YEARS)
    assert fits[0].slope == pytest.approx(-0.5, abs=1e-9)
    assert fits[0].front_km_per_day == pytest.approx(2.0 * phase2i.KM_PER_DEGREE, rel=1e-9)


def test_a_faster_front_puts_fewer_days_in_a_degree() -> None:
    slow = phase2i.year_fits(_panel(speed=1.0), 40.0)[0]
    fast = phase2i.year_fits(_panel(speed=4.0), 40.0)[0]
    assert abs(slow.slope) > abs(fast.slope)
    assert fast.front_km_per_day > slow.front_km_per_day


def test_a_departure_shift_moves_the_intercept_and_leaves_the_slope_alone() -> None:
    """The design's load-bearing split: a departure change is latitude-flat by construction."""
    panel = _panel(speed=2.0, departure_shift_per_year=-0.05)
    fits = phase2i.year_fits(panel, _mean_latitude(panel))
    slopes = np.array([fit.slope for fit in fits])
    intercepts = np.array([fit.intercept for fit in fits])
    assert slopes.std() == pytest.approx(0.0, abs=1e-9)
    assert intercepts[-1] - intercepts[0] == pytest.approx(-0.05 * (len(YEARS) - 1), abs=1e-6)


def test_a_front_that_speeds_up_at_2012_shows_a_step_in_the_slope() -> None:
    panel = _panel(speed=2.0, speed_after_2012=2.5)
    fits = phase2i.year_fits(panel, _mean_latitude(panel))
    trend = phase2i.trend_with_break(
        np.array([f.year for f in fits], dtype=float),
        np.array([f.slope for f in fits]),
        name="t",
        draws=200,
    )
    assert trend is not None
    assert trend.step_clear
    # 1/2.0 - 1/2.5 = 0.1 days per degree, and the slope is negative, so the step is positive.
    assert trend.step == pytest.approx(0.1, abs=1e-6)


def test_a_step_in_the_slope_implies_a_bigger_date_step_further_from_the_mean() -> None:
    band = phase2i.Band(
        name="t",
        low=30.0,
        high=50.0,
        stations=19,
        mean_latitude=40.0,
        fits=(),
        speeds=(),
        slope_trend=phase2i.Trend(
            per_decade=0.0,
            decade_interval=(-1.0, 1.0),
            step=-0.18,
            step_interval=(-0.2, -0.16),
        ),
        intercept_trend=None,
    )
    assert band.implied_step_at(28.0) == pytest.approx(2.16, abs=1e-9)
    assert abs(band.implied_step_at(46.0)) < abs(band.implied_step_at(28.0))


def test_the_duty_cycle_is_the_share_of_the_night_the_front_advances_through() -> None:
    speeds = phase2i.Speeds(
        year=2000, front_km_per_day=50.0, flight_km_per_hour=25.0, night_hours=10.0
    )
    assert speeds.duty_cycle == pytest.approx(0.2)
    assert (
        phase2i.Speeds(2000, 50.0, 0.0, 10.0).duty_cycle
        != phase2i.Speeds(2000, 50.0, 0.0, 10.0).duty_cycle
    )  # NaN when there is no flight speed to divide by


def test_the_fixed_panel_drops_a_station_missing_a_year() -> None:
    panel = _panel(drop_station_year=("K35", 2003))
    fixed = phase2i.fixed_panel(panel, (30.0, 50.0))
    assert "K35" not in set(fixed["station_id"].to_list())
    assert fixed["station_id"].n_unique() == len(LATITUDES) - 1


def test_the_band_restricts_before_it_fixes_the_panel() -> None:
    fixed = phase2i.fixed_panel(_panel(), (37.0, 50.0))
    latitudes = fixed["station_latitude"].unique().to_list()
    assert min(latitudes) >= 37.0
    assert max(latitudes) <= 50.0


def test_a_year_with_too_few_stations_is_not_fitted() -> None:
    panel = _panel().filter(~((pl.col("year") == 2005) & (pl.col("station_latitude") > 33.0)))
    years = {fit.year for fit in phase2i.year_fits(panel, 40.0)}
    assert 2005 not in years
    assert 2006 in years
