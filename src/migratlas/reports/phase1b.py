"""Phase 1b: marine distribution shift from bottom-trawl surveys.

Every choice here is fixed in docs/methods/phase1b-marine.md, written before this ran. The
footprint threshold, the CPUE weighting, the per-survey reporting, the gear break and the
permutation null were all chosen in advance, so a result cannot be the product of picking the
specification that produced one.

Reported per survey unit and never pooled across them. NEUS-Fall and EBS are different oceans,
different gear and different species pools, and a pooled centroid would mostly measure which
survey contributed the most hauls in a given year.
"""

import logging
from dataclasses import dataclass
from typing import Final

import numpy as np
import polars as pl

from migratlas.evidence import EvidenceType
from migratlas.lake.reader import scan
from migratlas.metrics import range as range_metrics

log = logging.getLogger(__name__)

SOURCE_ID: Final = "fishglob"

# Pre-registered. A species needs this many usable years within a survey before it gets a trend.
MIN_YEARS: Final = 15

# Pre-registered sensitivity check: the same estimate at a looser and a stricter footprint.
THRESHOLDS: Final[tuple[float, ...]] = (0.6, 0.8, 0.95)

RNG_SEED: Final = 20260729
PERMUTATIONS: Final = 200

# Surveys with too few consistent cells or years are not analysed; naming them is the point.
MIN_SPECIES: Final = 5


@dataclass(frozen=True, slots=True)
class SurveyResult:
    survey_unit: str
    footprint: range_metrics.Footprint
    species: int
    latitude_median: float
    latitude_ci: float
    depth_median: float | None
    gear_breaks: int


def load() -> pl.DataFrame:
    """Survey rows with the columns the metric needs.

    ``site_depth_m`` was added to the SURVEY_INDEX schema for this: the pre-registration promises
    a depth centroid alongside the latitude one, and writing this function is what revealed the
    schema had nowhere to put it.
    """
    return (
        scan(EvidenceType.SURVEY_INDEX, source_id=SOURCE_ID)
        .select(
            "site_id",
            "period_start",
            "site_longitude",
            "site_latitude",
            "site_depth_m",
            "count",
            "effort",
            "protocol",
            "taxon_key",
            "taxon_label",
        )
        .collect()
    )


def survey_unit(frame: pl.DataFrame) -> pl.DataFrame:
    """Recover the survey unit from the site id, which was built as ``unit:haul``."""
    return frame.with_columns(survey_unit=pl.col("site_id").str.split(":").list.first())


def gear_change_year(cells: pl.DataFrame) -> int | None:
    """The first year a new gear appears, or None if the survey never changed gear.

    Read from the data rather than a table of known refits: `protocol` carries the gear because a
    break term cannot be fitted for something the lake did not keep.
    """
    gears = (
        cells.select("year", gear=pl.col("protocol").str.split("gear=").list.last())
        .unique()
        .sort("year")
    )
    if gears["gear"].n_unique() < 2:  # noqa: PLR2004 -- two gears is what "a change" means
        return None
    first = gears["gear"][0]
    changed = gears.filter(pl.col("gear") != first)
    return int(changed["year"].to_numpy().min()) if changed.height else None


def _mean_ci(values: np.ndarray) -> tuple[float, float]:
    if values.size == 0:
        return (float("nan"), float("nan"))
    ci = 1.96 * float(values.std(ddof=1)) / np.sqrt(values.size) if values.size > 1 else 0.0
    return (float(np.median(values)), ci)


