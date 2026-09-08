"""Phase 2h's pieces, on survey rows whose answer is built in.

Two seasons of one region, some species given the same decadal trend in both and some given
opposite trends, so a failure reads as a result: a species that agrees must not raise the pooled
disagreement, and a species that disagrees must.

The generator places a species' weighted centroid *exactly* where it is asked to, by splitting the
catch between the northernmost and southernmost cells of the footprint. The first version tilted
the catch across every cell instead, and a seasonal offset large enough to be worth testing drove
the tilt negative and was clipped -- which broke the linearity the test was asserting and looked
like the design failing. An exact construction cannot do that.
"""

from datetime import UTC, datetime

import numpy as np
import polars as pl
import pytest

from migratlas.reports import phase2h

YEARS = 30
CELLS = 16
START = 1990
NOISE = 0.02
"""Without noise the fit is exact, its standard error is zero, and every species is dropped."""


def _rows(
    *,
    trends: dict[str, dict[int, float]],
    offsets: dict[str, float] | None = None,
    units: tuple[str, ...] = ("A-1", "A-2"),
    cells: int = CELLS,
    noise: float = NOISE,
) -> pl.DataFrame:
    """Survey rows whose weighted centroid sits exactly where each season's trend asks.

    Every cell is sampled every year, so the footprint keeps all of them; the catch is a two-point
    mixture between the extreme cells, which puts the weighted mean at the target for any target
    inside the range and never asks for a negative weight. ``offsets`` shifts a whole season by a
    constant, which is the seasonal catchability confound the design claims cancels in a trend.
    """
    rng = np.random.default_rng(11)
    offsets = offsets or {}
    latitudes = [50.5 + index for index in range(cells)]
    low, high = latitudes[0], latitudes[-1]
    centre = float(np.mean(latitudes))
    records: list[dict[str, object]] = []
    for unit in units:
        for taxon, per_unit in trends.items():
            key = abs(hash(taxon)) % 10_000
            for step in range(YEARS):
                target = (
                    centre
                    + per_unit[units.index(unit)] * step / 10.0
                    + offsets.get(unit, 0.0)
                    + (float(rng.normal(0.0, noise)) if noise else 0.0)
                )
                share = (target - low) / (high - low)
                for index, latitude in enumerate(latitudes):
                    if index == 0:
                        catch = 1.0 - share
                    elif index == cells - 1:
                        catch = share
                    else:
                        # Surveyed, nothing caught: the footprint counts the haul, the centroid
                        # does not count the zero.
                        catch = 0.0
                    records.append(
                        {
                            "site_id": f"{unit}:{index}",
                            "period_start": datetime(START + step, 3, 1, tzinfo=UTC),
                            "site_longitude": 1.5,
                            "site_latitude": latitude,
                            "site_depth_m": 60.0,
                            "count": catch,
                            "effort": 1.0,
                            "protocol": "gear=X",
                            "taxon_key": key,
                            "taxon_label": taxon,
                            "survey_unit": unit,
                        }
                    )
    return pl.DataFrame(records)


def _results(frame: pl.DataFrame) -> list[phase2h.SpeciesResult]:
    cells, _, _, _ = phase2h.family_cells(frame, ("A-1", "A-2"))
    series = phase2h.season_series(cells)
    return phase2h.species_results(series, phase2h.season_trends(series))


def test_heterogeneity_is_zero_when_the_seasons_agree_and_large_when_they_do_not() -> None:
    agree = phase2h._heterogeneity(np.array([0.1, 0.1]), np.array([0.02, 0.02]))
    disagree = phase2h._heterogeneity(np.array([0.3, -0.3]), np.array([0.02, 0.02]))
    assert agree == pytest.approx(0.0, abs=1e-12)
    assert disagree > 100.0


def test_heterogeneity_at_two_seasons_is_the_squared_standardised_difference() -> None:
    """The note registers `z` at two seasons and Q above it; the two must be the same statistic."""
    values, errors = np.array([0.22, -0.05]), np.array([0.03, 0.04])
    z = (values[0] - values[1]) / np.sqrt(errors[0] ** 2 + errors[1] ** 2)
    assert phase2h._heterogeneity(values, errors) == pytest.approx(z**2, rel=1e-9)


def test_amplitude_is_the_range_and_its_error_comes_from_the_two_extremes() -> None:
    span, error = phase2h._amplitude(np.array([1.0, 4.0, 2.0]), np.array([0.1, 0.2, 0.3]))
    assert span == pytest.approx(3.0)
    assert error == pytest.approx(np.sqrt(0.2**2 + 0.1**2))


def test_the_trend_recovered_per_season_is_the_trend_that_was_built_in() -> None:
    results = _results(_rows(trends={"steady": {0: 0.30, 1: 0.30}, "also": {0: -0.20, 1: -0.20}}))
    recovered = {r.taxon_label: r.trends for r in results}
    assert recovered["steady"] == pytest.approx((0.30, 0.30), abs=0.02)
    assert recovered["also"] == pytest.approx((-0.20, -0.20), abs=0.02)


