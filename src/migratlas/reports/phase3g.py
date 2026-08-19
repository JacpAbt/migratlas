"""Phase 3g: does the water's oxygen sort the movers, where its temperature did not?

`docs/methods/phase3g-oxygen.md` binds everything below: Phase 3e's units clipped to the
biogeochemical era, oxygen read at each unit's own fishing depth, two calibrations that gate
the hypothesis, and one cross-unit fit conditioning oxygen on the warming 3e already measured.

Reuses Phase 3b's machinery rather than restating it -- the segment rule, the footprint, the trend
helper and the weighted-least-squares convention -- so a difference between this and Phase 3e is the
driver and nothing else. The one thing not reused is 3b's `regression`, whose design column is a
warming x depth interaction; §3 registers a different pair of columns, so the fit is written
here and the weights, the Q test and the interval convention are lifted unchanged.
"""

import logging
from dataclasses import dataclass
from typing import Final

import numpy as np
import polars as pl
from scipy import stats

from migratlas.lake.reader import scan_dataset
from migratlas.reports.phase3b import (
    MIN_SEGMENT_YEARS,
    MIN_SPECIES_YEARS,
    MIN_UNITS,
    Segment,
    _trend_per_decade,
    gear_by_year,
    longest_segment,
)

log = logging.getLogger(__name__)

BGC_FIRST_YEAR: Final = 1993
"""The reanalysis begins in January 1993, eleven years after OISST. §1 counted what that costs:
two units, and one of them is the 46-year run Phase 3e recovered."""

PREDICTED_MINIMUM_UNITS: Final = 15
"""Prediction 5, against the 16 counted before the design was fixed."""

OXYGEN_VARIABLE: Final = "cmems_o2_footprint_mean"


@dataclass(frozen=True, slots=True)
class Calibrations:
    """The two gates. Neither is the hypothesis; both must pass before it is read."""

    units: int
    median_oxygen_trend: float
    """C1: deoxygenation should be present. Negative passes."""
    warming_oxygen_correlation: float
    """C2: solubility ties them, so this should be negative. Positive means the sampling is not
    reading oxygen -- wrong depth, wrong footprint, wrong aggregation."""

    @property
    def c1_passes(self) -> bool:
        return self.median_oxygen_trend < 0

    @property
    def c2_passes(self) -> bool:
        return self.warming_oxygen_correlation < 0

    @property
    def both_pass(self) -> bool:
        return self.c1_passes and self.c2_passes


@dataclass(frozen=True, slots=True)
class OxygenUnit:
    """One unit's response and its two drivers, over the biogeochemical era."""

    segment: Segment
    species: int
    latitude_trend: float
    latitude_ci: float
    oxygen_trend: float
    """mmol m-3 per decade at the unit's own fishing depth."""
    warming_trend: float
    read_depth_m: float
    median_depth_m: float


@dataclass(frozen=True, slots=True)
class Fit:
    """The registered cross-unit fit: two standardised slopes and the heterogeneity test."""

    units: int
    q_statistic: float
    q_bar: float
    heterogeneous: bool
    oxygen_slope: float
    oxygen_ci: float
    warming_slope: float
    warming_ci: float


def _by_unit_year(source_id: str, variable: str, alias: str) -> pl.DataFrame:
    """A footprint-mean driver per survey-year, from the ingested monthly rows."""
    return (
        scan_dataset("driver_samples", source_id=source_id)
        .collect()
        .filter(pl.col("variable") == variable)
        .with_columns(year=pl.col("period_start").dt.year())
        .group_by("site_id", "year")
        .agg(pl.col("value").mean().alias(alias), depth=pl.col("depth_m").first())
        .rename({"site_id": "survey"})
    )


