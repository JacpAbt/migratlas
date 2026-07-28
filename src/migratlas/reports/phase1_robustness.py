"""Does the phenology trend survive the things that could be producing it?

Four specifications for the dual-polarisation break, a placebo window, and a permutation
null. The point is not to find the one right specification -- the upgrade dates are not
publicly available per station -- but to show whether the estimate depends on which one is
chosen. A trend that is stable across all four is a stronger claim than any single
specification, precisely because it does not rest on getting the dates right.
"""

import logging
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING, Final

import numpy as np
import polars as pl

from migratlas.evidence import EvidenceType, spec_for
from migratlas.metrics import breaks
from migratlas.metrics.phenology import Season, passage_quantiles
from migratlas.reports.phase1 import (
    AUTUMN,
    LATITUDE_BANDS,
    MIN_COVERAGE,
    MIN_NIGHTS,
    MIN_YEARS,
    SPRING,
    load_conus_traffic,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

log = logging.getLogger(__name__)

# The rollout ran from the first operational dual-pol radar in early 2011 to fleet
# completion in mid-2013.
ROLLOUT: Final[tuple[date, date]] = (date(2010, 10, 1), date(2013, 12, 31))
TRANSITION: Final[tuple[int, int]] = (2011, 2013)
FLEET_MIDPOINT_YEAR: Final = 2012

RNG_SEED: Final = 20260728
PERMUTATIONS: Final = 200

# Mid-winter nights: same instrument, same window kind, same pipeline, but no migration to
# have a phenology. A trend here of comparable size would mean the pipeline manufactures
# trends, which is decisive in a way the daytime placebo is not.
MIDWINTER: Final = Season("midwinter", 1, 45)

# How close to the window edge counts as clipped. A week: passage-date quantiles move a few
# days per decade, so anything nearer than that is uninformative about timing.
EDGE_DAYS: Final = 7


@dataclass(frozen=True, slots=True)
class Estimate:
    label: str
    stations: int
    days_per_decade: float
    ci95: float

    def __str__(self) -> str:
        return (
            f"{self.label:<34} n={self.stations:>3}  "
            f"{self.days_per_decade:+.2f} +/- {self.ci95:.2f}"
        )


def _mean_ci(slopes: Sequence[float]) -> tuple[float, float]:
    values = np.asarray(slopes, dtype=float)
    if values.size == 0:
        return (float("nan"), float("nan"))
    ci = 1.96 * float(values.std(ddof=1)) / np.sqrt(values.size) if values.size > 1 else 0.0
    return (float(values.mean()), ci)


def _slope(years: np.ndarray, passage: np.ndarray, step: np.ndarray | None) -> float | None:
    """Least-squares trend in days per year, optionally with a level-shift term.

    With ``step`` the design is ``passage ~ 1 + year + post_break``, so the year
    coefficient is the trend net of a one-off jump at the break.
    """
    columns = [np.ones_like(years), years]
    if step is not None and 0 < step.sum() < step.size:
        columns.append(step)
    design = np.column_stack(columns)
    if np.linalg.matrix_rank(design) < design.shape[1]:
        return None
    coefficients, *_ = np.linalg.lstsq(design, passage, rcond=None)
    return float(coefficients[1])


def seasonal_series(
    nights: pl.DataFrame, *, max_year: int, seasons: Sequence[Season] = (SPRING, AUTUMN)
) -> pl.DataFrame:
    """Per station-season-year median passage date, with station latitude attached."""
    quantiles = passage_quantiles(
        nights.filter(pl.col("timestamp").dt.year() <= max_year),
        spec_for(EvidenceType.FLUX),
        seasons=list(seasons),
        quantiles=[0.5],
        min_coverage=MIN_COVERAGE,
        min_observations=MIN_NIGHTS,
    )
    sites = nights.group_by("station_id").agg(pl.col("station_latitude").first())
    return quantiles.filter(pl.col("q50_doy").is_not_null()).join(sites, on="station_id")


def window_truncation(nights: pl.DataFrame, *, max_year: int) -> list[str]:
    """Test whether the autumn window clips passage at low latitudes.

    The hierarchical model's break coefficient is +2.2 days at 24-32N and +0.0 at 42-50N. A
    hardware upgrade cannot do that, so something else is riding on the 2012 dummy in the
    south, and the obvious candidate is the window: 213-334 doy was chosen for northern
    passage, and if southern autumn passage runs past day 334 the q90 has nowhere to go.

    A clipped series shows up as q90 piling up against the window edge. Result: it does not --
    0.0% in every band and era -- so the window is NOT the explanation, and this function stays
    as the record of a refuted hypothesis. The panel-composition test in phase1_hierarchical is
    the one that found the cause.
    """
    quantiles = passage_quantiles(
        nights.filter(pl.col("timestamp").dt.year() <= max_year),
        spec_for(EvidenceType.FLUX),
        seasons=[AUTUMN],
        quantiles=[0.9],
        min_coverage=MIN_COVERAGE,
        min_observations=MIN_NIGHTS,
    )
    sites = nights.group_by("station_id").agg(pl.col("station_latitude").first())
    frame = (
        quantiles.filter(pl.col("q90_doy").is_not_null())
        .join(sites, on="station_id")
        .with_columns(
            clipped=pl.col("q90_doy") >= AUTUMN.end_doy - EDGE_DAYS,
            era=pl.when(pl.col("year") >= FLEET_MIDPOINT_YEAR)
            .then(pl.lit("post"))
            .otherwise(pl.lit("pre")),
        )
    )

    lines = [
        f"  q90 within {EDGE_DAYS} d of the window end (day {AUTUMN.end_doy}), by band and era:",
        "    band       pre-2012   2012+   n",
    ]
    for low, high in LATITUDE_BANDS:
        band = frame.filter(pl.col("station_latitude").is_between(low, high, closed="left"))
        if band.is_empty():
            continue
        shares = {
            era: band.filter(pl.col("era") == era)["clipped"].to_numpy().mean()
            for era in ("pre", "post")
        }
        lines.append(
            f"    {low}-{high}N     {shares['pre']:>6.1%}  {shares['post']:>6.1%}  {band.height:>5}"
        )
    return lines


def specification_estimates(
    series: pl.DataFrame, break_dates: dict[str, date], season: str
) -> list[Estimate]:
    """The same trend under four treatments of the dual-polarisation break."""
    seasonal = series.filter(pl.col("season") == season)

    specifications: dict[str, list[float]] = {
        "no break term": [],
        "break at detected outage": [],
        f"common break at {FLEET_MIDPOINT_YEAR}": [],
        f"transition {TRANSITION[0]}-{TRANSITION[1]} dropped": [],
    }

    for (station,), group in seasonal.group_by(["station_id"], maintain_order=True):
        if group.height < MIN_YEARS:
            continue
        years = group["year"].to_numpy().astype(float)
        passage = group["q50_doy"].to_numpy().astype(float)

        plain = _slope(years, passage, None)
        if plain is not None:
            specifications["no break term"].append(plain * 10)

        detected = break_dates.get(station)
        if detected is not None:
            step = (years >= detected.year).astype(float)
            value = _slope(years, passage, step)
            if value is not None:
                specifications["break at detected outage"].append(value * 10)

        common = _slope(years, passage, (years >= FLEET_MIDPOINT_YEAR).astype(float))
        if common is not None:
            specifications[f"common break at {FLEET_MIDPOINT_YEAR}"].append(common * 10)

        keep = (years < TRANSITION[0]) | (years > TRANSITION[1])
        if keep.sum() >= MIN_YEARS:
            dropped = _slope(years[keep], passage[keep], None)
            if dropped is not None:
                specifications[f"transition {TRANSITION[0]}-{TRANSITION[1]} dropped"].append(
                    dropped * 10
                )

    estimates: list[Estimate] = []
    for label, slopes in specifications.items():
        mean, ci = _mean_ci(slopes)
        estimates.append(Estimate(label, len(slopes), mean, ci))
    return estimates


def permutation_null(series: pl.DataFrame, season: str) -> tuple[float, float, float]:
    """Mean trend after shuffling year labels within each station.

    Breaks any real time ordering while preserving each station's distribution of passage
    dates, so the observed estimate should sit outside this null if it means anything.
    """
    rng = np.random.default_rng(RNG_SEED)
    seasonal = series.filter(pl.col("season") == season)
    groups = [
        (
            group["year"].to_numpy().astype(float),
            group["q50_doy"].to_numpy().astype(float),
        )
        for (_,), group in seasonal.group_by(["station_id"], maintain_order=True)
        if group.height >= MIN_YEARS
    ]

    means: list[float] = []
    for _ in range(PERMUTATIONS):
        slopes = []
        for years, passage in groups:
            value = _slope(years, rng.permutation(passage), None)
            if value is not None:
                slopes.append(value * 10)
        if slopes:
            means.append(float(np.mean(slopes)))

    null = np.asarray(means)
    return (float(null.mean()), float(np.quantile(null, 0.025)), float(np.quantile(null, 0.975)))


def render(max_year: int = 2025) -> str:
    """Run the robustness battery and render it."""
    nights = load_conus_traffic("night")

    night_series = seasonal_series(nights, max_year=max_year)
    outages = breaks.find_outages(
        nights,
        site_column="station_id",
        time_column="timestamp",
        window=ROLLOUT,
        min_days=4,
        max_days=40,
    )
    break_dates = {o.site: o.start for o in outages}

    out = [
        "Phase 1a robustness",
        "=" * 74,
        f"Window 1995-{max_year}. Detected outages: {len(break_dates)} stations, "
        f"median {int(np.median([o.days for o in outages])) if outages else 0} days.",
        "Detected dates are ONE specification, not ground truth -- see the method note.",
    ]

    for season in ("spring", "autumn"):
        out += ["", "=" * 74, f"{season}: dual-polarisation break sensitivity", "=" * 74]
        for estimate in specification_estimates(night_series, break_dates, season):
            out.append(f"  {estimate}")

    out += [
        "",
        "=" * 74,
        "autumn window truncation, by latitude",
        "=" * 74,
        "  Why: the hierarchical fit puts a +2.2 d instrument break at 24-32N and +0.0 d at",
        "  42-50N. Hardware cannot do that, so something else rides on the 2012 dummy there.",
    ]
    out += window_truncation(nights, max_year=max_year)

    # Placebo 1: the daytime window. Weaker than it first appears -- daytime aerial biomass
    # is not zero (diurnal migrants, and insects especially in autumn), so a daytime trend
    # may be real biology rather than an artefact. Suggestive, not decisive.
    day_series = seasonal_series(load_conus_traffic("day"), max_year=max_year)
    out += ["", "=" * 74, "placebo 1: daytime window, same pipeline", "=" * 74]
    for season in ("spring", "autumn"):
        night = specification_estimates(night_series, break_dates, season)[0]
        day = specification_estimates(day_series, break_dates, season)[0]
        out.append(
            f"  {season:<8} night {night.days_per_decade:+.2f} +/- {night.ci95:.2f}"
            f"   |   day {day.days_per_decade:+.2f} +/- {day.ci95:.2f}"
        )
    out.append("  Daytime biomass is genuinely non-zero, so this is suggestive, not decisive.")

    # Placebo 2: mid-winter nights. Same instrument, same window kind, same pipeline, but no
    # migration to have a phenology. A comparable trend here would be decisive.
    winter = seasonal_series(nights, max_year=max_year, seasons=[MIDWINTER])
    winter_slopes: list[float] = []
    for (_,), group in winter.group_by(["station_id"], maintain_order=True):
        if group.height < MIN_YEARS:
            continue
        value = _slope(
            group["year"].to_numpy().astype(float),
            group["q50_doy"].to_numpy().astype(float),
            None,
        )
        if value is not None:
            winter_slopes.append(value * 10)
    winter_mean, winter_ci = _mean_ci(winter_slopes)
    out += [
        "",
        "=" * 74,
        "placebo 2: mid-winter nights, no migration to time",
        "=" * 74,
        f"  midwinter  n={len(winter_slopes):>3}  {winter_mean:+.2f} +/- {winter_ci:.2f} d/decade",
    ]

    out += ["", "=" * 74, "permutation null: year labels shuffled within station", "=" * 74]
    for season in ("spring", "autumn"):
        mean, low, high = permutation_null(night_series, season)
        out.append(f"  {season:<8} null mean {mean:+.3f}  95% interval [{low:+.2f}, {high:+.2f}]")

    out += [
        "",
        "A trend that survives all four break specifications does not depend on knowing the",
        "upgrade dates. One that does not survive them is a confound, not a finding.",
    ]
    return "\n".join(out)
