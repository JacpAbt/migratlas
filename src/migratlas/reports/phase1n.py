"""Phase 1n -- with the footprint held equal, what is the protocol difference made of?

Pre-registered in ``docs/methods/phase1n-shared-footprint.md`` before any shared-cell
restriction was computed.

`protocol-disagreement` publishes a noise-corrected method-to-species scatter of 1.17 on a
comparison where the two Swedish programmes were measured over **different areas** -- 33
consistently sampled cells against 84. Phase 1l and Phase 1m both closed by naming that as the next
thing to fix and neither did, so part of what the ledger calls protocol is geography and nobody
knows what part.

Then #67: a constant offset is a calibration and correctable; a difference that varies with
something names that something. Both covariates here are properties of the *species* rather than of
the difference, which is the circularity Phase 1m named and Phase 3i refused.
"""

import logging
from dataclasses import dataclass
from typing import Final

import numpy as np
import polars as pl

from migratlas.metrics import range as range_metrics
from migratlas.models.influence import Influence, leave_one_out
from migratlas.reports import phase1k, phase1l

log = logging.getLogger(__name__)

SEED: Final = 1
BOOTSTRAP: Final = 1_000

PUBLISHED_RATIO: Final = 1.17
RATIO_TOLERANCE: Final = 5e-3
"""Two significant figures, which is what the calibration promised."""

MIN_SHARED_SPECIES: Final = 60
"""A third of Phase 1l's 166, fixed in the registration rather than against the answer."""

DETECTABILITY: Final = "detectability"
LATITUDE: Final = "where it lives"
COVARIATES: Final[tuple[str, ...]] = (DETECTABILITY, LATITUDE)


@dataclass(frozen=True, slots=True)
class Footprints:
    """What each network kept, and what they keep in common."""

    per_network: dict[str, int]
    shared: int


@dataclass(frozen=True, slots=True)
class Slope:
    """One covariate's relationship with the paired difference."""

    covariate: str
    slope: float
    ci: float
    leverage: Influence | None

    @property
    def clears_zero(self) -> bool:
        return abs(self.slope) > self.ci


@dataclass(frozen=True, slots=True)
class Shared:
    """The phase: the calibration, the restricted ratio, and the shape of what is left."""

    calibration: float
    footprints: Footprints
    species: int
    offset: float
    offset_ci: float
    ratio: float
    noise_share: float
    slopes: tuple[Slope, ...]

    @property
    def calibrated(self) -> bool:
        return abs(self.calibration - PUBLISHED_RATIO) < RATIO_TOLERANCE

    @property
    def offset_clears_zero(self) -> bool:
        return abs(self.offset) > self.offset_ci


def _kept_cells(source_id: str, years: tuple[int, int]) -> pl.DataFrame:
    """One network's consistent cells inside the shared window.

    The window is applied before the cells are formed, exactly as `phase1l._slopes` applies it: a
    footprint computed over the whole span and then trimmed would keep cells that are not consistent
    inside the years actually fitted.
    """
    frame = phase1k.load_counts(source_id).filter(
        pl.col("period_start").dt.year().is_between(years[0], years[1])
    )
    cells = range_metrics.to_cells(frame)
    kept, _ = range_metrics.consistent_footprint(cells)
    if kept.is_empty():
        return pl.DataFrame()
    return kept


def footprints(years: tuple[int, int]) -> tuple[Footprints, pl.DataFrame, dict[str, pl.DataFrame]]:
    """Each network's consistent cells, their intersection, and the restricted rows.

    Each network's own consistency rule is applied first and the intersection taken afterwards, so
    neither is relaxed to manufacture overlap -- which would be choosing a footprint to suit the
    answer rather than restricting to one.
    """
    kept = {source_id: _kept_cells(source_id, years) for source_id in phase1l.PAIR}
    sets = []
    for frame in kept.values():
        if frame.is_empty():
            return Footprints(per_network={}, shared=0), pl.DataFrame(), {}
        sets.append(frame.select("cell_longitude", "cell_latitude").unique())
    shared = sets[0].join(sets[1], on=["cell_longitude", "cell_latitude"], how="inner")
    restricted = {
        source_id: frame.join(shared, on=["cell_longitude", "cell_latitude"], how="inner")
        for source_id, frame in kept.items()
    }
    return (
        Footprints(
            per_network={
                source_id: frame.height for source_id, frame in zip(kept, sets, strict=True)
            },
            shared=shared.height,
        ),
        shared,
        restricted,
    )


