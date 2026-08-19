"""Phase 3d: the dress rehearsal — would the standing prediction have worked?

`docs/methods/phase3d-rehearsal.md` binds every choice here. For each target autumn 2017-2024:
fit the registered response class on years strictly before the target, weather columns only
(the target season's modes are unknowable at issue time), then predict the target from SEAS5's
June issue and grade against what the radar observed. All 143 stations, no selection — the
stations Phase 3a found significant were selected on these same years, and grading them alone
would be selection dressed as validation.
"""

import logging
from dataclasses import dataclass
from statistics import median
from typing import Final

import numpy as np
import polars as pl

from migratlas.evidence import EvidenceType, spec_for
from migratlas.lake.reader import scan_dataset
from migratlas.metrics.phenology import passage_quantiles
from migratlas.models.skill import LAMBDAS, _loo_error, fit_ridge
from migratlas.reports.phase1 import AUTUMN, MIN_COVERAGE, MIN_NIGHTS, SPRING, load_conus_nights
from migratlas.reports.phase3a import (
    PRE_SEASON_MONTHS,
    SEASON_MONTHS,
    WEATHER_COLUMNS,
    _covariates,
    binomial_bar,
)

log = logging.getLogger(__name__)

SEED: Final = 20260819
TARGET_YEARS: Final = tuple(range(2017, 2025))
MIN_TRAIN_YEARS: Final = 10
REPAIRINGS: Final = 1000
MIN_CORRELATION_POINTS: Final = 2
"""A correlation over two points is a line through them, not a measurement."""


@dataclass(frozen=True, slots=True)
class StationRehearsal:
    """One station's eight blind grades, and the null they are judged against."""

    station_id: str
    targets: int
    skill: float
    null_threshold: float
    significant: bool
    driver_correlation: float
    """SEAS5's June-issued season temperature against the observed one, over the targets."""


def _forecast_covariates() -> pl.DataFrame:
    """Per station-year forecast columns from the SEAS5 rows, June issues only."""
    rows = (
        scan_dataset("driver_samples", source_id="seas5")
        .collect()
        .with_columns(
            year=pl.col("period_start").dt.year(),
            month=pl.col("period_start").dt.month(),
        )
    )

    def season_mean(variable: str, months: tuple[int, ...], name: str) -> pl.DataFrame:
        return (
            rows.filter(pl.col("variable") == variable, pl.col("month").is_in(months))
            .group_by("site_id", "year")
            .agg(pl.col("value").mean().alias(name))
        )

    season = SEASON_MONTHS["autumn"]
    pre = PRE_SEASON_MONTHS["autumn"]
    out = season_mean("seas5_air_temperature_2m", season, "temp_season")
    out = out.join(season_mean("seas5_air_temperature_2m", pre, "temp_pre"), on=["site_id", "year"])
    out = out.join(
        season_mean("seas5_total_precipitation", season, "precip_season"), on=["site_id", "year"]
    )
    return out.rename({"site_id": "station_id"})


@dataclass(frozen=True, slots=True)
class _TargetFit:
    """One rolling origin's fitted artifacts: the model never depends on the pairing."""

    year: int
    observed: float
    weights: np.ndarray
    centre: np.ndarray
    scale: np.ndarray
    climatology: float

    def predict(self, x_target: np.ndarray) -> float:
        standardised = (x_target - self.centre) / self.scale
        return float(np.concatenate([[1.0], standardised]) @ self.weights)


def _fit_target(x_train: np.ndarray, y_train: np.ndarray, year: int, observed: float) -> _TargetFit:
    """The registered class, fit once per rolling origin."""
    centre = x_train.mean(axis=0)
    scale = x_train.std(axis=0)
    scale[scale == 0.0] = 1.0
    standardised = (x_train - centre) / scale
    errors = [_loo_error(standardised, y_train, lam) for lam in LAMBDAS]
    weights = fit_ridge(standardised, y_train, LAMBDAS[int(np.argmin(errors))])
    return _TargetFit(
        year=year,
        observed=observed,
        weights=weights,
        centre=centre,
        scale=scale,
        climatology=float(y_train.mean()),
    )


