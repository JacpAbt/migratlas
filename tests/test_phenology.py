"""Passage-date quantiles. The properties here are what make a trend estimate meaningful."""

from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from migratlas.evidence import EvidenceType, spec_for
from migratlas.metrics.phenology import (
    NORTHERN_AUTUMN,
    NORTHERN_SPRING,
    MetricNotApplicableError,
    Season,
    passage_quantiles,
)

FLUX = spec_for(EvidenceType.FLUX)


def _series(
    values: dict[int, float],
    *,
    year: int = 2019,
    station: str = "KBGM",
    coverage: float | None = 1.0,
) -> pl.DataFrame:
    """A frame of (day-of-year -> magnitude) for one station-year."""
    start = datetime(year, 1, 1, tzinfo=UTC)
    return pl.DataFrame(
        {
            "station_id": [station] * len(values),
            "timestamp": [start + timedelta(days=doy - 1) for doy in values],
            "magnitude": list(values.values()),
            "coverage_fraction": [coverage] * len(values),
        }
    )


def _flat_season(season: Season, value: float = 100.0, **kwargs: object) -> pl.DataFrame:
    span = range(season.start_doy, season.end_doy + 1)
    return _series(dict.fromkeys(span, value), **kwargs)  # type: ignore[arg-type]


# --- Correctness of the quantile itself --------------------------------------
def test_uniform_passage_puts_the_median_mid_season() -> None:
    """A flat curve must give the midpoint, or the interpolation is skewed."""
    result = passage_quantiles(
        _flat_season(NORTHERN_SPRING), FLUX, seasons=[NORTHERN_SPRING], quantiles=[0.5]
    )
    midpoint = (NORTHERN_SPRING.start_doy + NORTHERN_SPRING.end_doy) / 2
    assert result["q50_doy"][0] == pytest.approx(midpoint, abs=1.0)


def test_all_passage_on_one_night_pins_every_quantile_to_it() -> None:
    values = dict.fromkeys(range(NORTHERN_SPRING.start_doy, NORTHERN_SPRING.end_doy + 1), 0.0)
    values[120] = 5000.0
    result = passage_quantiles(
        _series(values), FLUX, seasons=[NORTHERN_SPRING], quantiles=[0.1, 0.5, 0.9]
    )
    for column in ("q10_doy", "q50_doy", "q90_doy"):
        assert result[column][0] == pytest.approx(120.0, abs=1.0)


def test_quantiles_are_ordered() -> None:
    values = {doy: float(doy % 17) for doy in range(60, 181)}
    result = passage_quantiles(_series(values), FLUX, seasons=[NORTHERN_SPRING])
    assert result["q10_doy"][0] <= result["q50_doy"][0] <= result["q90_doy"][0]


def test_shifting_the_curve_shifts_the_median_by_the_same_amount() -> None:
    """The whole point: a 10-day earlier passage must read as 10 days earlier."""
    base = dict.fromkeys(range(100, 141), 1.0)
    shifted = {doy - 10: 1.0 for doy in range(100, 141)}
    season = Season("test", 60, 180)
    first = passage_quantiles(_series(base), FLUX, seasons=[season], quantiles=[0.5])
    second = passage_quantiles(_series(shifted), FLUX, seasons=[season], quantiles=[0.5])
    assert first["q50_doy"][0] - second["q50_doy"][0] == pytest.approx(10.0, abs=0.5)


def test_interpolation_gives_sub_daily_resolution() -> None:
    """Snapping to whole days would quantise a shift measured in days per decade."""
    values = {100: 1.0, 101: 3.0}
    season = Season("test", 60, 180)
    result = passage_quantiles(
        _series(values), FLUX, seasons=[season], quantiles=[0.5], min_observations=2
    )
    # Half of the total 4.0 is 2.0, reached a quarter of the way into the second night.
    assert result["q50_doy"][0] != int(result["q50_doy"][0])


# --- Guards ------------------------------------------------------------------
def test_thin_seasons_yield_nulls_not_confident_numbers() -> None:
    result = passage_quantiles(
        _series({100: 5.0, 101: 5.0}),
        FLUX,
        seasons=[Season("test", 60, 180)],
        min_observations=20,
    )
    assert result["q50_doy"][0] is None
    assert result["observations"][0] == 2


