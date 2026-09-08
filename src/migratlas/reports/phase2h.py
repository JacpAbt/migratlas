"""Phase 2h -- is a marine where-shift a range shift, or a cut through a season?

Pre-registered in ``docs/methods/phase2h-phase-cut.md`` before any seasonal contrast was computed.
A bottom-trawl survey sails in a fixed season, so a species that moves within its year is sampled
at the same phase every time, and a change in *when* it arrives cannot be told from a change in
*where* it lives. Eight regions in the lake are trawled in two or three seasons under separate
survey unit ids, which makes the question answerable with the instrument that asked it.

**The estimand that matters is the trend, not the centroid.** A seasonal difference in catchability
-- a fish on the bottom in winter and in midwater in summer -- moves a centroid with no animal
having moved, and it is a *level* offset, so it cancels in a per-decade trend. That cancellation is
the design: each species' trend is fitted once per season on the footprint and years the seasons
share, and their disagreement is measured against their own errors.

**The split-half control decides whether any of it can be read.** A least-squares trend error on an
autocorrelated centroid series is too small, and a disagreement between seasons would look the same
as a disagreement between two halves of one season. If the halves disagree as much, this instrument
cannot separate a phase cut from a wandering centroid, and the note says so instead of claiming.
"""

import logging
from dataclasses import dataclass
from typing import Final
from zlib import crc32

import numpy as np
import polars as pl
from scipy import stats

from migratlas.metrics.range import (
    MIN_CELLS,
    centroids,
    consistent_footprint,
    shift_per_decade,
    to_cells,
)
from migratlas.reports import phase1b

log = logging.getLogger(__name__)

SEED: Final = 1
DRAWS: Final = 1_000

FAMILIES: Final[dict[str, tuple[str, ...]]] = {
    "North Sea": ("NS-IBTS-1", "NS-IBTS-3"),
    "west Scotland": ("SWC-IBTS-1", "SWC-IBTS-4"),
    "Baltic": ("BITS-1", "BITS-4"),
    "Gulf of Cadiz": ("SP-ARSA-1", "SP-ARSA-4"),
    "Gulf of Mexico": ("GMEX-Summer", "GMEX-Fall"),
    "northeast US": ("NEUS-Spring", "NEUS-Fall"),
    "southeast US": ("SEUS-spring", "SEUS-summer", "SEUS-fall"),
    "Scotian Shelf": ("SCS-SPRING", "SCS-SUMMER", "SCS-FALL"),
}
"""A region trawled in more than one season, each season a separate survey unit."""

CALIBRATION: Final[dict[str, float]] = {
    "BITS-1": -0.183,
    "GMEX-Fall": -0.119,
    "NEUS-Spring": 0.101,
    "SWC-IBTS-4": 0.258,
}
"""Phase 1b's published per-unit medians, for the four seasonal units it happened to print."""
CALIBRATION_TOLERANCE: Final = 0.02
"""Registered loose because Phase 1b's break term was not re-derived. Correction 1 derives it:
the miss it left on BITS-1 was 0.085, four times this tolerance, and not absorbable by widening
one."""

MIN_YEARS: Final = 15
"""A species needs this many usable years in every season of its family. Phase 1b's floor."""
CONTROL_MIN_YEARS: Final = 8
"""Amendment C: half the main floor, rounded up, for each half of a split-half control."""
MIN_SPECIES: Final = 20
MIN_FAMILIES: Final = 6
AMPLITUDE_FLOOR: Final = 0.2
"""Prediction 3: the median absolute seasonal amplitude that counts as real, in degrees."""
CONTROL_BAR: Final = 1.2
"""Prediction 7: above this median absolute z from the split halves, prediction 4 is unreadable."""
FAMILIES_FOR_DISAGREEMENT: Final = 0.5
"""Prediction 4: the share of passing families whose Q must clear its bar."""
CORRELATION_CEILING: Final = 0.9
"""Prediction 6: a between-season trend correlation at or above this is not "shift plus noise"."""

LATITUDE: Final = "mean_latitude"
UNIT: Final = "survey_unit"
TAXON: Final[tuple[str, ...]] = ("taxon_key", "taxon_label")
GROUP: Final[tuple[str, ...]] = (UNIT, *TAXON)
PAIR: Final = 2