def _driver_trends(
    oxygen: pl.DataFrame, warming: pl.DataFrame, name: str, start: int, end: int
) -> tuple[float, float, float] | None:
    """A unit's oxygen and warming trends per decade, and the depth oxygen was read at.

    None where either series is shorter than the segment floor, so the unit goes to coverage rather
    than entering the fit on a driver too short to trend. Both are required: the registered fit
    conditions one on the other and cannot be run on a unit missing either.
    """
    water = oxygen.filter(pl.col("survey") == name, pl.col("year").is_between(start, end)).sort(
        "year"
    )
    heat = warming.filter(pl.col("survey") == name, pl.col("year").is_between(start, end)).sort(
        "year"
    )
    if water.height < MIN_SEGMENT_YEARS or heat.height < MIN_SEGMENT_YEARS:
        return None
    oxygen_trend, _ = _trend_per_decade(water["year"].to_numpy(), water["o2"].to_numpy())
    warming_trend, _ = _trend_per_decade(heat["year"].to_numpy(), heat["sst"].to_numpy())
    return oxygen_trend, warming_trend, float(water["depth"][0])


def units() -> tuple[list[OxygenUnit], list[str], Calibrations]:
    """Every qualifying unit's estimands, the coverage rows, and the two calibrations."""
    from migratlas.metrics import range as range_metrics  # noqa: PLC0415 -- report sibling
    from migratlas.reports import phase1b  # noqa: PLC0415 -- report sibling

    cells = range_metrics.to_cells(phase1b.survey_unit(phase1b.load()))
    oxygen = _by_unit_year("cmems_bgc", OXYGEN_VARIABLE, "o2")
    warming = (
        scan_dataset("driver_samples", source_id="oisst")
        .collect()
        .with_columns(year=pl.col("period_start").dt.year())
        .group_by("site_id", "year")
        .agg(sst=pl.col("value").mean())
        .rename({"site_id": "survey"})
    )

    fitted: list[OxygenUnit] = []
    coverage: list[str] = []
    for (name,), survey in cells.sort("survey_unit").group_by(["survey_unit"], maintain_order=True):
        restricted, footprint = range_metrics.consistent_footprint(survey)
        if footprint.cells < range_metrics.MIN_CELLS:
            continue
        segment = longest_segment(
            [(int(r["year"]), str(r["gear"])) for r in gear_by_year(restricted).to_dicts()]
        )
        if segment is None:
            coverage.append(str(name))
            continue

        start = max(segment.start, BGC_FIRST_YEAR)
        inside = restricted.filter(pl.col("year").is_between(start, segment.end))
        clipped = inside["year"].n_unique()
        if clipped < MIN_SEGMENT_YEARS:
            coverage.append(str(name))
            continue
        clipped_segment = Segment(
            survey=str(name), gear=segment.gear, start=start, end=segment.end, years=clipped
        )

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

        drivers = _driver_trends(oxygen, warming, str(name), start, segment.end)
        if drivers is None:
            coverage.append(str(name))
            continue
        oxygen_trend, warming_trend, read_depth = drivers

        depths = inside["site_depth_m"].drop_nulls().to_numpy()
        if depths.size == 0:
            coverage.append(str(name))
            continue

        fitted.append(
            OxygenUnit(
                segment=clipped_segment,
                species=latitude.height,
                latitude_trend=float(np.median(shifts)),
                latitude_ci=(
                    1.96 * float(shifts.std(ddof=1)) / np.sqrt(shifts.size)
                    if shifts.size > 1
                    else float("nan")
                ),
                oxygen_trend=oxygen_trend,
                warming_trend=warming_trend,
                read_depth_m=read_depth,
                median_depth_m=float(np.median(depths)),
            )
        )
        log.info(
            "%s: %d years (%d-%d), %d species, lat %+.3f, o2 %+.3f at %.0f m, sst %+.3f",
            name, clipped, start, segment.end, latitude.height,
            float(np.median(shifts)), oxygen_trend, read_depth, warming_trend,
        )  # fmt: skip

    oxygen_trends = np.array([u.oxygen_trend for u in fitted])
    warming_trends = np.array([u.warming_trend for u in fitted])
    correlation = (
        float(np.corrcoef(warming_trends, oxygen_trends)[0, 1]) if len(fitted) > 1 else float("nan")
    )
    calibrations = Calibrations(
        units=len(fitted),
        median_oxygen_trend=float(np.median(oxygen_trends)) if fitted else float("nan"),
        warming_oxygen_correlation=correlation,
    )
    return fitted, coverage, calibrations