def test_a_species_with_the_same_trend_in_both_seasons_does_not_disagree() -> None:
    frame = _rows(trends={"steady": {0: 0.30, 1: 0.30}, "also": {0: -0.20, 1: -0.20}})
    _, kept, lower, upper = phase2h.family_cells(frame, ("A-1", "A-2"))
    assert kept == CELLS
    assert (lower, upper) == (START, START + YEARS - 1)
    results = _results(frame)
    assert len(results) == 2
    assert max(r.root_q for r in results) < 3.0


def test_a_seasonal_level_offset_does_not_disagree_but_shows_as_amplitude() -> None:
    """The design's load-bearing claim: seasonal catchability is a level, and a level cancels."""
    offset = 1.5
    results = _results(
        _rows(
            trends={"steady": {0: 0.30, 1: 0.30}, "also": {0: -0.20, 1: -0.20}},
            offsets={"A-2": offset},
        )
    )
    assert len(results) == 2
    assert max(r.root_q for r in results) < 3.0
    assert [abs(r.amplitude) for r in results] == pytest.approx([offset, offset], abs=0.05)


def test_opposite_trends_between_seasons_raise_the_disagreement() -> None:
    results = _results(_rows(trends={"split": {0: 0.40, 1: -0.40}}))
    assert len(results) == 1
    assert results[0].root_q > 5.0


def test_a_species_missing_a_season_is_dropped_rather_than_compared_on_fewer() -> None:
    frame = _rows(trends={"both": {0: 0.2, 1: 0.2}, "one": {0: 0.2, 1: 0.2}}).filter(
        ~((pl.col("taxon_label") == "one") & (pl.col("survey_unit") == "A-2"))
    )
    assert [r.taxon_label for r in _results(frame)] == ["both"]


def test_the_pair_correlation_is_one_when_the_seasons_rank_species_alike() -> None:
    frame = _rows(
        trends={
            "up": {0: 0.40, 1: 0.38},
            "flat": {0: 0.00, 1: 0.02},
            "down": {0: -0.40, 1: -0.38},
        }
    )
    cells, _, _, _ = phase2h.family_cells(frame, ("A-1", "A-2"))
    trends = phase2h.season_trends(phase2h.season_series(cells))
    assert phase2h.pair_correlation(trends, ("A-1", "A-2")) == pytest.approx(1.0)


def test_the_footprint_is_intersected_and_the_year_span_is_the_overlap() -> None:
    # A cell only the first season ever sampled, and three years only the second one has.
    frame = _rows(trends={"steady": {0: 0.2, 1: 0.2}}).filter(
        ~(pl.col("site_id") == "A-2:5")
        & ~(
            (pl.col("survey_unit") == "A-1")
            & (pl.col("period_start").dt.year() > START + YEARS - 4)
        )
    )
    cells, kept, lower, upper = phase2h.family_cells(frame, ("A-1", "A-2"))
    assert kept == CELLS - 1
    assert (lower, upper) == (START, START + YEARS - 4)
    assert cells["year"].max() == START + YEARS - 4


def test_a_family_whose_footprint_is_too_small_is_dropped_with_its_reason() -> None:
    result = phase2h.family_result(
        _rows(trends={"steady": {0: 0.2, 1: 0.2}}, cells=4), "tiny", ("A-1", "A-2")
    )
    assert not result.coverage.passes
    assert result.coverage.dropped is not None
    assert "shared cells" in result.coverage.dropped


def test_a_family_with_too_few_species_is_dropped_and_says_how_many() -> None:
    result = phase2h.family_result(
        _rows(trends={"steady": {0: 0.2, 1: 0.2}}), "thin", ("A-1", "A-2")
    )
    assert not result.coverage.passes
    assert result.coverage.dropped is not None
    assert "under 20" in result.coverage.dropped


def test_the_split_half_control_is_quiet_on_a_clean_trend() -> None:
    """Odd and even years share the trend, so their standardised difference is about one."""
    frame = _rows(trends={f"s{i}": {0: 0.1 * i, 1: 0.1 * i} for i in range(6)})
    cells, _, _, _ = phase2h.family_cells(frame, ("A-1", "A-2"))
    median = phase2h.split_half_control(cells, "A-1")
    assert median is not None
    assert median < phase2h.CONTROL_BAR


def test_the_split_half_control_returns_none_when_a_half_cannot_clear_the_floor() -> None:
    frame = _rows(trends={"steady": {0: 0.2, 1: 0.2}}).filter(
        pl.col("period_start").dt.year() < START + 2 * phase2h.CONTROL_MIN_YEARS - 4
    )
    cells, _, _, _ = phase2h.family_cells(frame, ("A-1", "A-2"))
    assert phase2h.split_half_control(cells, "A-1") is None