def _seed(name: str) -> int:
    return (crc32(name.encode()) ^ SEED) & 0x7FFF_FFFF


@dataclass(frozen=True, slots=True)
class Coverage:
    """What a family kept, and why it was dropped if it was."""

    family: str
    units: tuple[str, ...]
    cells: int
    years: tuple[int, int]
    species: int
    dropped: str | None

    @property
    def passes(self) -> bool:
        return self.dropped is None


@dataclass(frozen=True, slots=True)
class SpeciesResult:
    """One species in one family: its per-season trends, their disagreement, its amplitude."""

    taxon_key: int
    taxon_label: str
    seasons: int
    q: float
    """Inverse-variance weighted heterogeneity across the seasons' trends, chi-square on k-1."""
    trends: tuple[float, ...]
    amplitude: float
    """The range of the per-season mean centroids, degrees. |difference| at two seasons."""
    amplitude_stderr: float

    @property
    def root_q(self) -> float:
        """`|z|` at two seasons, and its generalisation above that."""
        return float(np.sqrt(self.q / (self.seasons - 1)))


@dataclass(frozen=True, slots=True)
class FamilyResult:
    """One region, pooled over its species."""

    coverage: Coverage
    species: tuple[SpeciesResult, ...]
    q_total: float
    q_bar: float
    median_root_q: float
    median_amplitude: float
    amplitude_q: float
    amplitude_q_bar: float
    pair_correlation: float
    control_median: float | None
    """None where no half cleared the control's year floor -- reported as uncontrolled."""

    @property
    def disagrees(self) -> bool:
        return bool(np.isfinite(self.q_total)) and self.q_total > self.q_bar

    @property
    def amplitude_heterogeneous(self) -> bool:
        return bool(np.isfinite(self.amplitude_q)) and self.amplitude_q > self.amplitude_q_bar


@dataclass(frozen=True, slots=True)
class Correlation:
    """Prediction 5: does a species' seasonal amplitude predict its seasons' disagreement?"""

    rho: float
    null_low: float
    null_high: float
    pairs: int

    @property
    def clears_null(self) -> bool:
        return bool(np.isfinite(self.rho)) and self.rho > self.null_high


@dataclass(frozen=True, slots=True)
class Phase2h:
    families: tuple[FamilyResult, ...]
    calibration: dict[str, float]
    correlation: Correlation

    @property
    def passing(self) -> tuple[FamilyResult, ...]:
        return tuple(f for f in self.families if f.coverage.passes)

    @property
    def calibrated(self) -> bool:
        """Every published unit reproduced, or the loader disagrees with the published one."""
        return all(
            unit in self.calibration
            and abs(self.calibration[unit] - target) < CALIBRATION_TOLERANCE
            for unit, target in CALIBRATION.items()
        )

    @property
    def controlled(self) -> bool:
        """Prediction 7: the split halves are quiet wherever the control ran."""
        medians = [f.control_median for f in self.passing if f.control_median is not None]
        return bool(medians) and max(medians) <= CONTROL_BAR


# --- The panels -----------------------------------------------------------------------------


def load() -> pl.DataFrame:
    """Every marine survey row with its unit recovered, through Phase 1b's own loader."""
    return phase1b.survey_unit(phase1b.load())


def family_cells(frame: pl.DataFrame, units: tuple[str, ...]) -> tuple[pl.DataFrame, int, int, int]:
    """The family's rows on the footprint and year span every one of its seasons shares.

    The footprint is computed per season and intersected, because a cell sampled consistently in
    summer and never in winter is not a cell this comparison can use. The span is the overlap of
    the seasons' spans, so both trends are fitted over the same years.
    """
    rows = frame.filter(pl.col(UNIT).is_in(pl.Series(units).implode()))
    if rows.is_empty():
        return rows, 0, 0, 0

    cells = to_cells(rows)
    keep: pl.DataFrame | None = None
    lower, upper = -np.inf, np.inf
    for unit in units:
        season = cells.filter(pl.col(UNIT) == unit)
        if season.is_empty():
            return season, 0, 0, 0
        restricted, _ = consistent_footprint(season)
        present = restricted.select("cell_longitude", "cell_latitude").unique()
        keep = (
            present
            if keep is None
            else keep.join(present, on=["cell_longitude", "cell_latitude"], how="inner")
        )
        years = season["year"].to_numpy()
        lower, upper = max(lower, float(years.min())), min(upper, float(years.max()))

    if keep is None or keep.height < MIN_CELLS or lower > upper:
        return cells.clear(), 0 if keep is None else keep.height, int(lower), int(upper)

    shared = cells.join(keep, on=["cell_longitude", "cell_latitude"], how="inner").filter(
        pl.col("year").is_between(int(lower), int(upper))
    )
    return shared, keep.height, int(lower), int(upper)