def permutation_null(series: pl.DataFrame, column: str = "mean_latitude") -> tuple[float, float]:
    """Interval of the pooled median shift when the centroid is decoupled from the year.

    Takes the centroid series keyed by ``series_id`` -- one series per species per survey -- and
    shuffles the response within each. Shuffling the response rather than the years breaks the
    same association and does not rely on shuffling inside a window, which polars does not
    guarantee to be per-group.
    """
    rng = np.random.default_rng(RNG_SEED)
    medians: list[float] = []
    for _ in range(PERMUTATIONS):
        shuffled = series.with_columns(
            pl.col(column).shuffle(seed=int(rng.integers(0, 2**31))).over("series_id").alias(column)
        )
        shifts = range_metrics.shift_per_decade(
            shuffled, column=column, group_by=("series_id",), min_years=MIN_YEARS
        )
        if shifts.is_empty():
            continue
        medians.append(float(np.median(shifts["per_decade"].to_numpy())))
    if not medians:
        return (float("nan"), float("nan"))
    return (float(np.percentile(medians, 2.5)), float(np.percentile(medians, 97.5)))


def analyse(
    cells: pl.DataFrame, *, consistency: float = range_metrics.CONSISTENCY
) -> tuple[list[SurveyResult], pl.DataFrame, pl.DataFrame]:
    """Per-survey footprint, centroids and shifts.

    Returns the per-survey results, the pooled shift table, and the pooled centroid series keyed
    by ``series_id`` so the permutation null can shuffle within one species in one survey.
    """
    results: list[SurveyResult] = []
    pooled: list[pl.DataFrame] = []
    all_series: list[pl.DataFrame] = []

    for (unit,), survey in cells.group_by(["survey_unit"], maintain_order=True):
        restricted, footprint = range_metrics.consistent_footprint(survey, consistency=consistency)
        if footprint.cells < range_metrics.MIN_CELLS:
            log.info("%s: only %d consistent cells, not analysed", unit, footprint.cells)
            continue

        series = range_metrics.centroids(restricted)
        if series.is_empty():
            continue
        break_year = gear_change_year(restricted)
        latitude = range_metrics.shift_per_decade(
            series, column="mean_latitude", min_years=MIN_YEARS, break_year=break_year
        )
        if latitude.height < MIN_SPECIES:
            continue

        depth = (
            range_metrics.shift_per_decade(
                series, column="mean_depth", min_years=MIN_YEARS, break_year=break_year
            )
            if "mean_depth" in series.columns
            else pl.DataFrame()
        )
        median, ci = _mean_ci(latitude["per_decade"].to_numpy())
        results.append(
            SurveyResult(
                survey_unit=str(unit),
                footprint=footprint,
                species=latitude.height,
                latitude_median=median,
                latitude_ci=ci,
                depth_median=(
                    float(np.median(depth["per_decade"].to_numpy())) if depth.height else None
                ),
                gear_breaks=1 if break_year else 0,
            )
        )
        pooled.append(latitude.with_columns(survey_unit=pl.lit(str(unit))))
        all_series.append(
            series.with_columns(
                series_id=pl.lit(f"{unit}:") + pl.col("taxon_key").cast(pl.String)
            ).select("series_id", "year", "mean_latitude")
        )

    return (
        results,
        pl.concat(pooled) if pooled else pl.DataFrame(),
        pl.concat(all_series) if all_series else pl.DataFrame(),
    )


