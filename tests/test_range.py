from datetime import UTC, datetime

import polars as pl
import pytest

from migratlas.metrics import range as range_metrics


def survey(
    *,
    years: range = range(2000, 2021),
    cells: tuple[float, ...] = (40.5, 41.5, 42.5),
    drift: float = 0.0,
    depth_drift: float = 0.0,
    late_cell: float | None = None,
) -> pl.DataFrame:
    """A survey sampling the same cells every year, optionally with a real drift.

    ``late_cell`` adds a cell sampled only in the second half of the record -- the footprint
    confound, and the one thing the metric exists to be immune to.
    """
    rows = []
    for year in years:
        elapsed = year - min(years)
        sampled = list(cells)
        if late_cell is not None and elapsed > len(years) // 2:
            sampled.append(late_cell)
        for latitude in sampled:
            rows.append(
                {
                    "site_id": f"S{latitude}",
                    "period_start": datetime(year, 6, 1, tzinfo=UTC),
                    "site_longitude": -10.5,
                    "site_latitude": latitude + drift * elapsed,
                    "site_depth_m": 100.0 + depth_drift * elapsed,
                    "count": 10.0,
                    "effort": 1.0,
                    "taxon_key": 1,
                    "taxon_label": "Testus specius",
                }
            )
    return pl.DataFrame(rows)


def test_cpue_divides_catch_by_effort() -> None:
    """A haul that swept twice the area is not evidence of twice as many animals."""
    frame = survey().with_columns(effort=pl.lit(2.0), count=pl.lit(10.0))
    cells = range_metrics.to_cells(frame)
    assert cells["cpue"].unique().to_list() == [5.0]


def test_a_stable_survey_shows_no_shift() -> None:
    cells = range_metrics.to_cells(survey())
    restricted, footprint = range_metrics.consistent_footprint(cells)
    assert footprint.cells_dropped == 0
    shifts = range_metrics.shift_per_decade(range_metrics.centroids(restricted))
    assert shifts["per_decade"][0] == pytest.approx(0.0, abs=1e-9)


def test_a_real_drift_is_recovered() -> None:
    cells = range_metrics.to_cells(survey(drift=0.02))
    restricted, _ = range_metrics.consistent_footprint(cells)
    shifts = range_metrics.shift_per_decade(range_metrics.centroids(restricted))
    # 0.02 degrees a year is 0.2 a decade.
    assert shifts["per_decade"][0] == pytest.approx(0.2, abs=0.01)


def test_a_footprint_that_grows_northward_fakes_a_shift() -> None:
    """The whole reason the footprint rule exists, shown in both directions.

    Without the rule, a survey that added a northern cell halfway through shows a poleward
    centroid shift while every animal stayed exactly where it was.
    """
    cells = range_metrics.to_cells(survey(late_cell=55.5))

    unrestricted = range_metrics.shift_per_decade(range_metrics.centroids(cells))
    assert unrestricted["per_decade"][0] > 0.5

    restricted, footprint = range_metrics.consistent_footprint(cells)
    assert footprint.cells_dropped == 1
    corrected = range_metrics.shift_per_decade(range_metrics.centroids(restricted))
    assert corrected["per_decade"][0] == pytest.approx(0.0, abs=1e-9)


def test_the_footprint_reports_what_it_dropped() -> None:
    """A silent restriction reads as full coverage; the cost has to be visible."""
    cells = range_metrics.to_cells(survey(late_cell=55.5))
    _, footprint = range_metrics.consistent_footprint(cells)
    assert footprint.rows_dropped > 0
    assert 0 < footprint.rows_share < 1
    assert "dropped 1" in str(footprint)


def test_depth_centroid_is_computed_when_the_column_is_there() -> None:
    """Depth is half the marine story; latitude alone would hide a real depth response."""
    cells = range_metrics.to_cells(survey(depth_drift=1.5))
    restricted, _ = range_metrics.consistent_footprint(cells)
    series = range_metrics.centroids(restricted)
    assert "mean_depth" in series.columns
    shifts = range_metrics.shift_per_decade(series, column="mean_depth")
    assert shifts["per_decade"][0] == pytest.approx(15.0, abs=0.1)


def test_a_break_term_absorbs_a_step() -> None:
    """A gear change moves every measurement at once, which is not a trend."""
    stepped = range_metrics.centroids(
        range_metrics.consistent_footprint(range_metrics.to_cells(survey()))[0]
    ).with_columns(
        mean_latitude=pl.col("mean_latitude")
        + pl.when(pl.col("year") >= 2010).then(2.0).otherwise(0.0)
    )

    ignored = range_metrics.shift_per_decade(stepped)
    assert ignored["per_decade"][0] > 0.5

    modelled = range_metrics.shift_per_decade(stepped, break_year=2010)
    assert modelled["per_decade"][0] == pytest.approx(0.0, abs=0.01)
    assert modelled["break_shift"][0] == pytest.approx(2.0, abs=0.01)


def test_a_short_series_gets_no_trend() -> None:
    cells = range_metrics.to_cells(survey(years=range(2010, 2020)))
    restricted, _ = range_metrics.consistent_footprint(cells)
    shifts = range_metrics.shift_per_decade(range_metrics.centroids(restricted), min_years=15)
    assert shifts.is_empty()