def season_series(cells: pl.DataFrame) -> pl.DataFrame:
    """Abundance-weighted latitude per species per season per year."""
    return centroids(cells, group_by=GROUP)


def season_trends(series: pl.DataFrame, cells: pl.DataFrame) -> pl.DataFrame:
    """A per-decade latitude trend per species per season, with its standard error.

    Correction 1 in the note: each season carries a break term at its *own* gear change year,
    the way Phase 1b fits every unit. A gear change inside one season of a family and not the
    other puts a step in one centroid, and this design would have read that step as a phase cut.
    """
    out: list[pl.DataFrame] = []
    for unit in series[UNIT].unique(maintain_order=True).to_list():
        season = cells.filter(pl.col(UNIT) == unit)
        trends = shift_per_decade(
            series.filter(pl.col(UNIT) == unit),
            column=LATITUDE,
            group_by=TAXON,
            min_years=MIN_YEARS,
            break_year=phase1b.gear_change_year(season),
        )
        if not trends.is_empty():
            out.append(
                trends.with_columns(
                    pl.lit(str(unit)).alias(UNIT),
                    # A season that changed gear carries a float here and one that did not carries
                    # nulls, and the two will not stack without being told they are the same type.
                    pl.col("break_shift").cast(pl.Float64),
                )
            )
    return pl.concat(out) if out else pl.DataFrame()


# --- The statistics -------------------------------------------------------------------------


def _heterogeneity(values: np.ndarray, errors: np.ndarray) -> float:
    """Inverse-variance weighted Q across a species' seasons. Chi-square on k-1 if they agree."""
    weights = 1.0 / np.square(errors)
    mean = float(np.sum(weights * values) / np.sum(weights))
    return float(np.sum(weights * np.square(values - mean)))


def _amplitude(means: np.ndarray, errors: np.ndarray) -> tuple[float, float]:
    """The range of a species' per-season mean centroids, and its error from the two extremes."""
    high, low = int(np.argmax(means)), int(np.argmin(means))
    span = float(means[high] - means[low])
    error = float(np.sqrt(errors[high] ** 2 + errors[low] ** 2))
    return span, error


def species_results(series: pl.DataFrame, trends: pl.DataFrame) -> list[SpeciesResult]:
    """Every species with a usable trend in every season of its family.

    A species missing a season, or carrying a null standard error in one, is dropped rather than
    compared against fewer seasons than its neighbours: the pooled Q's degrees of freedom would
    then depend on which species happened to be measurable.
    """
    seasons = trends[UNIT].n_unique()
    usable = trends.filter(pl.col("stderr").is_not_null(), pl.col("stderr") > 0)
    complete = (
        usable.group_by(list(TAXON))
        .agg(pl.len().alias("n"))
        .filter(pl.col("n") == seasons)
        .select(TAXON)
    )
    if complete.is_empty():
        return []

    per_species = (
        series.join(complete, on=list(TAXON), how="inner")
        .group_by([*TAXON, UNIT])
        .agg(
            mean=pl.col(LATITUDE).mean(),
            spread=pl.col(LATITUDE).std(),
            years=pl.len(),
        )
    )
    joined = (
        usable.join(complete, on=list(TAXON), how="inner")
        .join(per_species, on=[*TAXON, UNIT], how="inner")
        .sort([*TAXON, UNIT])
    )

    out: list[SpeciesResult] = []
    for (key, label), group in joined.group_by(list(TAXON), maintain_order=True):
        values = group["per_decade"].to_numpy().astype(float)
        errors = group["stderr"].to_numpy().astype(float)
        means = group["mean"].to_numpy().astype(float)
        # The error on a season's mean centroid, not on one year of it.
        spread = group["spread"].to_numpy().astype(float)
        counts = group["years"].to_numpy().astype(float)
        mean_errors = np.where(counts > 1, spread / np.sqrt(counts), np.nan)
        if not np.all(np.isfinite(mean_errors)):
            continue
        span, span_error = _amplitude(means, mean_errors)
        out.append(
            SpeciesResult(
                taxon_key=int(key),
                taxon_label=str(label),
                seasons=values.size,
                q=_heterogeneity(values, errors),
                trends=tuple(float(v) for v in values),
                amplitude=span,
                amplitude_stderr=span_error,
            )
        )
    return out


