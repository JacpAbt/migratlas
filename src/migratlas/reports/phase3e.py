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

MIN_SHARED_SURVEYS: Final = 3
"""Surveys a taxon must appear in before it can separate the sea from the species."""


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


def _warming(
    oisst: pl.DataFrame, insitu: pl.DataFrame, name: str, start: int, end: int
) -> tuple[float, tuple[float, float] | None] | None:
    """One unit's OISST warming trend, and its calibration pair where both waters exist.

    None when the OISST series is shorter than the segment floor; the pair is None for the
    units that never recorded their own water.
    """
    water = oisst.filter(pl.col("survey") == name, pl.col("year").is_between(start, end)).sort(
        "year"
    )
    if water.height < MIN_SEGMENT_YEARS:
        return None
    sst_trend, _ = _trend_per_decade(water["year"].to_numpy(), water["sst"].to_numpy())
    both = water.join(insitu.filter(pl.col("survey") == name), on=["survey", "year"]).sort("year")
    if both.height < MIN_SEGMENT_YEARS:
        return sst_trend, None
    insitu_trend, _ = _trend_per_decade(both["year"].to_numpy(), both["insitu_sst"].to_numpy())
    matched, _ = _trend_per_decade(both["year"].to_numpy(), both["sst"].to_numpy())
    return sst_trend, (matched, insitu_trend)


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

        warming = _warming(oisst, insitu, str(name), start, segment.end)
        if warming is None:
            coverage.append(str(name))
            continue
        sst_trend, pair = warming
        if pair is not None:
            calibration_pairs.append(pair)

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

    # ADR 0016, and not a graded prediction: the registration asked for no leverage check, so this
    # can only ever be a diagnostic. It is printed because this phase's heterogeneity result is the
    # one owed to the ledger, and publishing a statistic over eighteen units without asking whether
    # one of them carries it is what Phase 3g nearly did.
    lines.append(
        f"ADR 0016 — Q survives dropping any one unit: {'yes' if fit.q_survives else 'NO'}."
    )
    lines.append(
        f"Weight sensitivity — Q clears its bar while the per-unit intervals are understated by "
        f"less than {fit.q_robustness:.2f}x. Comparable clustering corrections measured elsewhere "
        f"in this project run 2.4x to 4.5x."
    )
    if fit.leverage is not None:
        worst = fit.leverage.worst()
        named = f" furthest is {worst[0]} at {worst[1]:+.3f} ± {worst[2]:.3f}" if worst else ""
        lines.append(
            f"ADR 0016 — the warming slope is a null, so it has no verdict to lose "
            f"(clears zero: {'yes' if fit.leverage.clears_at_full else 'no'}; "
            f"publishable: {'yes' if fit.leverage.publishable else 'NO'}).{named}"
        )
    return "\n".join(lines)


# --- Unregistered diagnostics: why do the seas differ? -----------------------------------
#
# `seas-disagree` publishes Cochran's Q at 235.7 against a bar of 27.6 and a warming null, and the
# note stopped there. Four measured drivers now fail to sort the units -- warming, depth, oxygen
# after leverage, and Phase 3j's three cluster axes -- so "the seas differ" is a fact with no
# explanation attached, which is the shape of an unfinished result rather than a caveated one.
#
# Both functions below are UNREGISTERED and can never be graded predictions: they were written after
# the heterogeneity was published. Phase 3g's precedent governs how they may be read.


def sampling_drift() -> pl.DataFrame:
    """Where each survey's *sampling* went over time, with no fish in it at all.

    The marine twin of `phase1n.sampling_drift`, and it is here because that one found a fifth of
    the Swedish protocol offset was effort moving north rather than birds. A centroid is weighted by
    catch per unit effort, so where the hauls happen moves it: a survey whose stations drift north
    reports its fish drifting north.

    The consistency rule keeps a cell only where it was sampled in 80% of the survey's years. It
    says nothing about how many hauls each kept cell got in each year, and that is what a centroid
    is weighted over.
    """
    from migratlas.metrics import range as range_metrics  # noqa: PLC0415 -- report sibling
    from migratlas.reports import phase1b  # noqa: PLC0415 -- report sibling

    cells = range_metrics.to_cells(phase1b.survey_unit(phase1b.load()))
    rows: list[dict[str, object]] = []
    for (name,), survey in cells.group_by(["survey_unit"], maintain_order=True):
        restricted, footprint = range_metrics.consistent_footprint(survey)
        if footprint.cells < range_metrics.MIN_CELLS:
            continue
        # Hauls, not catch: this is a question about where the ship went.
        per_year = (
            restricted.group_by("year")
            .agg(latitude=pl.col("cell_latitude").mean(), hauls=pl.len())
            .drop_nulls()
            .sort("year")
        )
        if per_year.height < MIN_SEGMENT_YEARS:
            continue
        drift, _ = _trend_per_decade(per_year["year"].to_numpy(), per_year["latitude"].to_numpy())
        rows.append({"survey_unit": str(name), "sampling_drift": drift})
    return pl.DataFrame(rows)


def sea_or_species() -> dict[str, float]:
    """For species caught in several surveys: does the sea explain more than the species?

    The marine twin of Phase 1l's pairing, and the question the owner asked of the birds. Surveys
    reach -0.22 and +0.26 in opposite directions -- but different surveys hold different species, so
    that spread could be the seas disagreeing or simply different animals living in different
    places. Restricting to taxa caught in three or more surveys makes the two separable, because
    then the same animal is measured in several seas.

    Both shares use `phase1m._icc`, the project's own coherence measure, so they are comparable to
    every grouping result elsewhere: group by taxon and the share is what the species explains,
    group by survey and it is what the sea explains.
    """
    from migratlas.metrics import range as range_metrics  # noqa: PLC0415 -- report sibling
    from migratlas.reports import phase1b, phase1m  # noqa: PLC0415 -- report siblings

    cells = range_metrics.to_cells(phase1b.survey_unit(phase1b.load()))
    _, pooled, _ = phase1b.analyse(cells)
    if pooled.is_empty():
        return {}

    counts = pooled.group_by("taxon_key").agg(surveys=pl.col("survey_unit").n_unique())
    shared = counts.filter(pl.col("surveys") >= MIN_SHARED_SURVEYS)["taxon_key"]
    table = pooled.filter(pl.col("taxon_key").is_in(shared)).select(
        slope=pl.col("per_decade"),
        stderr=pl.col("stderr"),
        taxon=pl.col("taxon_key").cast(pl.String),
        survey=pl.col("survey_unit"),
    )
    if table.is_empty():
        return {}

    by_taxon = phase1m._icc(table.rename({"taxon": "group"}))  # noqa: SLF001 -- the project's own
    by_survey = phase1m._icc(table.rename({"survey": "group"}))  # noqa: SLF001
    return {
        "pairs": float(table.height),
        "taxa": float(table["taxon"].n_unique()),
        "surveys": float(table["survey"].n_unique()),
        "species_share": by_taxon[1],
        "sea_share": by_survey[1],
    }
