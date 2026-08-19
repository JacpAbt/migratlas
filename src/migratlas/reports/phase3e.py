"""Phase 3e: the marine question with OISST, gated by the water the surveys did record.

`docs/methods/phase3e-marine-oisst.md` binds everything: Phase 3b's design with the warming
driver substituted for every unit, segments clipped to the OISST era, the deterministic gear
rule, and a calibration on the dual-record units that decides whether any of it is interpreted.
"""

import logging
from dataclasses import dataclass
from typing import Final

import numpy as np
import polars as pl

from migratlas.lake.reader import scan_dataset
from migratlas.reports.phase3b import (
    MIN_SEGMENT_YEARS,
    MIN_SPECIES_YEARS,
    MIN_UNITS,
    Regression,
    Segment,
    Unit,
    _trend_per_decade,
    gear_by_year,
    longest_segment,
    regression,
)

log = logging.getLogger(__name__)

OISST_FIRST_YEAR: Final = 1982
"""The first complete calendar year of the record (it begins September 1981)."""

PREDICTED_MINIMUM_UNITS_3E: Final = 15
MIN_CALIBRATION_PAIRS: Final = 2
"""A correlation over two points is a line through them, not a measurement."""


@dataclass(frozen=True, slots=True)
class Calibration:
    """OISST against the haul thermometers, where both waters exist."""

    units: int
    correlation: float
    passes: bool


def _oisst_by_unit_year() -> pl.DataFrame:
    """Footprint-mean OISST per survey-year, from the ingested driver rows."""
    return (
        scan_dataset("driver_samples", source_id="oisst")
        .collect()
        .with_columns(year=pl.col("period_start").dt.year())
        .group_by("site_id", "year")
        .agg(sst=pl.col("value").mean())
        .rename({"site_id": "survey"})
    )


