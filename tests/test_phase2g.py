"""Phase 2g's pieces, on frames whose answer is built in, and the one refactor it needed.

Phase 1g's spatial machinery took a `driver` argument so this phase could call it on rain. The
first test is that the default reproduces what it did before; the rest are the new pieces.
"""

import numpy as np
import polars as pl
import pytest

from migratlas.reports import phase1g, phase2g


def _cells(n: int = 100) -> pl.DataFrame:
    rng = np.random.default_rng(31)
    side = int(np.sqrt(n))
    lat = np.repeat(np.arange(side), side) * 0.25 - 30.0
    lon = np.tile(np.arange(side), side) * 0.25 + 25.0
    effort = rng.normal(0.0, 5.0, size=n)
    water = rng.normal(0.0, 1.0, size=n)
    rain = rng.normal(0.0, 0.5, size=n)
    return pl.DataFrame(
        {
            "cell_lat": lat[:n],
            "cell_lon": lon[:n],
            "delta": 0.5 * effort + 2.0 * rain + rng.normal(0.0, 0.5, size=n),
            "delta_corrected": 0.5 * effort + 2.0 * rain,
            "effort": effort,
            "water": water,
            phase2g.RAIN: rain,
            phase2g.RAIN_FIRST: rng.uniform(0.0, 4.0, size=n),
        }
    )


def test_the_driver_argument_defaults_to_water_and_changes_nothing_there() -> None:
    frame = _cells()
    assert phase1g.fit(frame) == phase1g.fit(frame, driver="water")


def test_the_driver_argument_reads_the_named_column() -> None:
    frame = _cells()
    assert phase1g.fit(frame, driver=phase2g.RAIN).water == pytest.approx(2.0, abs=0.3)
    assert phase1g.fit(frame).water == pytest.approx(0.0, abs=0.5)


def test_cell_level_reads_the_rain_and_keeps_its_sign_across_quadrants() -> None:
    result = phase2g.cell_level(_cells())
    assert result.main.water == pytest.approx(2.0, abs=0.3)
    assert result.sign_survives_quadrants
    assert result.placebo_cells == 25


def test_a_species_coefficient_is_recovered_with_effort_held() -> None:
    rng = np.random.default_rng(5)
    rain = rng.normal(0.0, 0.5, size=400)
    effort = rng.normal(0.0, 5.0, size=400)
    rate = 0.02 * effort + 0.3 * rain + rng.normal(0.0, 0.05, size=400)
    coefficient, half = phase2g._species_coefficient(rate, rain, effort)
    assert coefficient == pytest.approx(0.3, abs=0.03)
    assert half < 0.05


def test_reporting_rates_put_a_zero_where_a_species_was_not_recorded() -> None:
    """The same arithmetic `reporting_rates` performs, on two cells: the zero is a cell."""
    cells = pl.DataFrame(
        {
            "cell_lat": [-30.0, -30.0],
            "cell_lon": [25.0, 25.25],
            "n_1": [10.0, 20.0],
            "n_2": [10.0, 40.0],
        }
    )
    first = pl.DataFrame(
        {
            "taxon_key": [1, 1],
            "taxon_label": ["a", "a"],
            "cell_lat": [-30.0, -30.0],
            "cell_lon": [25.0, 25.25],
            "k": [5.0, 10.0],
        }
    )
    second = pl.DataFrame(
        {
            "taxon_key": [1],
            "taxon_label": ["a"],
            "cell_lat": [-30.0],
            "cell_lon": [25.0],
            "k": [10.0],
        }
    )
    keys = ["taxon_key", "cell_lat", "cell_lon"]
    baseline = first.group_by("taxon_key", "taxon_label").agg(seen=pl.len())
    rates = (
        baseline.join(cells, how="cross")
        .join(first.select(*keys, k_1=pl.col("k")), on=keys, how="left")
        .join(second.select(*keys, k_2=pl.col("k")), on=keys, how="left")
        .with_columns(pl.col("k_1").fill_null(0.0), pl.col("k_2").fill_null(0.0))
        .with_columns(delta_rate=(pl.col("k_2") / pl.col("n_2")) - (pl.col("k_1") / pl.col("n_1")))
        .sort("cell_lon")
    )
    # Cell one: 10/10 - 5/10 = +0.5. Cell two: 0/40 - 10/20 = -0.5, the zero being a cell.
    assert rates["delta_rate"].to_list() == pytest.approx([0.5, -0.5])