def pair_correlation(trends: pl.DataFrame, units: tuple[str, ...]) -> float:
    """The mean Spearman correlation between the seasons' per-species trends, over season pairs."""
    wide = trends.pivot(on=UNIT, index=list(TAXON), values="per_decade")
    present = [unit for unit in units if unit in wide.columns]
    rhos: list[float] = []
    for i, first in enumerate(present):
        for second in present[i + 1 :]:
            both = wide.select(first, second).drop_nulls()
            if both.height < PAIR + 1:
                continue
            rho = stats.spearmanr(both[first].to_numpy(), both[second].to_numpy()).statistic
            if np.isfinite(rho):
                rhos.append(float(rho))
    return float(np.mean(rhos)) if rhos else float("nan")


def split_half_control(cells: pl.DataFrame, unit: str) -> float | None:
    """Prediction 7. Two interleaved halves of one season, and how far apart their trends land.

    Interleaved rather than early-against-late, because a species with a real trend would make
    early-against-late disagree by construction. Odd and even years share the trend and differ
    only in their noise, so a spread above 1 is the error model being too small.
    """
    season = cells.filter(pl.col(UNIT) == unit)
    if season.is_empty():
        return None
    halves: list[pl.DataFrame] = []
    for remainder in (0, 1):
        part = season.filter(pl.col("year") % PAIR == remainder)
        series = centroids(part, group_by=TAXON)
        if series.is_empty():
            return None
        halves.append(
            shift_per_decade(
                series,
                column=LATITUDE,
                group_by=TAXON,
                min_years=CONTROL_MIN_YEARS,
                break_year=phase1b.gear_change_year(season),
            )
        )
    if any(half.is_empty() for half in halves):
        return None

    joined = (
        halves[0]
        .filter(pl.col("stderr").is_not_null(), pl.col("stderr") > 0)
        .join(
            halves[1].filter(pl.col("stderr").is_not_null(), pl.col("stderr") > 0),
            on=list(TAXON),
            how="inner",
            suffix="_even",
        )
        .sort(list(TAXON))
    )
    if joined.is_empty():
        return None
    difference = joined["per_decade"].to_numpy() - joined["per_decade_even"].to_numpy()
    combined = np.sqrt(
        np.square(joined["stderr"].to_numpy()) + np.square(joined["stderr_even"].to_numpy())
    )
    return float(np.median(np.abs(difference / combined)))


def family_result(frame: pl.DataFrame, name: str, units: tuple[str, ...]) -> FamilyResult:
    """One region, from its rows to its pooled disagreement."""
    cells, kept_cells, lower, upper = family_cells(frame, units)
    if cells.is_empty() or kept_cells < MIN_CELLS:
        return _empty(name, units, kept_cells, (lower, upper), "footprint under ten shared cells")

    series = season_series(cells)
    if series.is_empty():
        return _empty(name, units, kept_cells, (lower, upper), "no species caught in every season")
    trends = season_trends(series, cells)
    results = species_results(series, trends)
    if len(results) < MIN_SPECIES:
        return _empty(
            name,
            units,
            kept_cells,
            (lower, upper),
            f"{len(results)} species with fifteen years in every season, under {MIN_SPECIES}",
        )

    q_values = np.array([r.q for r in results])
    degrees = int(sum(r.seasons - 1 for r in results))
    amplitudes = np.array([r.amplitude for r in results])
    amplitude_errors = np.array([r.amplitude_stderr for r in results])

    # The season the control runs in: the one with the most usable species (amendment B).
    per_unit = (
        trends.group_by(UNIT).agg(pl.len().alias("n")).sort(["n", UNIT], descending=[True, False])
    )
    control = split_half_control(cells, str(per_unit[UNIT][0])) if per_unit.height else None

    return FamilyResult(
        coverage=Coverage(
            family=name,
            units=units,
            cells=kept_cells,
            years=(lower, upper),
            species=len(results),
            dropped=None,
        ),
        species=tuple(results),
        q_total=float(np.sum(q_values)),
        q_bar=float(stats.chi2.ppf(0.95, degrees)),
        median_root_q=float(np.median([r.root_q for r in results])),
        median_amplitude=float(np.median(np.abs(amplitudes))),
        amplitude_q=_heterogeneity(amplitudes, amplitude_errors),
        amplitude_q_bar=float(stats.chi2.ppf(0.95, len(results) - 1)),
        pair_correlation=pair_correlation(trends, units),
        control_median=control,
    )