def _slopes_on(rows: pl.DataFrame) -> pl.DataFrame:
    """Per-species slopes on an already-restricted set of rows."""
    series = range_metrics.centroids(rows)
    if series.is_empty():
        return pl.DataFrame()
    return range_metrics.shift_per_decade(
        series, column="mean_latitude", min_years=phase1k.MIN_YEARS
    ).select(
        taxon_key=pl.col("taxon_key").cast(pl.String),
        slope=pl.col("per_decade"),
        stderr=pl.col("stderr"),
    )


def _covariates(restricted: dict[str, pl.DataFrame]) -> pl.DataFrame:
    """Per species: how readily it is counted, and where it lives.

    Detectability is pooled over *both* programmes deliberately. Taking it from one would make the
    covariate one protocol's view of the species, which is the thing under test.
    """
    both = pl.concat(
        [
            frame.select("taxon_key", "count", "effort", "cell_latitude")
            for frame in restricted.values()
        ]
    )
    return (
        both.with_columns(taxon_key=pl.col("taxon_key").cast(pl.String))
        .group_by("taxon_key")
        .agg(
            **{
                DETECTABILITY: (pl.col("count").sum() / pl.col("effort").sum()),
                LATITUDE: pl.col("cell_latitude").mean(),
            }
        )
    )


def _regress(difference: np.ndarray, covariate: np.ndarray, *, name: str) -> Slope:
    """Least squares of the paired difference on one standardised covariate.

    The unit is the species and species are the independent thing here -- which is the one place in
    this project where that is true rather than assumed, since a species appears once.
    """
    usable = np.isfinite(difference) & np.isfinite(covariate)
    y, x = difference[usable], covariate[usable]
    spread = x.std(ddof=1)
    if y.size < 3 or spread == 0:  # noqa: PLR2004 -- a slope through two points has no interval
        return Slope(covariate=name, slope=float("nan"), ci=float("nan"), leverage=None)
    standardised = (x - x.mean()) / spread

    def fit(rows: np.ndarray) -> float:
        design = np.column_stack([np.ones(rows.size), standardised[rows]])
        solution, *_ = np.linalg.lstsq(design, y[rows], rcond=None)
        return float(solution[1])

    everything = np.arange(y.size)
    slope = fit(everything)
    rng = np.random.default_rng(SEED)
    draws = np.array(
        [fit(rng.integers(0, y.size, size=y.size)) for _ in range(BOOTSTRAP)], dtype=float
    )
    low, high = np.percentile(draws, [2.5, 97.5])

    # ADR 0016, reported whether or not it binds: 166 species is above its floor of 30, but the
    # shared-footprint panel may not be.
    indices = list(range(y.size))
    leverage = leave_one_out(
        indices,
        lambda subset: (fit(np.array(list(subset))), float(high - low) / 2.0),
        name=str,
    )
    return Slope(covariate=name, slope=slope, ci=float(high - low) / 2.0, leverage=leverage)


def collect() -> Shared | None:
    """The calibration, the restricted ratio, and the two covariate slopes."""
    published = phase1l.decompose()
    if published is None or published.method_sd is None or not published.species_sd:
        log.warning("phase1n: the published decomposition is unavailable, so nothing is calibrated")
        return None
    calibration = published.method_sd / published.species_sd

    years = phase1l.shared_window()
    counts, _, restricted = footprints(years)
    if not restricted:
        log.warning("phase1n: one network kept no consistent cells inside the shared window")
        return None

    slopes = {source_id: _slopes_on(rows) for source_id, rows in restricted.items()}
    first, second = (slopes[source_id] for source_id in phase1l.PAIR)
    if first.is_empty() or second.is_empty():
        return None
    paired = first.join(second, on="taxon_key", how="inner", suffix="_two")
    if paired.height < MIN_SHARED_SPECIES:
        log.info("phase1n: %d species on the shared footprint, under the floor", paired.height)

    split = phase1l.split_difference(
        paired["slope"].to_numpy().astype(float),
        paired["slope_two"].to_numpy().astype(float),
        paired["stderr"].to_numpy().astype(float),
        paired["stderr_two"].to_numpy().astype(float),
    )
    difference = (paired["slope"] - paired["slope_two"]).to_numpy().astype(float)
    offset = float(np.mean(difference))
    offset_ci = 1.96 * float(np.std(difference, ddof=1)) / np.sqrt(difference.size)

    joined = paired.join(_covariates(restricted), on="taxon_key", how="left")
    measured = tuple(
        _regress(
            (joined["slope"] - joined["slope_two"]).to_numpy().astype(float),
            joined[name].to_numpy().astype(float),
            name=name,
        )
        for name in COVARIATES
    )
    return Shared(
        calibration=calibration,
        footprints=counts,
        species=paired.height,
        offset=offset,
        offset_ci=offset_ci,
        ratio=(
            split.method_sd / split.species_sd
            if split.method_sd is not None and split.species_sd
            else float("nan")
        ),
        noise_share=split.noise_share,
        slopes=measured,
    )


