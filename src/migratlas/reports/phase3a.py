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


@dataclass(frozen=True, slots=True)
class MarineSkill:
    """One survey's verdict, with the construction facts the note must carry."""

    survey: str
    years: int
    species: int
    columns: str
    skill: Skill


MIN_MARINE_YEARS: Final = 20
"""Prediction 3's own scope: units with at least twenty years."""

MIN_REFERENCE_YEARS: Final = 5
"""A species contributes only if its train-era reference stands on at least this many years."""


def _species_anomalies(series: pl.DataFrame, train_years: set[int]) -> pl.DataFrame:
    """Per-year cross-species mean latitude anomaly, referenced to the train era alone.

    Each species' reference is its own train-era mean — full-period references would leak the
    test years into the response's construction, the same leak the harness closes for the
    covariates. Species without MIN_REFERENCE_YEARS train-era years contribute nothing.
    """
    references = (
        series.filter(pl.col("year").is_in(sorted(train_years)))
        .group_by("taxon_key")
        .agg(reference=pl.col("mean_latitude").mean(), reference_years=pl.len())
        .filter(pl.col("reference_years") >= MIN_REFERENCE_YEARS)
    )
    return (
        series.join(references, on="taxon_key")
        .with_columns(anomaly=pl.col("mean_latitude") - pl.col("reference"))
        .group_by("year")
        .agg(anomaly=pl.col("anomaly").mean(), species=pl.col("taxon_key").n_unique())
        .sort("year")
    )


def _haul_temperatures() -> pl.DataFrame:
    """Per survey-year means of the in-situ temperatures, keyed like phase1b's units."""
    hauls = scan_dataset("driver_samples", source_id="fishglob").collect()
    return (
        hauls.with_columns(
            survey=pl.col("site_id").str.split(":").list.first(),
            year=pl.col("period_start").dt.year(),
        )
        .group_by("survey", "year", "variable")
        .agg(pl.col("value").mean())
        .pivot("variable", index=["survey", "year"], values="value")
    )


def marine() -> tuple[list[MarineSkill], int]:
    """Every qualifying survey's hindcast, and the count excluded for gear changes."""
    from migratlas.metrics import range as range_metrics  # noqa: PLC0415 -- report sibling
    from migratlas.models.skill import era_split  # noqa: PLC0415 -- only marine needs it here
    from migratlas.reports import phase1b  # noqa: PLC0415 -- report sibling

    cells = range_metrics.to_cells(phase1b.survey_unit(phase1b.load()))
    temperatures = _haul_temperatures()

    results: list[MarineSkill] = []
    gear_excluded = 0
    for (unit,), survey in cells.group_by(["survey_unit"], maintain_order=True):
        restricted, footprint = range_metrics.consistent_footprint(survey)
        if footprint.cells < range_metrics.MIN_CELLS:
            continue
        # The trend fit absorbs a gear change with a break term; the registered model class
        # has none, and a level step in the response reads as skill or destroys it. Excluded
        # rather than modeled, per §2.
        if phase1b.gear_change_year(restricted) is not None:
            gear_excluded += 1
            continue
        series = range_metrics.centroids(restricted)
        if series.is_empty():
            continue

        drivers = temperatures.filter(pl.col("survey") == str(unit))
        sst_years = drivers.drop_nulls("sea_surface_temperature")["year"].to_list()
        sbt_years = (
            drivers.drop_nulls("sea_bottom_temperature")["year"].to_list()
            if "sea_bottom_temperature" in drivers.columns
            else []
        )
        # Both temperatures when the survey measured both; the water it did measure when not.
        # Fixed here, blind, so no survey's columns are chosen after seeing its skill.
        use_sbt = len(sbt_years) >= MIN_MARINE_YEARS
        driver_years = set(sst_years) & set(sbt_years) if use_sbt else set(sst_years)
        years = sorted(set(series["year"].to_list()) & driver_years)
        if len(years) < MIN_MARINE_YEARS:
            continue

        split = era_split(len(years))
        if split is None:
            continue
        train_years = {years[i] for i in split.train}
        response = _species_anomalies(series.filter(pl.col("year").is_in(years)), train_years)
        response = response.filter(pl.col("year").is_in(years)).sort("year")
        if response.height != len(years):
            continue

        columns = ["sea_surface_temperature"] + (["sea_bottom_temperature"] if use_sbt else [])
        x = (
            drivers.filter(pl.col("year").is_in(years))
            .sort("year")
            .select(columns)
            .to_numpy()
            .astype(float)
        )
        y = response["anomaly"].to_numpy().astype(float)
        verdict = hindcast(x, y, seed=SEED)
        if verdict is None:
            continue
        results.append(
            MarineSkill(
                survey=str(unit),
                years=len(years),
                species=int(np.median(response["species"].to_numpy())),
                columns="+".join(columns),
                skill=verdict,
            )
        )
        log.info("%s: %d years, skill %+.3f", unit, len(years), verdict.score)
    return results, gear_excluded