def _empty(
    name: str, units: tuple[str, ...], cells: int, years: tuple[int, int], why: str
) -> FamilyResult:
    return FamilyResult(
        coverage=Coverage(
            family=name, units=units, cells=cells, years=years, species=0, dropped=why
        ),
        species=(),
        q_total=float("nan"),
        q_bar=float("nan"),
        median_root_q=float("nan"),
        median_amplitude=float("nan"),
        amplitude_q=float("nan"),
        amplitude_q_bar=float("nan"),
        pair_correlation=float("nan"),
        control_median=None,
    )


def correlation(families: tuple[FamilyResult, ...], *, draws: int) -> Correlation:
    """Prediction 5, pooled over families against a within-family shuffle null.

    Shuffled inside a family, because families differ in both amplitude and disagreement and a
    pooled shuffle would test that difference rather than the relation inside a region.
    """
    blocks: list[tuple[np.ndarray, np.ndarray, str]] = []
    for family in families:
        if not family.coverage.passes:
            continue
        amplitudes = np.abs([r.amplitude for r in family.species])
        roots = np.array([r.root_q for r in family.species])
        finite = np.isfinite(amplitudes) & np.isfinite(roots)
        if finite.sum() > PAIR:
            blocks.append((amplitudes[finite], roots[finite], family.coverage.family))
    if not blocks:
        return Correlation(rho=float("nan"), null_low=float("nan"), null_high=float("nan"), pairs=0)

    observed = stats.spearmanr(
        np.concatenate([a for a, _, _ in blocks]), np.concatenate([r for _, r, _ in blocks])
    ).statistic
    null = np.empty(draws, dtype=float)
    generators = [np.random.default_rng(_seed(name)) for _, _, name in blocks]
    for draw in range(draws):
        shuffled = [rng.permutation(a) for rng, (a, _, _) in zip(generators, blocks, strict=True)]
        null[draw] = stats.spearmanr(
            np.concatenate(shuffled), np.concatenate([r for _, r, _ in blocks])
        ).statistic
    finite_null = null[np.isfinite(null)]
    low, high = np.percentile(finite_null, [2.5, 97.5]) if finite_null.size else (np.nan, np.nan)
    return Correlation(
        rho=float(observed),
        null_low=float(low),
        null_high=float(high),
        pairs=int(sum(a.size for a, _, _ in blocks)),
    )


def calibration(frame: pl.DataFrame) -> dict[str, float]:
    """Each published unit's pooled median trend on its own footprint, with no seasonal restriction.

    This is Phase 1b's quantity recomputed through this module's call path. It is the one number
    here that has a published value to miss, and on the registered run it missed: BITS-1 came out
    at -0.098 against a published -0.183, because Phase 1b fits a level shift at each unit's gear
    change year and this did not. The break term is Phase 1b's own, called rather than restated.
    """
    out: dict[str, float] = {}
    for unit in CALIBRATION:
        rows = frame.filter(pl.col(UNIT) == unit)
        if rows.is_empty():
            continue
        restricted, _ = consistent_footprint(to_cells(rows))
        series = centroids(restricted, group_by=TAXON)
        if series.is_empty():
            continue
        trends = shift_per_decade(
            series,
            column=LATITUDE,
            group_by=TAXON,
            min_years=phase1b.MIN_YEARS,
            break_year=phase1b.gear_change_year(restricted),
        )
        median = trends["per_decade"].median() if not trends.is_empty() else None
        if isinstance(median, (int, float)):
            out[unit] = float(median)
    return out


