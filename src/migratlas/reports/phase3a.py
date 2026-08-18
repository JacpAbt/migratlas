"""Phase 3a, the aerial half: the registered hindcasts, and the predictions they grade.

Everything discretionary was fixed before this module ran — the design in
`docs/methods/phase3a-skill.md`, the harness in `models/skill.py`, the covariate list and
season windows here, the seed below. The test era is touched once, by `aerial()`, and the
numbers it returns are appended to the method note with every prediction graded, whichever way
they land.

The covariate list, fixed per the registration's §2 and named here so the note can quote it:
seasonal-mean 2 m temperature, pre-season-mean 2 m temperature (June-July for autumn, the
window Phase 2a's response function already fitted on; January-February for spring, the same
distance ahead of the season's gate), seasonal-mean total precipitation, and the seasonal means
of the four modes (ONI, NAO, AO, PDO). Seven columns against a minimum of ten training years.
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
from migratlas.models.skill import Skill, hindcast
from migratlas.reports.phase1 import AUTUMN, MIN_COVERAGE, MIN_NIGHTS, SPRING, load_conus_nights

log = logging.getLogger(__name__)

# Fixed before any fit, like everything else in this file. The date the registration landed.
SEED: Final = 20260818

SEASON_MONTHS: Final[dict[str, tuple[int, ...]]] = {
    "spring": (3, 4, 5, 6),
    "autumn": (8, 9, 10, 11),
}
PRE_SEASON_MONTHS: Final[dict[str, tuple[int, ...]]] = {
    "spring": (1, 2),
    "autumn": (6, 7),
}
INDEX_NAMES: Final = ("oni", "nao", "ao", "pdo")
WEATHER_COLUMNS: Final = ("temp_season", "temp_pre", "precip_season")
COLUMNS: Final = (*WEATHER_COLUMNS, *INDEX_NAMES)

# The map-level null: with no skill anywhere, each unit is significant with this probability.
FALSE_POSITIVE_RATE: Final = 0.05


@dataclass(frozen=True, slots=True)
class StationSkill:
    """One station-season's three verdicts: the registered model and its two halves."""

    station_id: str
    season: str
    years: int
    full: Skill
    weather_only: Skill
    indices_only: Skill


@dataclass(frozen=True, slots=True)
class SeasonVerdict:
    """One season's aerial map, with the counts the predictions grade."""

    season: str
    stations: int
    significant: int
    binomial_bar: int
    """Significant stations above this count cannot be the 5% false-positive rate alone."""
    median_skill: float


def binomial_bar(units: int, rate: float = FALSE_POSITIVE_RATE) -> int:
    """The 95th percentile of Binomial(units, rate): the count chance alone reaches.

    Exact, by accumulating the mass — the counts are small and scipy was never a dependency.
    """
    probabilities = np.zeros(units + 1)
    for k in range(units + 1):
        log_mass = _log_choose(units, k) + k * np.log(rate) + (units - k) * np.log1p(-rate)
        probabilities[k] = np.exp(log_mass)
    cumulative = np.cumsum(probabilities)
    return int(np.searchsorted(cumulative, 0.95))


def _log_choose(n: int, k: int) -> float:
    from math import lgamma  # noqa: PLC0415 -- one function, stdlib

    return lgamma(n + 1) - lgamma(k + 1) - lgamma(n - k + 1)


def _monthly(source_id: str) -> pl.DataFrame:
    frame = scan_dataset("driver_samples", source_id=source_id).collect()
    return frame.with_columns(
        year=pl.col("period_start").dt.year(),
        month=pl.col("period_start").dt.month(),
    )


def _season_mean(
    frame: pl.DataFrame, months: tuple[int, ...], variable: str, name: str, *, by_site: bool
) -> pl.DataFrame:
    keys = ["site_id", "year"] if by_site else ["year"]
    return (
        frame.filter(pl.col("variable") == variable, pl.col("month").is_in(months))
        .group_by(keys)
        .agg(pl.col("value").mean().alias(name))
    )


def _covariates(season: str) -> pl.DataFrame:
    """One row per station-year with the seven registered columns."""
    era = _monthly("era5")
    idx = _monthly("noaa_climate_indices")
    months = SEASON_MONTHS[season]
    out = _season_mean(era, months, "air_temperature_2m", "temp_season", by_site=True)
    out = out.join(
        _season_mean(
            era, PRE_SEASON_MONTHS[season], "air_temperature_2m", "temp_pre", by_site=True
        ),
        on=["site_id", "year"],
    )
    out = out.join(
        _season_mean(era, months, "total_precipitation", "precip_season", by_site=True),
        on=["site_id", "year"],
    )
    for name in INDEX_NAMES:
        out = out.join(_season_mean(idx, months, name, name, by_site=False), on="year")
    return out.rename({"site_id": "station_id"})


