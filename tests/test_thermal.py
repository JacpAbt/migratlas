"""Occupied against available temperature, and the ratio between them.

Built so each case has a known answer. A tracking index is a ratio of two fitted trends, which is
the kind of quantity that produces a plausible number from a sign error, a swapped numerator or a
denominator that should have been refused.
"""

from datetime import UTC, datetime

import numpy as np
import polars as pl
import pytest

from migratlas.metrics import thermal

YEARS = range(1990, 2021)
"""31 years, comfortably over the 15-year floor."""


def _cells(
    *,
    ambient_per_year: float = 0.05,
    occupied_per_year: float = 0.05,
    base: float = 8.0,
    share: float = 1.0,
    doy_per_year: float = 0.0,
) -> pl.DataFrame:
    """A survey where the ambient and the occupied temperature move at chosen rates.

    Two cells per year: the species is caught in one of them, and the ambient is the mean over
    both. Keeping them separate is what lets occupied and available move independently, which is
    the whole point of the pairing.
    """
    rows = []
    for offset, year in enumerate(YEARS):
        occupied = base + occupied_per_year * offset
        # The unoccupied cell carries whatever makes the two-cell mean follow the ambient rate.
        ambient = base + ambient_per_year * offset
        other = 2 * ambient - occupied
        day = round(150 + doy_per_year * offset)
        for index, (temperature, cpue) in enumerate(((occupied, 10.0), (other, 0.0))):
            rows.append(
                {
                    "site_id": f"S{year}-{index}",
                    "period_start": datetime(year, 1, 1, tzinfo=UTC).replace(
                        month=1 + (day - 1) // 31, day=1 + (day - 1) % 28
                    ),
                    "year": year,
                    "cpue": cpue,
                    "taxon_key": 1,
                    "taxon_label": "Testus specius",
                    thermal.BOTTOM: temperature
                    if np.random.default_rng(offset).random() <= share
                    else None,
                }
            )
    return pl.DataFrame(rows)


def test_a_species_holding_its_temperature_in_a_warming_sea_scores_one() -> None:
    """Full tracking: the ambient rose and the occupied did not."""
    cells = _cells(ambient_per_year=0.05, occupied_per_year=0.0)
    results, ambient = thermal.tracking(thermal.occupied(cells), thermal.available(cells))
    assert ambient is not None
    assert ambient.per_decade == pytest.approx(0.5, abs=1e-6)
    [item] = results
    assert item.held == pytest.approx(1.0, abs=1e-6)


def test_a_species_warming_with_its_sea_scores_zero() -> None:
    """No tracking: it stayed put and the water warmed around it."""
    cells = _cells(ambient_per_year=0.05, occupied_per_year=0.05)
    results, _ = thermal.tracking(thermal.occupied(cells), thermal.available(cells))
    [item] = results
    assert item.held == pytest.approx(0.0, abs=1e-6)


def test_a_species_moving_into_warmer_water_scores_below_zero() -> None:
    """The direction that would be invisible if the index were an absolute difference."""
    cells = _cells(ambient_per_year=0.05, occupied_per_year=0.10)
    results, _ = thermal.tracking(thermal.occupied(cells), thermal.available(cells))
    [item] = results
    assert item.held == pytest.approx(-1.0, abs=1e-6)


def test_a_sea_that_did_not_warm_yields_no_index_at_all() -> None:
    """The refusal that matters most.

    Holding a constant temperature in an ocean that did not warm is stillness, not tracking, and
    the ratio would divide by noise. A magnitude floor let this through once and produced a mean
    index of +1.23 on an ambient trend of +0.069 +/- 0.181.
    """
    cells = _cells(ambient_per_year=0.0, occupied_per_year=0.0)
    results, ambient = thermal.tracking(thermal.occupied(cells), thermal.available(cells))
    assert results == []
    assert ambient is not None
    assert not ambient.distinguishable


def test_a_trend_is_distinguishable_only_against_its_own_error() -> None:
    """A magnitude is not a test. A large trend on noisy data is not separable from zero, and a
    small one on clean data is."""
    years = np.arange(1990, 2021)
    clean = thermal._trend(years, 0.02 * (years - 1990))
    assert clean is not None
    assert clean.distinguishable

    rng = np.random.default_rng(20260730)
    noisy = thermal._trend(years, 0.02 * (years - 1990) + rng.normal(0, 5.0, years.size))
    assert noisy is not None
    assert not noisy.distinguishable


def test_the_available_temperature_ignores_catch() -> None:
    """It is the water on offer, not the water the fish chose.

    Weighting it by any species' catch would make the denominator a property of that species, and
    every index would then be one divided by itself.
    """
    cells = _cells(ambient_per_year=0.05, occupied_per_year=0.0)
    series = thermal.available(cells)
    # Two cells per year, so the mean is the midpoint -- not the occupied cell's value.
    first = series.sort("year").row(0, named=True)
    assert first["available"] == pytest.approx(8.0, abs=1e-6)
    assert first["hauls"] == 2


def test_a_year_too_sparse_in_thermometers_is_dropped_not_averaged() -> None:
    """Coverage runs from 99.8% to 0% across surveys, so a year built from a handful of readings
    is a different sample rather than a noisier one."""
    cells = _cells(share=0.2)
    series = thermal.available(cells)
    assert series.height < len(YEARS)


def test_a_short_series_gets_no_trend() -> None:
    cells = _cells().filter(pl.col("year") <= 1999)
    results, ambient = thermal.tracking(thermal.occupied(cells), thermal.available(cells))
    assert ambient is None
    assert results == []


def test_calendar_drift_is_measured_so_it_can_be_ruled_out() -> None:
    """A survey that moved later in the season samples warmer water for that reason alone. It is
    confound one, and the only defence is measuring it."""
    cells = _cells(doy_per_year=1.0)
    drift = thermal.date_drift(thermal.available(cells))
    assert drift is not None
    assert drift.per_decade > 0


def test_a_stable_calendar_reports_no_drift() -> None:
    drift = thermal.date_drift(thermal.available(_cells(doy_per_year=0.0)))
    assert drift is not None
    assert drift.per_decade == pytest.approx(0.0, abs=0.5)


def test_the_tracking_field_does_not_shadow_a_tuple_method() -> None:
    """It was called `index`, which silently overrides `tuple.index` on a NamedTuple. mypy caught
    it; this keeps it caught."""
    item = thermal.Tracking(
        taxon_key=1,
        taxon_label="x",
        occupied_per_decade=0.0,
        ambient_per_decade=0.5,
        held=1.0,
        years=31,
    )
    # `index` is still the tuple method rather than a float field. Searching for the ambient
    # value, which is unique in this tuple -- 1.0 would match taxon_key, since 1 == 1.0.
    assert callable(item.index)
    assert item.index(0.5) == 3
    assert item.held == 1.0