def units_3e() -> tuple[list[Unit], list[str], Calibration]:
    """Every qualifying unit under the 3e rules, the coverage rows, and the calibration."""
    from migratlas.metrics import range as range_metrics  # noqa: PLC0415 -- report sibling
    from migratlas.reports import phase1b  # noqa: PLC0415 -- report sibling

    cells = range_metrics.to_cells(phase1b.survey_unit(phase1b.load()))
    oisst = _oisst_by_unit_year()
    insitu = (
        scan_dataset("driver_samples", source_id="fishglob")
        .collect()
        .filter(pl.col("variable") == "sea_surface_temperature")
        .with_columns(
            survey=pl.col("site_id").str.split(":").list.first(),
            year=pl.col("period_start").dt.year(),
        )
        .group_by("survey", "year")
        .agg(insitu_sst=pl.col("value").mean())
    )

    fitted: list[Unit] = []
    coverage: list[str] = []
    calibration_pairs: list[tuple[float, float]] = []
    for (name,), survey in cells.group_by(["survey_unit"], maintain_order=True):
        restricted, footprint = range_metrics.consistent_footprint(survey)
        if footprint.cells < range_metrics.MIN_CELLS:
            continue
        segment = longest_segment(
            [(int(r["year"]), str(r["gear"])) for r in gear_by_year(restricted).to_dicts()]
        )
        if segment is None:
            coverage.append(str(name))
            continue
        start = max(segment.start, OISST_FIRST_YEAR)
        inside = restricted.filter(pl.col("year").is_between(start, segment.end))
        clipped_years = inside["year"].n_unique()
        if clipped_years < MIN_SEGMENT_YEARS:
            coverage.append(str(name))
            continue
        segment = Segment(
            survey=str(name), gear=segment.gear, start=start, end=segment.end, years=clipped_years
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

        water = oisst.filter(
            pl.col("survey") == str(name), pl.col("year").is_between(start, segment.end)
        ).sort("year")
        if water.height < MIN_SEGMENT_YEARS:
            coverage.append(str(name))
            continue
        sst_trend, _ = _trend_per_decade(water["year"].to_numpy(), water["sst"].to_numpy())

        both = water.join(insitu.filter(pl.col("survey") == str(name)), on=["survey", "year"]).sort(
            "year"
        )
        if both.height >= MIN_SEGMENT_YEARS:
            insitu_trend, _ = _trend_per_decade(
                both["year"].to_numpy(), both["insitu_sst"].to_numpy()
            )
            oisst_trend_matched, _ = _trend_per_decade(
                both["year"].to_numpy(), both["sst"].to_numpy()
            )
            calibration_pairs.append((oisst_trend_matched, insitu_trend))

        depth = float(np.median(inside["site_depth_m"].drop_nulls().to_numpy()))
        fitted.append(
            Unit(
                segment=segment,
                species=latitude.height,
                latitude_trend=float(np.median(shifts)),
                latitude_ci=(
                    1.96 * float(shifts.std(ddof=1)) / np.sqrt(shifts.size)
                    if shifts.size > 1
                    else float("nan")
                ),
                temperature_trend=sst_trend,
                bottom_trend=None,
                median_depth_m=depth,
            )
        )
        log.info(
            "%s: %d clipped years (%d-%d), %d species, lat %+.3f, oisst %+.3f",
            name, clipped_years, start, segment.end, latitude.height,
            float(np.median(shifts)), sst_trend,
        )  # fmt: skip

    grid = np.array([p[0] for p in calibration_pairs])
    haul = np.array([p[1] for p in calibration_pairs])
    correlation = (
        float(np.corrcoef(grid, haul)[0, 1])
        if len(calibration_pairs) > MIN_CALIBRATION_PAIRS and grid.std() > 0 and haul.std() > 0
        else float("nan")
    )
    calibration = Calibration(
        units=len(calibration_pairs),
        correlation=correlation,
        passes=bool(np.isfinite(correlation) and correlation > 0),
    )
    return fitted, coverage, calibration


def render() -> str:
    """Every registered prediction graded, the calibration before anything else."""
    fitted, coverage, calibration = units_3e()

    def grade(passed: bool) -> str:  # noqa: FBT001 -- a grade is a boolean by nature
        return "GRADED TRUE" if passed else "GRADED FALSE"

    lines = [
        f"Units fitted: {len(fitted)}; coverage rows: {len(coverage)} ({', '.join(coverage)}).",
        f"Prediction 1 ({grade(calibration.passes)}): OISST vs in-situ warming across "
        f"{calibration.units} dual-record units, correlation {calibration.correlation:+.3f}.",
    ]
    if len(fitted) < MIN_UNITS:
        lines.append(
            f"STOP CONDITION: fewer than {MIN_UNITS} units — coverage statement, no regression."
        )
        return "\n".join(lines)
    if not calibration.passes:
        lines.append(
            "STOP CONDITION: the calibration failed, so predictions 2-4 are UNINTERPRETED and "
            "the published result is OISST failing to track the shelf water."
        )
        return "\n".join(lines)

    fit: Regression = regression(fitted)
    positive = fit.temp_slope - fit.temp_ci > 0
    negative_interaction = fit.interaction_slope + fit.interaction_ci < 0
    lines += [
        f"Prediction 2 ({grade(fit.heterogeneous)}): Cochran's Q {fit.q_statistic:.1f} against "
        f"a chi-square bar of {fit.q_bar:.1f} across {fit.units} units.",
        f"Prediction 3 ({grade(positive)}): latitude trend on OISST warming, slope "
        f"{fit.temp_slope:+.3f} ± {fit.temp_ci:.3f} °lat per °C (both per decade).",
        f"Prediction 4 ({grade(negative_interaction)}): warming x depth interaction "
        f"{fit.interaction_slope:+.3f} ± {fit.interaction_ci:.3f} (depth standardised).",
        f"Prediction 5 ({grade(len(fitted) >= PREDICTED_MINIMUM_UNITS_3E)}): {len(fitted)} "
        f"units entered against the predicted fifteen.",
    ]
    return "\n".join(lines)