def aerial() -> list[StationSkill]:
    """Every station-season's hindcast, through the registered harness, exactly once."""
    nights = load_conus_nights()
    quantiles = passage_quantiles(
        nights,
        spec_for(EvidenceType.FLUX),
        seasons=[SPRING, AUTUMN],
        quantiles=(0.5,),
        min_coverage=MIN_COVERAGE,
        min_observations=MIN_NIGHTS,
    ).drop_nulls("q50_doy")

    results: list[StationSkill] = []
    for season in ("spring", "autumn"):
        rows = quantiles.filter(pl.col("season") == season).join(
            _covariates(season), on=["station_id", "year"]
        )
        for (station,), group in rows.group_by(["station_id"], maintain_order=True):
            unit = group.sort("year")
            y = unit["q50_doy"].to_numpy().astype(float)
            x = unit.select(COLUMNS).to_numpy().astype(float)
            full = hindcast(x, y, seed=SEED)
            if full is None:
                continue
            weather = hindcast(x[:, : len(WEATHER_COLUMNS)], y, seed=SEED)
            modes = hindcast(x[:, len(WEATHER_COLUMNS) :], y, seed=SEED)
            if weather is None or modes is None:  # unreachable: the split sees only len(y)
                continue
            results.append(
                StationSkill(
                    station_id=str(station),
                    season=season,
                    years=len(y),
                    full=full,
                    weather_only=weather,
                    indices_only=modes,
                )
            )
        log.info("%s: %d station fits", season, sum(1 for r in results if r.season == season))
    return results


def verdicts(results: list[StationSkill]) -> list[SeasonVerdict]:
    out = []
    for season in ("spring", "autumn"):
        units = [r for r in results if r.season == season]
        significant = sum(1 for r in units if r.full.significant)
        out.append(
            SeasonVerdict(
                season=season,
                stations=len(units),
                significant=significant,
                binomial_bar=binomial_bar(len(units)),
                median_skill=median(r.full.score for r in units) if units else float("nan"),
            )
        )
    return out


def render() -> str:
    """The numbers for the method note's results section, every prediction graded."""
    results = aerial()
    seasons = {v.season: v for v in verdicts(results)}
    spring, autumn = seasons["spring"], seasons["autumn"]

    conditioned = [r for r in results if r.indices_only.significant]

    def grade(passed: bool) -> str:  # noqa: FBT001 -- a grade is a boolean by nature
        return "GRADED TRUE" if passed else "GRADED FALSE"

    # An empty season is a pipeline fact, not a scientific verdict: the first run of this
    # module printed GRADED FALSE over zero spring units because the lake's ERA5 had never
    # been fetched for January-February, and a grade earned that way would be a lie.
    if spring.stations == 0 or autumn.stations == 0:
        p1 = "UNGRADEABLE: a season fitted zero units, which is a data gap, not a verdict"
        p2 = p1
    else:
        p1 = grade(spring.significant > spring.binomial_bar)
        p2 = grade(spring.median_skill > autumn.median_skill)
    if conditioned:
        marginal = median(r.full.score - r.indices_only.score for r in conditioned)
        weather_alone = median(r.weather_only.score for r in conditioned)
        p5 = (
            f"Prediction 5 ({grade(marginal < weather_alone)}): at the {len(conditioned)} "
            f"station-seasons where the modes alone predict, the weather's marginal "
            f"contribution over the modes is {marginal:+.3f} at the median against "
            f"{weather_alone:+.3f} solo."
        )
    else:
        p5 = (
            "Prediction 5 (UNGRADEABLE): the modes alone predict nowhere, so the comparison "
            "has no stations to run on."
        )

    return "\n".join(
        [
            f"Stations fitted: {spring.stations} spring, {autumn.stations} autumn "
            f"(seed {SEED}, columns {', '.join(COLUMNS)}).",
            f"Prediction 1 ({p1}): spring significant at {spring.significant} of "
            f"{spring.stations} stations against a chance bar of {spring.binomial_bar}.",
            f"Prediction 2 ({p2}): median spring skill {spring.median_skill:+.3f} vs autumn "
            f"{autumn.median_skill:+.3f}.",
            p5,
            f"Autumn for the record: {autumn.significant} of {autumn.stations} significant "
            f"against a chance bar of {autumn.binomial_bar}.",
        ]
    )