def render_marine() -> str:
    """Prediction 3's grade, and the marine map's counts."""
    results, gear_excluded = marine()
    significant = sum(1 for r in results if r.skill.significant)
    passed = results and significant >= len(results) / 2
    scores = sorted(r.skill.score for r in results)
    med = scores[len(scores) // 2] if scores else float("nan")
    return "\n".join(
        [
            f"Surveys fitted: {len(results)} (seed {SEED}); {gear_excluded} excluded for a "
            f"gear change inside the span, per the registration's comparability rule.",
            f"Prediction 3 ({'GRADED TRUE' if passed else 'GRADED FALSE'}): haul temperature "
            f"carries significant positive skill in {significant} of {len(results)} units "
            f"with >= {MIN_MARINE_YEARS} years, against the registered bar of half.",
            f"Median skill across fitted surveys: {med:+.3f}. Chance bar for "
            f"{len(results)} units: {binomial_bar(len(results))}.",
        ]
    )


@dataclass(frozen=True, slots=True)
class HerdSkill:
    """One herd's verdict, or the reason it has none."""

    herd: str
    years: int
    columns: str
    skill: Skill | None
    excluded: str = ""


MIN_HERD_ANIMALS: Final = 10
"""A herd-year speaks only when at least this many animals stand behind it — the same floor
the displacement-flat finding's scope names."""

WINTER_MONTHS: Final = (1, 2, 3)


def herds() -> list[HerdSkill]:
    """Prediction 4's fits: displacement against green-up and snow, per herd."""
    from migratlas.drivers.era5_land import BOX_DEG, herd_centroid  # noqa: PLC0415
    from migratlas.reports import phase1h  # noqa: PLC0415 -- report sibling

    greenup = _monthly("pku_gimms_ndvi")
    snow = _monthly("era5_land")

    results: list[HerdSkill] = []
    for herd in phase1h.SOURCES:
        rows = phase1h.seasons(herd)
        yearly = (
            pl.DataFrame(
                {
                    "year": [s.year for s in rows],
                    "displacement": [s.displacement_km for s in rows],
                }
            )
            .group_by("year")
            .agg(displacement=pl.col("displacement").median(), animals=pl.len())
            .filter(pl.col("animals") >= MIN_HERD_ANIMALS)
        )

        centre = herd_centroid(herd)
        cells = greenup.filter(
            (pl.col("latitude") - centre.latitude).abs() <= BOX_DEG,
            (pl.col("longitude") - centre.longitude).abs() <= BOX_DEG,
        )
        green_years = cells.group_by("year").agg(greenup=pl.col("value").mean())
        winter = (
            snow.filter(pl.col("site_id") == herd, pl.col("month").is_in(WINTER_MONTHS))
            .group_by("year")
            .agg(snow=pl.col("value").mean())
        )

        # Green-up when the herd's box has dated cells; snow always. Fixed blind: a polar range
        # whose NDVI never clears the metric's own refusals fits on the snow it does have.
        columns = (["greenup"] if green_years.height > 0 else []) + ["snow"]
        unit = yearly.join(winter, on="year")
        if "greenup" in columns:
            unit = unit.join(green_years, on="year")
        unit = unit.sort("year")

        verdict = hindcast(
            unit.select(columns).to_numpy().astype(float),
            unit["displacement"].to_numpy().astype(float),
            seed=SEED,
        )
        results.append(
            HerdSkill(
                herd=herd,
                years=unit.height,
                columns="+".join(columns),
                skill=verdict,
                excluded="" if verdict else "below the registration's own 15-year floor",
            )
        )
        log.info("%s: %d herd-years, columns %s", herd, unit.height, "+".join(columns))
    return results


def render_herds() -> str:
    """Prediction 4's grade: the herds must show nothing, and honestly."""
    results = herds()
    fitted = [r for r in results if r.skill is not None]
    lines = []
    for r in results:
        if r.skill is None:
            lines.append(f"{r.herd}: not fitted — {r.years} usable years, {r.excluded}.")
        else:
            lines.append(
                f"{r.herd}: skill {r.skill.score:+.3f} against a null bar of "
                f"{r.skill.null_threshold:+.3f} ({r.columns}, {r.years} years) — "
                f"{'SIGNIFICANT' if r.skill.significant else 'not significant'}."
            )
    none_significant = all(not r.skill.significant for r in fitted if r.skill)
    if fitted:
        grade = "GRADED TRUE" if none_significant else "GRADED FALSE"
        lines.append(
            f"Prediction 4 ({grade}): displacement shows "
            f"{'no' if none_significant else ''} significant skill in "
            f"{'any' if none_significant else 'a'} fitted herd."
        )
    else:
        lines.append("Prediction 4 (UNGRADEABLE): no herd cleared the year floor.")
    return "\n".join(lines)


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
