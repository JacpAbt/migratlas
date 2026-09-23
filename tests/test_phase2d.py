"""Phase 2d's pieces, on panels whose answer is built in.

The window rule, the within-site fit with and without a year term, the year-clustered interval and
the pooled heterogeneity are each testable without a lake -- and each has a failure that would look
like a result: a window that overlaps the flight, a response that absorbs a shared trend, an
interval that pretends site-years are independent, a Q against the wrong number of units.
"""

import numpy as np
import polars as pl
import pytest

from migratlas.reports import phase2d

SITES = 30
YEARS = 30


def test_the_window_ends_the_month_before_the_flight_month() -> None:
    assert phase2d.window_for(6) == (4, 5)
    assert phase2d.window_for(4) == (2, 3)
    assert phase2d.window_for(8) == (6, 7)


def test_a_flight_too_early_for_a_pre_season_is_coverage() -> None:
    assert phase2d.window_for(2) is None
    assert phase2d.window_for(1) is None


def test_the_flight_month_is_read_off_the_median_day() -> None:
    # Day 166 is 15 June in a non-leap year.
    assert phase2d.flight_month(np.array([160.0, 166.0, 172.0])) == 6
    assert phase2d.flight_month(np.array([100.0, 105.0, 110.0])) == 4


def _panel(
    *,
    response: float,
    year_trend: float = 0.0,
    temperature_trend: float = 0.0,
    shared_spring: float = 1.0,
    shared_residual: float = 0.0,
) -> pl.DataFrame:
    """Sites with their own intercepts, one national spring per year, and a known response.

    `shared_spring` is how much of a year's temperature every site shares. `shared_residual` is a
    national year effect on the flight date that temperature does not explain -- the thing that
    makes a year-clustered interval wider than a naive one, because it is what correlates the
    residuals within a year. Without it the residuals are independent and clustering is not wider,
    which is Phase 3j's lesson in this setting.
    """
    rng = np.random.default_rng(11)
    intercepts = rng.normal(150.0, 10.0, size=SITES)
    national = rng.normal(0.0, shared_spring, size=YEARS)
    year_effect = (
        rng.normal(0.0, shared_residual, size=YEARS) if shared_residual else np.zeros(YEARS)
    )
    rows: list[dict[str, object]] = []
    for s in range(SITES):
        for y in range(YEARS):
            year = 1990 + y
            temperature = (
                10.0 + national[y] + rng.normal(0.0, 0.3) + temperature_trend * (year - 1990) / 10
            )
            flight = (
                intercepts[s]
                + response * (temperature - 10.0)
                + year_trend * (year - 1990) / 10
                + year_effect[y]
                + rng.normal(0.0, 2.0)
            )
            rows.append(
                {
                    "site_id": f"S{s:03d}",
                    "year": year,
                    "flight_day": float(flight),
                    "temperature": float(temperature),
                    "label": "Testus testus",
                    "generation": "pollard-walk",
                }
            )
    return pl.DataFrame(rows)


def _columns(panel: pl.DataFrame) -> phase2d.Columns:
    _, site = np.unique(panel["site_id"].to_numpy(), return_inverse=True)
    return phase2d.Columns(
        site=np.asarray(site, dtype=int),
        flight=panel["flight_day"].to_numpy().astype(float),
        temperature=panel["temperature"].to_numpy().astype(float),
        year=panel["year"].to_numpy().astype(int),
    )


def test_the_within_fit_recovers_a_known_response() -> None:
    columns = _columns(_panel(response=-5.0))
    assert phase2d._within_fit(columns, with_year=False) == pytest.approx(-5.0, abs=0.4)
    assert phase2d._within_fit(columns, with_year=True) == pytest.approx(-5.0, abs=0.4)


def test_a_year_term_removes_a_shared_trend_that_arm_a_absorbs() -> None:
    """Phase 2c's lesson, built in: both series trend, and only arm B declines to credit warmth."""
    columns = _columns(
        _panel(response=0.0, year_trend=-8.0, temperature_trend=0.6, shared_spring=0.3)
    )
    absorbed = phase2d._within_fit(columns, with_year=False)
    corrected = phase2d._within_fit(columns, with_year=True)
    assert absorbed < -2.0, absorbed
    assert corrected == pytest.approx(0.0, abs=1.0), corrected


def test_a_year_clustered_interval_is_wider_where_years_share_a_residual() -> None:
    columns = _columns(_panel(response=-5.0, shared_spring=1.5, shared_residual=3.0))
    clustered = phase2d._year_bootstrap(columns, name="t", clustered=True, draws=100)
    naive = phase2d._year_bootstrap(columns, name="t", clustered=False, draws=100)
    assert clustered[1] - clustered[0] > naive[1] - naive[0]


def test_unit_response_reads_its_label_and_generation_off_the_panel() -> None:
    result = phase2d.unit_response(
        _panel(response=-5.0), unit="1:pollard-walk", window=(4, 5), draws=20
    )
    assert result.label == "Testus testus"
    assert result.generation == "pollard-walk"
    assert result.sites == SITES
    assert result.years == YEARS
    assert result.response_b == pytest.approx(-5.0, abs=0.4)
    assert not result.migrant


def _unit(
    label: str, response: float, stderr: float, *, migrant: bool = False
) -> phase2d.UnitResponse:
    return phase2d.UnitResponse(
        unit=label,
        label=label,
        generation="pollard-walk",
        migrant=migrant,
        years=30,
        sites=50,
        rows=1500,
        window=(4, 5),
        response_a=response * 1.1,
        response_b=response,
        interval_b=(response - 1.96 * stderr, response + 1.96 * stderr),
        naive_b=(response - stderr, response + stderr),
        warming=0.3,
        advance=-2.0,
    )


def test_heterogeneity_clears_only_when_the_species_genuinely_differ() -> None:
    alike = [_unit(f"u{i}", -4.0 + 0.05 * i, 0.5) for i in range(25)]
    differ = [_unit(f"u{i}", -8.0 + 0.4 * i, 0.5) for i in range(25)]
    q_alike, bar = phase2d.heterogeneity(alike)
    q_differ, _ = phase2d.heterogeneity(differ)
    assert q_alike < bar
    assert q_differ > bar


def test_the_pooled_share_is_a_ratio_of_medians() -> None:
    units = [_unit(f"u{i}", -4.0, 0.5) for i in range(25)]
    result = phase2d.pooled(units, draws=50)
    assert result is not None
    # S x W = -4.0 x 0.3 = -1.2 against A = -2.0.
    assert result.share == pytest.approx(0.6)
    assert result.heterogeneous is False


def test_too_few_units_is_a_coverage_statement() -> None:
    assert phase2d.pooled([_unit(f"u{i}", -4.0, 0.5) for i in range(5)], draws=20) is None


def test_the_pre_season_needs_every_window_month() -> None:
    driver = pl.DataFrame(
        {
            "site_id": ["a", "a", "a", "b"],
            "year": [2000, 2000, 2001, 2000],
            "month": [4, 5, 4, 5],
            "value": [8.0, 12.0, 9.0, 11.0],
        }
    )
    out = phase2d.pre_season(driver, (4, 5)).sort("site_id")
    assert out.height == 1
    assert out["temperature"][0] == pytest.approx(10.0)
