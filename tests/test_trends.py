import numpy as np
import polars as pl
import pytest

from migratlas.models.trends import (
    LATITUDE_ORIGIN,
    MIN_SITES,
    NotEnoughDataError,
    fit_passage_trend,
)

RNG_SEED = 20260728


def panel(  # noqa: PLR0913 -- a fixture builder, and each knob is a distinct scenario
    *,
    sites: int = 40,
    years: range = range(1995, 2026),
    days_per_decade: float = -1.0,
    break_year: int | None = None,
    break_days: float = 0.0,
    latitude_effect: float = 0.0,
    noise: float = 2.0,
    season: str = "autumn",
) -> pl.DataFrame:
    """A synthetic passage-date panel with a known trend, break and latitude gradient."""
    rng = np.random.default_rng(RNG_SEED)
    midpoint = np.mean(list(years))
    rows = []
    for index in range(sites):
        latitude = 25.0 + 25.0 * index / max(sites - 1, 1)
        # Each site gets its own baseline, which is what the random intercept is for.
        baseline = 250.0 + rng.normal(0, 6)
        slope = days_per_decade + latitude_effect * (latitude - LATITUDE_ORIGIN)
        for year in years:
            decades = (year - midpoint) / 10
            shift = break_days if break_year is not None and year >= break_year else 0.0
            rows.append(
                {
                    "station_id": f"S{index:03d}",
                    "season": season,
                    "year": year,
                    "q50_doy": baseline + slope * decades + shift + rng.normal(0, noise),
                    "station_latitude": latitude,
                }
            )
    return pl.DataFrame(rows)


def test_recovers_a_known_trend() -> None:
    fit = fit_passage_trend(panel(days_per_decade=-1.5))
    assert fit.converged
    assert fit.per_decade.value == pytest.approx(-1.5, abs=0.2)
    assert fit.per_decade.pvalue < 0.01


def test_reports_no_trend_when_there_is_none() -> None:
    fit = fit_passage_trend(panel(days_per_decade=0.0))
    assert abs(fit.per_decade.value) < fit.per_decade.ci95


def test_an_unmodelled_break_masquerades_as_a_trend() -> None:
    """The reason the break term exists at all.

    A flat series with a step at the instrument upgrade must come back as a trend when the step
    is ignored, and as no trend once it is modelled. If this test ever passed both ways, the
    break term would be doing nothing.
    """
    frame = panel(days_per_decade=0.0, break_year=2012, break_days=3.0)

    ignored = fit_passage_trend(frame)
    assert ignored.per_decade.value > 0.5

    modelled = fit_passage_trend(frame, break_year=2012)
    assert abs(modelled.per_decade.value) < 0.3
    assert modelled.break_shift is not None
    assert modelled.break_shift.value == pytest.approx(3.0, abs=0.4)


def test_recovers_a_latitude_gradient() -> None:
    fit = fit_passage_trend(panel(days_per_decade=-1.0, latitude_effect=-0.08))
    assert fit.per_decade_per_degree is not None
    assert fit.per_decade_per_degree.value == pytest.approx(-0.08, abs=0.03)
    # The main effect is the trend at the centring latitude, not the mean over sites.
    assert fit.per_decade.value == pytest.approx(-1.0, abs=0.25)


def test_latitude_can_be_dropped() -> None:
    """Fitting inside a narrow latitude band leaves nothing for the term to explain."""
    fit = fit_passage_trend(panel(), latitude=None)
    assert fit.per_decade_per_degree is None
    assert fit.break_shift is None


def test_between_site_spread_is_reported_in_days() -> None:
    fit = fit_passage_trend(panel(noise=1.0))
    # Sites were drawn with a baseline sd of 6 days.
    assert 3.0 < fit.site_sd < 9.0


def test_too_few_sites_is_refused() -> None:
    with pytest.raises(NotEnoughDataError, match="not enough"):
        fit_passage_trend(panel(sites=MIN_SITES - 1))


def test_a_single_year_is_refused() -> None:
    with pytest.raises(NotEnoughDataError, match="not enough"):
        fit_passage_trend(panel(years=range(2000, 2001)))


def test_two_seasons_at_once_are_refused() -> None:
    """Spring and autumn are different phenomena; pooling them estimates neither."""
    both = pl.concat([panel(season="spring"), panel(season="autumn")])
    with pytest.raises(NotEnoughDataError, match="one season at a time"):
        fit_passage_trend(both)


def test_nulls_are_dropped_not_imputed() -> None:
    frame = panel()
    holed = frame.with_columns(
        q50_doy=pl.when(pl.col("year") == 2005).then(None).otherwise(pl.col("q50_doy"))
    )
    fit = fit_passage_trend(holed)
    assert fit.observations == frame.height - frame.filter(pl.col("year") == 2005).height