def test_low_coverage_rows_are_excluded() -> None:
    """A night the instrument mostly missed is not a night with little movement."""
    good = _flat_season(NORTHERN_SPRING, coverage=1.0)
    # A huge value on a badly covered night would otherwise drag the median to it.
    bad = _series({61: 1_000_000.0}, coverage=0.1)
    combined = pl.concat([good, bad])
    result = passage_quantiles(
        combined, FLUX, seasons=[NORTHERN_SPRING], quantiles=[0.5], min_coverage=0.9
    )
    midpoint = (NORTHERN_SPRING.start_doy + NORTHERN_SPRING.end_doy) / 2
    assert result["q50_doy"][0] == pytest.approx(midpoint, abs=1.0)


def test_null_coverage_is_kept_because_unreported_is_not_poor() -> None:
    result = passage_quantiles(
        _flat_season(NORTHERN_SPRING, coverage=None),
        FLUX,
        seasons=[NORTHERN_SPRING],
        quantiles=[0.5],
    )
    assert result["q50_doy"][0] is not None


def test_zero_total_yields_nulls() -> None:
    result = passage_quantiles(
        _flat_season(NORTHERN_SPRING, value=0.0), FLUX, seasons=[NORTHERN_SPRING]
    )
    assert result["q50_doy"][0] is None


def test_presence_only_evidence_is_refused() -> None:
    """TRACK records where an animal was, not how much of anything passed."""
    with pytest.raises(MetricNotApplicableError, match="no value column"):
        passage_quantiles(pl.DataFrame(), spec_for(EvidenceType.TRACK))


def test_out_of_season_rows_are_ignored() -> None:
    values = dict.fromkeys(range(60, 181), 1.0) | {200: 10_000.0}
    result = passage_quantiles(_series(values), FLUX, seasons=[NORTHERN_SPRING], quantiles=[0.5])
    assert result["total"][0] == pytest.approx(121.0)


# --- Grouping ----------------------------------------------------------------
def test_stations_and_years_are_summarised_separately() -> None:
    frames = [
        _flat_season(NORTHERN_SPRING, station=station, year=year)
        for station in ("KBGM", "KABR")
        for year in (2018, 2019)
    ]
    result = passage_quantiles(pl.concat(frames), FLUX, seasons=[NORTHERN_SPRING], quantiles=[0.5])
    assert result.height == 4
    assert set(result["station_id"]) == {"KBGM", "KABR"}
    assert set(result["year"]) == {2018, 2019}


def test_both_seasons_are_returned() -> None:
    frame = pl.concat([_flat_season(NORTHERN_SPRING), _flat_season(NORTHERN_AUTUMN)])
    result = passage_quantiles(frame, FLUX, quantiles=[0.5])
    assert set(result["season"]) == {"spring", "autumn"}
    spring = result.filter(pl.col("season") == "spring")["q50_doy"][0]
    autumn = result.filter(pl.col("season") == "autumn")["q50_doy"][0]
    assert spring < autumn


def test_grouping_can_separate_quantities() -> None:
    """Filtered and unfiltered traffic must not be pooled into one curve."""
    frame = pl.concat(
        [
            _flat_season(NORTHERN_SPRING).with_columns(quantity=pl.lit("filtered")),
            _flat_season(NORTHERN_SPRING).with_columns(quantity=pl.lit("unfiltered")),
        ]
    )
    result = passage_quantiles(
        frame,
        FLUX,
        seasons=[NORTHERN_SPRING],
        quantiles=[0.5],
        group_by=("station_id", "quantity"),
    )
    assert result.height == 2


# --- Season validation -------------------------------------------------------
@pytest.mark.parametrize(("start", "end"), [(0, 100), (100, 60), (1, 400)])
def test_invalid_season_windows_are_refused(start: int, end: int) -> None:
    with pytest.raises(ValueError, match="invalid window"):
        Season("bad", start, end)


def test_default_seasons_do_not_overlap() -> None:
    assert NORTHERN_SPRING.end_doy < NORTHERN_AUTUMN.start_doy