def render() -> str:
    """Every registered prediction's quantity, and one verdict line."""
    out = [
        "Phase 1n -- with the footprint held equal, what is the protocol difference made of?",
        "=" * 78,
        "Pre-registered in docs/methods/phase1n-shared-footprint.md before any restriction was",
        "computed. Both covariates are properties of the species, never of the difference.",
        "",
    ]
    read = collect()
    if read is None:
        return "\n".join([*out, "VERDICT: nothing to read."])

    out += [
        f"Calibration -- Phase 1l's ratio on the unrestricted footprint: {read.calibration:.4f} "
        f"against {PUBLISHED_RATIO:.2f} -- {'PASS' if read.calibrated else 'FAIL'}",
        "",
    ]
    if not read.calibrated:
        return "\n".join([*out, "VERDICT: calibration FAILED -- nothing below is interpreted."])

    kept = "  ".join(f"{name} {count}" for name, count in read.footprints.per_network.items())
    out += [
        f"Consistent cells: {kept}  ->  shared {read.footprints.shared}",
        f"Species on the shared footprint: {read.species} "
        f"(floor {MIN_SHARED_SPECIES}{'' if read.species >= MIN_SHARED_SPECIES else ' -- BELOW'})",
        "",
        f"Ratio on the shared footprint: {read.ratio:.3f} against {PUBLISHED_RATIO:.2f} published",
        f"  estimation error is {read.noise_share:.0%} of the raw paired disagreement",
        f"Constant offset: {read.offset:+.4f} +/- {read.offset_ci:.4f} deg latitude per decade -- "
        f"{'clears' if read.offset_clears_zero else 'inside'} zero",
        "",
        "What the difference varies with:",
    ]
    for slope in read.slopes:
        verdict = "clears zero" if slope.clears_zero else "inside zero"
        room = ""
        if slope.leverage is not None and not slope.leverage.publishable:
            room = " -- and does NOT survive dropping one species"
        out.append(
            f"  {slope.covariate:16s} {slope.slope:+.4f} +/- {slope.ci:.4f} per sd -- "
            f"{verdict}{room}"
        )
    out += ["", "Predictions are graded in the method note, not here."]

    fell = read.ratio < PUBLISHED_RATIO
    above_one = read.ratio > 1.0
    varying = [slope.covariate for slope in read.slopes if slope.clears_zero]
    out.append(
        f"VERDICT: ratio {read.ratio:.3f} ({'fell' if fell else 'did not fall'}, "
        f"{'still above' if above_one else 'now below'} 1); "
        f"{'varies with ' + ', '.join(varying) if varying else 'no covariate slope clears zero'}"
    )
    return "\n".join(out)


def sampling_drift() -> dict[str, float]:
    """Where each programme's *sampling* went over time, with no species in it at all.

    UNREGISTERED, and labelled so wherever it prints. §5 asked for no such diagnostic, so it can
    never be a graded prediction -- run after the offset was seen, it could only confirm a hunch.

    It is here because the offset needs an explanation and "a constant difference in a rate" names a
    shape rather than a mechanism. The most obvious mechanism is bookkeeping: a centroid is an
    effort-weighted mean position, so if one programme's effort drifts north relative to the
    other's,
    *every* species' centroid drifts with it by the same amount -- which is exactly a constant rate
    offset that does not vary with detectability or with where a species lives.

    The consistency rule keeps a cell only where it was sampled in 80% of years. It says nothing
    about how much effort each kept cell got in each year, and the centroid is weighted by that.
    """
    years = phase1l.shared_window()
    _, _, restricted = footprints(years)
    drift: dict[str, float] = {}
    for source_id, rows in restricted.items():
        per_year = (
            rows.group_by("year")
            .agg(
                latitude=(
                    (pl.col("cell_latitude") * pl.col("effort")).sum() / pl.col("effort").sum()
                )
            )
            .drop_nulls()
            .sort("year")
        )
        if per_year.height < 3:  # noqa: PLR2004 -- a trend through two points is a line
            drift[source_id] = float("nan")
            continue
        fit = np.polyfit(
            per_year["year"].to_numpy().astype(float),
            per_year["latitude"].to_numpy().astype(float),
            1,
        )
        drift[source_id] = float(fit[0] * 10.0)
    first, second = (drift.get(source_id, float("nan")) for source_id in phase1l.PAIR)
    drift["difference"] = first - second
    return drift