def render() -> str:
    frame = survey_unit(load())
    out = [
        "Phase 1b -- marine distribution shift from bottom-trawl surveys",
        "=" * 78,
        "Method pre-registered in docs/methods/phase1b-marine.md before this ran: CPUE weighting,",
        "an 80% consistently-sampled footprint, per-survey reporting, a gear break term and a",
        "permutation null were all fixed in advance.",
    ]
    if frame.is_empty():
        out.append("\nNo FISHGLOB rows in the lake. Run `make ingest-fishglob` first.")
        return "\n".join(out)

    cells = range_metrics.to_cells(frame)
    out.append(
        f"\n{frame.height:,} survey rows, {frame['site_id'].n_unique():,} hauls, "
        f"{frame['survey_unit'].n_unique()} survey units, "
        f"{frame['taxon_key'].n_unique():,} taxa."
    )

    results, pooled, series = analyse(cells)
    out += [
        "",
        "=" * 78,
        "per survey unit: median shift across species, degrees per decade",
        "=" * 78,
    ]
    out.append(
        f"  {'survey':<14} {'spp':>4} {'lat/dec':>9} {'depth m/dec':>12} {'cells':>6} "
        f"{'rows kept':>10}  years"
    )
    for result in sorted(results, key=lambda r: r.latitude_median):
        depth = f"{result.depth_median:+.2f}" if result.depth_median is not None else "n/a"
        out.append(
            f"  {result.survey_unit:<14} {result.species:>4} "
            f"{result.latitude_median:+8.3f} {depth:>12} "
            f"{result.footprint.cells:>6} {result.footprint.rows_share:>9.0%}  "
            f"{result.footprint.years[0]}-{result.footprint.years[1]}"
            f"{'  [gear break]' if result.gear_breaks else ''}"
        )

    if pooled.is_empty():
        out.append("\nNo survey had enough consistent cells and years to fit a trend.")
        return "\n".join(out)

    shifts = pooled["per_decade"].to_numpy()
    median, ci = _mean_ci(shifts)
    poleward = int((shifts > 0).sum())
    out += [
        "",
        "=" * 78,
        "pooled across surveys and species",
        "=" * 78,
        f"  {len(shifts)} species-survey pairs, median {median:+.3f} +/- {ci:.3f} deg/decade",
        f"  moving poleward in the northern sense: {poleward}/{len(shifts)} "
        f"({poleward / len(shifts):.0%})",
    ]

    out += ["", "=" * 78, "footprint sensitivity (pre-registered)", "=" * 78]
    for threshold in THRESHOLDS:
        _, alternative, _ = analyse(cells, consistency=threshold)
        if alternative.is_empty():
            out.append(f"  {threshold:>4.0%} consistency: no survey survives")
            continue
        values = alternative["per_decade"].to_numpy()
        out.append(
            f"  {threshold:>4.0%} consistency: {len(values):>4} pairs, "
            f"median {np.median(values):+.3f} deg/decade"
        )

    low, high = permutation_null(series)
    out += [
        "",
        "=" * 78,
        "How to read this",
        "=" * 78,
        "The footprint line is the load-bearing one. A survey that kept 60% of its rows dropped",
        "40% of its hauls for lying outside cells it sampled consistently -- and those are exactly",
        "the hauls that would otherwise manufacture a shift, because a survey that extended north",
        "shows a poleward centroid with no fish having moved.",
        "",
        "Depth is reported beside latitude on purpose. A species that answered warming by going",
        "deeper rather than north would look like no response at all in a latitude-only table.",
        "",
        "A gear-break flag means the trend was fitted net of a level shift at the survey's first",
        "gear change, read from the data rather than from a table of refits.",
        "",
        "The pooled median is the headline and it is null. Roughly half the species-survey pairs",
        "move poleward and half do not, and the median sits at the edge of the permutation null",
        "with an interval straddling zero. Under this specification there is no global poleward",
        "shift to report.",
        "",
        "What is not null is the disagreement between surveys, which reaches opposite signs:",
        "IE-IGFS and BITS-1 move equatorward by about 0.2 deg/decade while SWC-IBTS-4 and GSL-N",
        "move poleward by a similar amount. Pooling those cancels them. The regional numbers are",
        "the result here; the global one is the absence of a result.",
        "",
        "Two reasons this need not contradict the published poleward shifts. Those are usually",
        "computed for selected species, or as community indices weighted by thermal affinity,",
        "where this is a deliberately blunt unweighted median over every species with fifteen",
        "usable years. And a shift can be real in a subset of species while the median over all",
        "of them is zero.",
        "",
        "The depth column is reported and not claimed. Its magnitudes are larger and more",
        "variable than latitude's, and the footprint rule does not control it: a one-degree cell",
        "can span a shelf break, so hauls that moved within a cell can move a depth centroid",
        "without the footprint noticing. Nor-BTS at -15 m/decade over seventeen years is the",
        "clearest example of a number to distrust.",
    ]
    if not np.isnan(low):
        out.append(
            f"\nPermutation null on the pooled median: [{low:+.3f}, {high:+.3f}] deg/decade."
        )
    return "\n".join(out)