def rehearsal() -> list[StationRehearsal]:
    """Every station's rolling-origin grades, exactly once."""
    nights = load_conus_nights()
    quantiles = (
        passage_quantiles(
            nights,
            spec_for(EvidenceType.FLUX),
            seasons=[SPRING, AUTUMN],
            quantiles=(0.5,),
            min_coverage=MIN_COVERAGE,
            min_observations=MIN_NIGHTS,
        )
        .drop_nulls("q50_doy")
        .filter(pl.col("season") == "autumn")
    )
    observed = _covariates("autumn")
    forecast = _forecast_covariates()
    rng = np.random.default_rng(SEED)

    results: list[StationRehearsal] = []
    for (station,), group in quantiles.group_by(["station_id"], maintain_order=True):
        history = group.join(observed, on=["station_id", "year"]).sort("year")
        targets = history.filter(pl.col("year").is_in(TARGET_YEARS)).join(
            forecast, on=["station_id", "year"], suffix="_fc"
        )
        if targets.is_empty():
            continue

        fits: list[_TargetFit] = []
        forecast_rows: list[np.ndarray] = []
        observed_temp: list[float] = []
        forecast_temp: list[float] = []
        for target in targets.sort("year").to_dicts():
            train = history.filter(pl.col("year") < target["year"])
            if train.height < MIN_TRAIN_YEARS:
                continue
            fits.append(
                _fit_target(
                    train.select(WEATHER_COLUMNS).to_numpy().astype(float),
                    train["q50_doy"].to_numpy().astype(float),
                    int(target["year"]),
                    float(target["q50_doy"]),
                )
            )
            forecast_rows.append(
                np.array([target[f"{c}_fc"] for c in WEATHER_COLUMNS], dtype=float)
            )
            observed_temp.append(float(target["temp_season"]))
            forecast_temp.append(float(target["temp_season_fc"]))
        if len(fits) < len(TARGET_YEARS) - 2:
            continue

        matrix = np.array(forecast_rows)
        errors = [(f.observed - f.predict(matrix[i])) ** 2 for i, f in enumerate(fits)]
        baselines = [(f.observed - f.climatology) ** 2 for f in fits]
        base = float(np.mean(baselines))
        skill = 1.0 - float(np.mean(errors)) / base if base > 0 else 0.0

        # The null re-pairs each target with the wrong years' forecasts. The fits are reused --
        # a model trained on years before the target cannot depend on which forecast it is
        # later shown -- so a re-pairing is a dot product, not a refit.
        null_scores = np.empty(REPAIRINGS)
        for index in range(REPAIRINGS):
            # "The wrong years' forecasts", literally: reject any draw that hands a target its
            # own forecast back, or the null would contain diluted copies of the real score.
            order = rng.permutation(len(fits))
            while np.any(order == np.arange(len(fits))):
                order = rng.permutation(len(fits))
            null_errors = [
                (f.observed - f.predict(matrix[wrong])) ** 2
                for f, wrong in zip(fits, order, strict=True)
            ]
            null_scores[index] = 1.0 - float(np.mean(null_errors)) / base if base > 0 else 0.0
        threshold = float(np.percentile(null_scores, 95.0))

        correlation = (
            float(np.corrcoef(observed_temp, forecast_temp)[0, 1])
            if len(observed_temp) > MIN_CORRELATION_POINTS and np.std(forecast_temp) > 0
            else float("nan")
        )
        results.append(
            StationRehearsal(
                station_id=str(station),
                targets=len(fits),
                skill=skill,
                null_threshold=threshold,
                significant=skill > threshold,
                driver_correlation=correlation,
            )
        )
    log.info("rehearsal: %d stations graded", len(results))
    return results


def render() -> str:
    """Every registered prediction graded, the driver calibration first."""
    results = rehearsal()
    if not results:
        return "No station carried enough history and forecasts to grade."

    correlations = [r.driver_correlation for r in results if not np.isnan(r.driver_correlation)]
    driver_median = median(correlations) if correlations else float("nan")
    driver_ok = bool(correlations) and driver_median > 0

    significant = sum(1 for r in results if r.significant)
    bar = binomial_bar(len(results))
    beats_chance = significant > bar
    skill_median = median(r.skill for r in results)

    def grade(passed: bool) -> str:  # noqa: FBT001 -- a grade is a boolean by nature
        return "GRADED TRUE" if passed else "GRADED FALSE"

    lines = [
        f"Stations graded: {len(results)} (targets 2017-2024, June issues, seed {SEED}).",
        f"Driver calibration: SEAS5 June-issued season temperature vs observed, map-median "
        f"correlation {driver_median:+.3f} over {len(correlations)} stations -- "
        f"{'PASSES' if driver_ok else 'FAILS'}.",
    ]
    if not driver_ok:
        lines.append(
            "Prediction 3 (GRADED FALSE), and per the registration predictions 1-2 are "
            "UNINTERPRETED: the verdict below is about the forecast, not about migration."
        )
    else:
        lines.append(f"Prediction 3 ({grade(driver_ok)}): the driver carries signal.")
    lines += [
        f"Prediction 1 ({grade(not beats_chance)}): the full pipeline "
        f"{'beats' if beats_chance else 'does not beat'} chance -- {significant} of "
        f"{len(results)} stations significant against a bar of {bar}. Median skill "
        f"{skill_median:+.3f}.",
        "#57 licence: "
        + (
            "GRANTED -- the rehearsal beat chance."
            if beats_chance
            else "REFUSED -- the standing prediction does not go live."
        ),
    ]
    return "\n".join(lines)