def fit(fitted: list[OxygenUnit]) -> Fit:
    """`latitude_trend ~ 1 + oxygen_trend + warming_trend`, both drivers standardised.

    Weights, the Q test and the pseudoinverse are Phase 3b's, unchanged. Standardised so the two
    coefficients are comparable to each other, which is what prediction 4 asks about -- warming was
    measured at +0.039 +/- 0.179 in Phase 3e and the question is whether oxygen adds to that.
    """
    y = np.array([u.latitude_trend for u in fitted])
    weights = np.array([1.0 / max((u.latitude_ci / 1.96) ** 2, 1e-6) for u in fitted])

    def standardise(values: np.ndarray) -> np.ndarray:
        spread = values.std(ddof=1)
        return (values - values.mean()) / (spread if spread > 0 else 1.0)

    oxygen = standardise(np.array([u.oxygen_trend for u in fitted]))
    warming = standardise(np.array([u.warming_trend for u in fitted]))

    pooled = float(np.sum(weights * y) / np.sum(weights))
    q = float(np.sum(weights * (y - pooled) ** 2))
    q_bar = float(stats.chi2.ppf(0.95, len(fitted) - 1))

    design = np.column_stack([np.ones(len(y)), oxygen, warming])
    root = np.sqrt(weights)
    solution, *_ = np.linalg.lstsq(design * root[:, None], y * root, rcond=None)
    residuals = y - design @ solution
    dof = len(y) - design.shape[1]
    sigma2 = float(np.sum(weights * residuals**2) / dof)
    covariance = sigma2 * np.linalg.pinv(design.T @ (design * weights[:, None]))
    errors = np.sqrt(np.diag(covariance))

    return Fit(
        units=len(fitted),
        q_statistic=q,
        q_bar=q_bar,
        heterogeneous=q > q_bar,
        oxygen_slope=float(solution[1]),
        oxygen_ci=float(1.96 * errors[1]),
        warming_slope=float(solution[2]),
        warming_ci=float(1.96 * errors[2]),
    )


def _grade(passed: bool) -> str:  # noqa: FBT001 -- a grade is a boolean by nature
    return "GRADED TRUE" if passed else "GRADED FALSE"