def collect(*, draws: int = DRAWS) -> Phase2h:
    """Every family, the calibration, and the amplitude-disagreement relation."""
    frame = load()
    log.info("fishglob: %d rows, %d units", frame.height, frame[UNIT].n_unique())
    families = tuple(family_result(frame, name, units) for name, units in FAMILIES.items())
    for family in families:
        cover = family.coverage
        log.info(
            "%s: %s, %d shared cells, %d-%d, %d species%s",
            cover.family,
            "/".join(cover.units),
            cover.cells,
            *cover.years,
            cover.species,
            "" if cover.passes else f" -- DROPPED: {cover.dropped}",
        )
    return Phase2h(
        families=families,
        calibration=calibration(frame),
        correlation=correlation(families, draws=draws),
    )


# --- The report -----------------------------------------------------------------------------


def _family_lines(family: FamilyResult) -> list[str]:
    cover = family.coverage
    if not cover.passes:
        return [f"  {cover.family}: DROPPED -- {cover.dropped}"]
    control = "uncontrolled" if family.control_median is None else f"{family.control_median:.2f}"
    return [
        f"  {cover.family} ({'/'.join(cover.units)}): {cover.species} species, "
        f"{cover.cells} shared cells, {cover.years[0]}-{cover.years[1]}",
        f"    disagreement Q {family.q_total:.1f} against {family.q_bar:.1f}"
        f" ({'CLEARS' if family.disagrees else 'quiet'}); median |z| {family.median_root_q:.2f}; "
        f"split-half |z| {control}",
        f"    amplitude median {family.median_amplitude:+.3f} deg, Q {family.amplitude_q:.1f} "
        f"against {family.amplitude_q_bar:.1f}; between-season trend rho "
        f"{family.pair_correlation:+.2f}",
    ]


def render() -> str:
    """Every family, the calibration first, and one verdict line."""
    read = collect()
    out = [
        "Phase 2h -- is a marine where-shift a range shift, or a cut through a season?",
        "=" * 78,
        "Pre-registered in docs/methods/phase2h-phase-cut.md before any seasonal contrast",
        "was computed. The calibration must reproduce Phase 1b's published per-unit medians",
        "before anything else is read, and the split-half control decides whether the",
        "disagreement can be read at all. Predictions are graded in the note.",
        "",
        "calibration, against Phase 1b:",
    ]
    for unit, target in CALIBRATION.items():
        got = read.calibration.get(unit)
        mark = (
            "MISSING"
            if got is None
            else ("PASS" if abs(got - target) < CALIBRATION_TOLERANCE else "FAIL")
        )
        shown = "--" if got is None else f"{got:+.3f}"
        out.append(f"  {unit}: {shown} against {target:+.3f}: {mark}")
    out.append("")

    for family in read.families:
        out += _family_lines(family)
    out.append("")

    passing = read.passing
    disagreeing = [f for f in passing if f.disagrees]
    out += [
        f"families passing coverage: {len(passing)} of {len(read.families)} (floor {MIN_FAMILIES})",
        f"families whose seasons disagree beyond their errors: {len(disagreeing)} of "
        f"{len(passing)}",
        f"amplitude against disagreement: rho {read.correlation.rho:+.3f} against a null of "
        f"[{read.correlation.null_low:+.3f}, {read.correlation.null_high:+.3f}] "
        f"on {read.correlation.pairs} species",
        "",
    ]

    verdict: list[str] = []
    if not read.calibrated:
        verdict.append("calibration FAILED -- nothing above it is read")
    elif len(passing) < MIN_FAMILIES:
        verdict.append(
            f"coverage FAILED: {len(passing)} families under the floor of {MIN_FAMILIES}"
        )
    elif not read.controlled:
        verdict.append("split-half control FIRED -- the seasons' disagreement is not interpretable")
    else:
        share = len(disagreeing) / len(passing)
        verdict.append(
            "the seasons disagree about the decadal shift in "
            f"{len(disagreeing)} of {len(passing)} families"
            f" ({'over' if share >= FAMILIES_FOR_DISAGREEMENT else 'under'} half)"
        )
        verdict.append(
            "amplitude "
            + ("predicts" if read.correlation.clears_null else "does not predict")
            + " the disagreement"
        )
    return "\n".join([*out, "VERDICT: " + "; ".join(verdict)])
