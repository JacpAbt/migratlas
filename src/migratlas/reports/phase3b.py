"""Phase 3b: the registered heterogeneity fits, on the longest single-gear segments.

Everything discretionary is in `docs/methods/phase3b-marine-scale.md`, fixed before any trend
was computed. The unit is a survey's longest unbroken gear segment (ties toward the earlier
one, twenty years minimum), so no break term exists anywhere in this module — the segment is
the break handling.
"""

import logging
from dataclasses import dataclass
from typing import Final

import numpy as np
import polars as pl
from scipy import stats

from migratlas.lake.reader import scan_dataset

log = logging.getLogger(__name__)

MIN_SEGMENT_YEARS: Final = 20
MIN_SPECIES_YEARS: Final = 15
MIN_UNITS: Final = 12
"""Below this the phase publishes as a coverage statement and the regression is not run."""
PREDICTED_MINIMUM_UNITS: Final = 15
"""Prediction 4's registered number: the salvage must beat Phase 3a's seven by at least this."""


@dataclass(frozen=True, slots=True)
class Segment:
    """One survey's longest single-gear run."""

    survey: str
    gear: str
    start: int
    end: int
    years: int


@dataclass(frozen=True, slots=True)
class Unit:
    """One fitted unit: the segment and its three registered estimands."""

    segment: Segment
    species: int
    latitude_trend: float
    latitude_ci: float
    temperature_trend: float
    bottom_trend: float | None
    median_depth_m: float


@dataclass(frozen=True, slots=True)
class Regression:
    """The registered cross-unit fit: two slopes, an intercept, and the heterogeneity test."""

    units: int
    q_statistic: float
    q_bar: float
    heterogeneous: bool
    temp_slope: float
    temp_ci: float
    interaction_slope: float
    interaction_ci: float


def gear_by_year(restricted: pl.DataFrame) -> pl.DataFrame:
    """A year's gear: the one with the most hauls, ties broken lexicographically.

    Registered in phase3e-marine-oisst.md §1 after measuring the segments twice returned
    different Baltic answers: `mode().first()` orders ties unstably, and a segmentation that
    changes between runs is an instrument measuring itself.
    """
    return (
        restricted.select("year", gear=pl.col("protocol").str.split("gear=").list.last())
        .group_by("year", "gear")
        .agg(hauls=pl.len())
        .sort(["year", "hauls", "gear"], descending=[False, True, False])
        .group_by("year", maintain_order=True)
        .agg(gear=pl.col("gear").first())
        .sort("year")
    )


def longest_segment(year_gear: list[tuple[int, str]]) -> Segment | None:
    """The longest run of consecutive recorded years under one gear, ties toward the earlier.

    'Consecutive' means consecutive in the record, not the calendar: a survey that skipped a
    year without changing gear did not break its segment — the break is the gear, nothing else.
    """
    if not year_gear:
        return None
    ordered = sorted(year_gear)
    best: tuple[int, int, int, str] | None = None  # (years, -start, end, gear) for max()
    start, gear, count = ordered[0][0], ordered[0][1], 0
    previous = start
    for year, this_gear in [*ordered, (ordered[-1][0] + 1, "\x00sentinel")]:
        if this_gear != gear:
            candidate = (count, -start, previous, gear)
            if best is None or candidate[0] > best[0]:
                best = candidate
            start, gear, count = year, this_gear, 0
        count += 1
        previous = year
    years, neg_start, end, best_gear = best if best is not None else (0, 0, 0, "")
    if years < MIN_SEGMENT_YEARS:
        return None
    return Segment(survey="", gear=best_gear, start=-neg_start, end=end, years=years)


def _trend_per_decade(years: np.ndarray, values: np.ndarray) -> tuple[float, float]:
    result = stats.linregress(years.astype(float), values)
    return float(result.slope * 10), float(result.stderr * 10 * 1.96)