def render() -> str:
    """The registered numbers, every prediction graded, run exactly once."""
    fitted, coverage, calibrations = units()
    out = [
        "Phase 3g -- does the water's oxygen sort the movers from the stayers?",
        "=" * 92,
        "Pre-registered in docs/methods/phase3g-oxygen.md before any CMEMS request. The units, the",
        "depth rule, the two calibrations and the one fit were all fixed before a value was read.",
        "",
        f"Units fitted: {len(fitted)}; coverage rows: {len(coverage)}"
        + (f" ({', '.join(coverage)})" if coverage else ""),
    ]

    if not fitted:
        out.append("\nNo unit carried both drivers. Nothing to calibrate and nothing to fit.")
        return "\n".join(out)

    out += [
        "",
        "=" * 92,
        "the units",
        "=" * 92,
        f"  {'survey':22s} {'years':>6s} {'lat/dec':>9s} {'o2/dec':>9s} {'read m':>7s} "
        f"{'haul m':>7s} {'sst/dec':>8s}",
    ]
    for unit in fitted:
        out.append(
            f"  {unit.segment.survey:22s} {unit.segment.years:6d} "
            f"{unit.latitude_trend:+9.3f} {unit.oxygen_trend:+9.3f} {unit.read_depth_m:7.1f} "
            f"{unit.median_depth_m:7.0f} {unit.warming_trend:+8.3f}"
        )

    out += [
        "",
        "=" * 92,
        "the calibrations, which gate everything below them",
        "=" * 92,
        f"  C1  median oxygen trend  {calibrations.median_oxygen_trend:+.3f} mmol m-3 per decade"
        f"   -> {_grade(calibrations.c1_passes)}",
        f"  C2  corr(warming, oxygen) {calibrations.warming_oxygen_correlation:+.3f}"
        f"                    -> {_grade(calibrations.c2_passes)}",
    ]

    below_floor = len(fitted) < MIN_UNITS
    out += [
        "",
        "=" * 92,
        "predictions",
        "=" * 92,
        f"  1 (C1, deoxygenation present):     {_grade(calibrations.c1_passes)}",
        f"  2 (C2, solubility visible):        {_grade(calibrations.c2_passes)}",
        f"  5 (at least {PREDICTED_MINIMUM_UNITS} units):            "
        f"{_grade(len(fitted) >= PREDICTED_MINIMUM_UNITS)}  ({len(fitted)} entered)",
    ]

    if below_floor:
        out += [
            "",
            f"STOP CONDITION FIRED: {len(fitted)} units against the registered floor of "
            f"{MIN_UNITS}.",
            "This phase publishes as a coverage statement. No regression is fitted.",
        ]
        return "\n".join(out)

    if not calibrations.both_pass:
        failed = "C1" if not calibrations.c1_passes else "C2"
        out += [
            "",
            f"STOP CONDITION FIRED: {failed} did not pass.",
            "Predictions 3, 4 and 6 are NOT interpreted, per §5. The published result is the",
            "calibration itself: what a biogeochemical reanalysis does and does not reproduce at",
            "shelf depths over these sixteen footprints. The fit below is printed for the record",
            "and is not read as evidence about fish.",
        ]

    fitted_model = fit(fitted)
    out += [
        "",
        "=" * 92,
        "the registered fit: latitude trend ~ oxygen trend + warming trend (both standardised)",
        "=" * 92,
        f"  units                {fitted_model.units}",
        f"  Cochran's Q          {fitted_model.q_statistic:.1f} against a bar of "
        f"{fitted_model.q_bar:.1f}  -> "
        f"{'heterogeneous' if fitted_model.heterogeneous else 'one population'}",
        f"  oxygen slope         {fitted_model.oxygen_slope:+.3f} +/- {fitted_model.oxygen_ci:.3f}"
        f"  degrees latitude per decade per sd",
        f"  warming slope        {fitted_model.warming_slope:+.3f} +/- "
        f"{fitted_model.warming_ci:.3f}",
    ]

    oxygen_clear = abs(fitted_model.oxygen_slope) > fitted_model.oxygen_ci
    warming_clear = abs(fitted_model.warming_slope) > fitted_model.warming_ci
    if calibrations.both_pass:
        out += [
            "",
            f"  3 (oxygen predicts, negative slope): "
            f"{_grade(fitted_model.oxygen_slope < 0 and oxygen_clear)}",
            f"  4 (oxygen clear where warming is not): "
            f"{_grade(oxygen_clear and not warming_clear)}",
            "  6 (primary production no better than oxygen): NOT RUN -- registered as a secondary",
            "    and deliberately not fitted while the primary driver's own reading is unresolved.",
        ]
    else:
        out += ["", "  3, 4 and 6: UNGRADEABLE -- the calibration gate closed above."]

    out += [
        "",
        "=" * 92,
        "how to read this",
        "=" * 92,
        "The oxygen slope is degrees of latitude per decade per standard deviation of oxygen",
        "trend across units, so it is comparable with the warming slope beside it and with",
        "nothing outside this table. Sixteen units is sixteen points, the two drivers are tied",
        "by solubility, and §6 refuses the word 'measured' for anything a biogeochemical",
        "reanalysis produces -- it assimilates far less than a physical one, so a trend in it",
        "partly reflects its own observing system.",
    ]
    return "\n".join(out)