def units() -> tuple[list[Unit], list[str]]:
    """Every qualifying unit's estimands, and the surveys published as coverage instead."""
    from migratlas.metrics import range as range_metrics  # noqa: PLC0415 -- report sibling
    from migratlas.reports import phase1b  # noqa: PLC0415 -- report sibling

    cells = range_metrics.to_cells(phase1b.survey_unit(phase1b.load()))
    temperatures = (
        scan_dataset("driver_samples", source_id="fishglob")
        .collect()
        .with_columns(
            survey=pl.col("site_id").str.split(":").list.first(),
            year=pl.col("period_start").dt.year(),
        )
        .group_by("survey", "year", "variable")
        .agg(pl.col("value").mean())
        .pivot("variable", index=["survey", "year"], values="value")
    )

    fitted: list[Unit] = []
    coverage: list[str] = []
    for (name,), survey in cells.group_by(["survey_unit"], maintain_order=True):
        restricted, footprint = range_metrics.consistent_footprint(survey)
        if footprint.cells < range_metrics.MIN_CELLS:
            continue
        year_gear = gear_by_year(restricted)
        segment = longest_segment([(int(r["year"]), str(r["gear"])) for r in year_gear.to_dicts()])
        if segment is None:
            coverage.append(str(name))
            continue
        segment = Segment(
            survey=str(name),
            gear=segment.gear,
            start=segment.start,
            end=segment.end,
            years=segment.years,
        )
        inside = restricted.filter(pl.col("year").is_between(segment.start, segment.end))

        series = range_metrics.centroids(inside)
        if series.is_empty():
            coverage.append(str(name))
            continue
        latitude = range_metrics.shift_per_decade(
            series, column="mean_latitude", min_years=MIN_SPECIES_YEARS
        )
        if latitude.is_empty():
            coverage.append(str(name))
            continue
        shifts = latitude["per_decade"].to_numpy().astype(float)
        median = float(np.median(shifts))
        ci = (
            1.96 * float(shifts.std(ddof=1)) / np.sqrt(shifts.size)
            if shifts.size > 1
            else float("nan")
        )

        water = temperatures.filter(
            pl.col("survey") == str(name),
            pl.col("year").is_between(segment.start, segment.end),
        ).sort("year")
        surface = water.drop_nulls("sea_surface_temperature")
        if surface.height < MIN_SEGMENT_YEARS:
            coverage.append(str(name))
            continue
        temp_trend, _ = _trend_per_decade(
            surface["year"].to_numpy(), surface["sea_surface_temperature"].to_numpy()
        )
        bottom_trend: float | None = None
        if "sea_bottom_temperature" in water.columns:
            bottom = water.drop_nulls("sea_bottom_temperature")
            if bottom.height >= MIN_SEGMENT_YEARS:
                bottom_trend, _ = _trend_per_decade(
                    bottom["year"].to_numpy(),
                    bottom["sea_bottom_temperature"].to_numpy(),
                )

        depths = inside["site_depth_m"].drop_nulls().to_numpy()
        if depths.size == 0:
            # The registered regression needs the depth interaction; a survey that never
            # recorded haul depth cannot enter it, and NaN poisons the solver silently.
            coverage.append(str(name))
            continue
        depth = float(np.median(depths))
        fitted.append(
            Unit(
                segment=segment,
                species=latitude.height,
                latitude_trend=median,
                latitude_ci=ci,
                temperature_trend=temp_trend,
                bottom_trend=bottom_trend,
                median_depth_m=depth,
            )
        )
        log.info(
            "%s: %d-year segment (%d-%d), %d species, lat %+.3f, sst %+.3f",
            name, segment.years, segment.start, segment.end,
            latitude.height, median, temp_trend,
        )  # fmt: skip
    return fitted, coverage


def regression(fitted: list[Unit]) -> Regression:
    """The one registered cross-unit fit: WLS with a depth interaction, and Cochran's Q."""
    y = np.array([u.latitude_trend for u in fitted])
    weights = np.array([1.0 / max((u.latitude_ci / 1.96) ** 2, 1e-6) for u in fitted])
    temp = np.array([u.temperature_trend for u in fitted])
    depth = np.array([u.median_depth_m for u in fitted])
    depth_std = (depth - depth.mean()) / depth.std(ddof=1)

    pooled = float(np.sum(weights * y) / np.sum(weights))
    q = float(np.sum(weights * (y - pooled) ** 2))
    q_bar = float(stats.chi2.ppf(0.95, len(fitted) - 1))

    design = np.column_stack([np.ones(len(y)), temp, temp * depth_std])
    root = np.sqrt(weights)
    solution, *_ = np.linalg.lstsq(design * root[:, None], y * root, rcond=None)
    residuals = y - design @ solution
    dof = len(y) - design.shape[1]
    sigma2 = float(np.sum(weights * residuals**2) / dof)
    # Pseudoinverse rather than inverse: a degenerate driver (every unit warming identically)
    # collapses a column into the intercept, and the fit should report huge intervals there
    # rather than crash.
    covariance = sigma2 * np.linalg.pinv(design.T @ (design * weights[:, None]))
    errors = np.sqrt(np.diag(covariance))

    return Regression(
        units=len(fitted),
        q_statistic=q,
        q_bar=q_bar,
        heterogeneous=q > q_bar,
        temp_slope=float(solution[1]),
        temp_ci=float(1.96 * errors[1]),
        interaction_slope=float(solution[2]),
        interaction_ci=float(1.96 * errors[2]),
    )


def render() -> str:
    """The registered numbers, every prediction graded, run exactly once."""
    fitted, coverage = units()
    lines = [
        f"Units fitted: {len(fitted)}; coverage rows: {len(coverage)} ({', '.join(coverage)})."
    ]
    if len(fitted) < MIN_UNITS:
        lines.append(
            f"STOP CONDITION: fewer than {MIN_UNITS} units — the phase publishes as a "
            "coverage statement and the regression was not run."
        )
        return "\n".join(lines)

    fit = regression(fitted)

    def grade(passed: bool) -> str:  # noqa: FBT001 -- a grade is a boolean by nature
        return "GRADED TRUE" if passed else "GRADED FALSE"

    positive = fit.temp_slope - fit.temp_ci > 0
    negative_interaction = fit.interaction_slope + fit.interaction_ci < 0
    lines += [
        f"Prediction 1 ({grade(fit.heterogeneous)}): Cochran's Q {fit.q_statistic:.1f} against "
        f"a chi-square bar of {fit.q_bar:.1f} across {fit.units} units.",
        f"Prediction 2 ({grade(positive)}): latitude trend on in-situ warming, slope "
        f"{fit.temp_slope:+.3f} ± {fit.temp_ci:.3f} °lat per °C (both per decade).",
        f"Prediction 3 ({grade(negative_interaction)}): warming x depth interaction "
        f"{fit.interaction_slope:+.3f} ± {fit.interaction_ci:.3f} (depth standardised).",
        f"Prediction 4 ({grade(len(fitted) >= PREDICTED_MINIMUM_UNITS)}): {len(fitted)} "
        f"units entered against Phase 3a's 7; the fragmented surveys are the coverage rows "
        "above.",
    ]
    return "\n".join(lines)
