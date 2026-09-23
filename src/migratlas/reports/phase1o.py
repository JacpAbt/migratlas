"""Phase 1o -- is the level between one species and all of them a taxonomic one?

Pre-registered in ``docs/methods/phase1o-taxonomic-groups.md`` before the rank lookup was fetched.
"""

import logging
from dataclasses import dataclass
from typing import Final

import numpy as np
import polars as pl

from migratlas.evidence.types import EvidenceType
from migratlas.lake.reader import scan
from migratlas.metrics import range as range_metrics
from migratlas.reports import phase1k, phase1l, phase1m

log = logging.getLogger(__name__)

SEED: Final = 1

FAMILY: Final = "family"
ORDER: Final = "order"
AXES: Final[tuple[str, ...]] = (FAMILY, ORDER)

MIN_MEMBERS: Final = 5
"""Species per group, the floor Phase 1m's stop condition used."""

MIN_RESOLVED: Final = 0.90
"""Prediction 1: below this the lookup is the finding rather than the grouping."""

DOMINANT_SHARE: Final = 2.0 / 3.0
"""Above this, one group holds so much of the panel that a near-zero coherence is arithmetic.

Registered in §2 as the most likely way this phase fails to answer its own question: a temperate
bird survey is mostly one order, and a grouping with one dominant group has almost no
between-group variance available to it whatever the taxonomy is worth.
"""


@dataclass(frozen=True, slots=True)
class AxisResult:
    """One network, one taxonomic axis."""

    source_id: str
    axis: str
    groups: int
    species: int
    dropped: int
    """Species in groups below the member floor."""
    largest_share: float
    signal: float
    coherence_raw: float
    coherence_corrected: float

    @property
    def interpretable(self) -> bool:
        """False when one group holds the panel: then a low coherence means nothing."""
        return self.largest_share <= DOMINANT_SHARE

    @property
    def clears_floor(self) -> bool:
        return bool(np.isfinite(self.coherence_corrected)) and (
            self.coherence_corrected > phase1m.ICC_FLOOR
        )


@dataclass(frozen=True, slots=True)
class Phase1o:
    """The lookup's success rate, and one result per network per axis."""

    keys: int
    resolved: int
    axes: tuple[AxisResult, ...]
    paired_ratio: float

    @property
    def resolved_share(self) -> float:
        return self.resolved / self.keys if self.keys else float("nan")

    @property
    def lookup_holds(self) -> bool:
        return self.resolved_share >= MIN_RESOLVED

    def best(self, axis: str) -> AxisResult | None:
        usable = [
            item
            for item in self.axes
            if item.axis == axis and item.interpretable and np.isfinite(item.coherence_corrected)
        ]
        return max(usable, key=lambda item: item.coherence_corrected) if usable else None


def _keys_in_use() -> list[int]:
    """Every distinct taxon key across the count networks and the flight-date scheme."""
    found: set[int] = set()
    for source_id in (*phase1k.COUNT_NETWORKS, phase1k.FLIGHT_NETWORK):
        keys = (
            scan(EvidenceType.SURVEY_INDEX, source_id=source_id)
            .select("taxon_key")
            .unique()
            .collect()["taxon_key"]
            .drop_nulls()
            .to_list()
        )
        found |= {int(key) for key in keys}
    return sorted(found)


def ranks() -> pl.DataFrame:
    """Family and order per taxon key, from the cached Backbone lookup."""
    from migratlas.taxonomy import gbif  # noqa: PLC0415 -- network on first call only

    keys = _keys_in_use()
    resolved = gbif.classifications(keys)
    return pl.DataFrame(
        [
            {
                "taxon_key": str(key),
                FAMILY: resolved.get(key, {}).get(FAMILY),
                ORDER: resolved.get(key, {}).get(ORDER),
            }
            for key in keys
        ]
    )


def _slopes(source_id: str) -> pl.DataFrame:
    """One network's per-species slopes, on its own consistent footprint.

    Phase 1k's floor and footprint rule, called through the same helpers, so a group here is a group
    of the same species Phase 1m grouped by latitude.
    """
    cells = range_metrics.to_cells(phase1k.load_counts(source_id))
    kept, _ = range_metrics.consistent_footprint(cells)
    if kept.is_empty():
        return pl.DataFrame()
    series = range_metrics.centroids(kept)
    if series.is_empty():
        return pl.DataFrame()
    return range_metrics.shift_per_decade(
        series, column="mean_latitude", min_years=phase1k.MIN_YEARS
    ).select(
        taxon_key=pl.col("taxon_key").cast(pl.String),
        slope=pl.col("per_decade"),
        stderr=pl.col("stderr"),
    )


def _axis(
    source_id: str, slopes: pl.DataFrame, rank_table: pl.DataFrame, axis: str
) -> AxisResult | None:
    """One network on one axis: the signal, the coherence, and whether it can be read."""
    joined = slopes.join(rank_table, on="taxon_key", how="left").drop_nulls(axis)
    if joined.is_empty():
        return None
    sizes = joined.group_by(axis).agg(members=pl.len())
    big = sizes.filter(pl.col("members") >= MIN_MEMBERS)[axis]
    table = joined.filter(pl.col(axis).is_in(big)).rename({axis: "group"})

    if table.is_empty() or table["group"].n_unique() < 2:  # noqa: PLR2004
        log.info("%s/%s: fewer than two groups clear the member floor", source_id, axis)
        return None

    counts = table.group_by("group").agg(members=pl.len())["members"].to_numpy()
    raw, corrected = phase1m._icc(table)  # noqa: SLF001 -- Phase 1m's own measure, not a second one

    # The group's slope is the unweighted mean of its members', with the error propagated -- Phase
    # 1m's estimand, so "family beats latitude" compares like with like.
    per_group = table.group_by("group").agg(
        mean=pl.col("slope").mean(),
        error=(pl.col("stderr").pow(2).sum().sqrt() / pl.len()),
    )
    ratios = (per_group["mean"] / per_group["error"]).abs().to_numpy().astype(float)
    finite = ratios[np.isfinite(ratios)]
    return AxisResult(
        source_id=source_id,
        axis=axis,
        groups=int(table["group"].n_unique()),
        species=table.height,
        dropped=joined.height - table.height,
        largest_share=float(counts.max() / counts.sum()),
        signal=float(np.median(finite)) if finite.size else float("nan"),
        coherence_raw=raw,
        coherence_corrected=corrected,
    )


def _grouped(slopes: pl.DataFrame, rank_table: pl.DataFrame, axis: str) -> pl.DataFrame:
    """One network's slopes collapsed to group means, with the members' error propagated."""
    joined = slopes.join(rank_table, on="taxon_key", how="left").drop_nulls(axis)
    if joined.is_empty():
        return pl.DataFrame()
    sizes = joined.group_by(axis).agg(members=pl.len())
    big = sizes.filter(pl.col("members") >= MIN_MEMBERS)[axis]
    return (
        joined.filter(pl.col(axis).is_in(big))
        .group_by(axis)
        .agg(
            slope=pl.col("slope").mean(),
            stderr=(pl.col("stderr").pow(2).sum().sqrt() / pl.len()),
        )
        .rename({axis: "group"})
    )


def paired_at_group_level(rank_table: pl.DataFrame) -> float:
    """Prediction 5: Phase 1l's method-to-species ratio with families as the unit.

    Registered because Phase 1m showed the protocol difference is systematic and Phase 1n has since
    shown it is a constant offset -- and an offset cannot be averaged away by any grouping. A ratio
    that fell here would contradict two published results rather than add to them.
    """
    grouped = {
        source_id: _grouped(_slopes(source_id), rank_table, FAMILY) for source_id in phase1l.PAIR
    }
    first, second = (grouped[source_id] for source_id in phase1l.PAIR)
    if first.is_empty() or second.is_empty():
        return float("nan")
    paired = first.join(second, on="group", how="inner", suffix="_two")
    if paired.height < 3:  # noqa: PLR2004 -- a variance over two groups is not one
        return float("nan")
    split = phase1l.split_difference(
        paired["slope"].to_numpy().astype(float),
        paired["slope_two"].to_numpy().astype(float),
        paired["stderr"].to_numpy().astype(float),
        paired["stderr_two"].to_numpy().astype(float),
    )
    if split.method_sd is None or not split.species_sd:
        return float("nan")
    return split.method_sd / split.species_sd


def collect() -> Phase1o | None:
    """The lookup, then every network on every axis."""
    rank_table = ranks()
    if rank_table.is_empty():
        return None
    resolved = rank_table.drop_nulls(FAMILY).height

    results: list[AxisResult] = []
    for source_id in phase1k.COUNT_NETWORKS:
        slopes = _slopes(source_id)
        if slopes.is_empty():
            log.info("%s: no qualifying species", source_id)
            continue
        for axis in AXES:
            found = _axis(source_id, slopes, rank_table, axis)
            if found is not None:
                results.append(found)

    return Phase1o(
        keys=rank_table.height,
        resolved=resolved,
        axes=tuple(results),
        paired_ratio=paired_at_group_level(rank_table),
    )


def render() -> str:
    """The lookup, the table, and one verdict line."""
    out = [
        "Phase 1o -- is the level between one species and all of them a taxonomic one?",
        "=" * 78,
        "Pre-registered in docs/methods/phase1o-taxonomic-groups.md before the lookup was fetched.",
        "Family and order only: the Backbone is a taxonomy and says nothing about migration.",
        "Coherence is the primary: averaging raises a signal whether or not a group is real.",
        "",
    ]
    read = collect()
    if read is None:
        return "\n".join([*out, "VERDICT: no rank table -- nothing to read."])

    out += [
        f"Lookup: {read.resolved} of {read.keys} keys resolved to a family "
        f"({read.resolved_share:.1%}) -- {'PASS' if read.lookup_holds else 'FAIL'}",
        "",
    ]
    if not read.lookup_holds:
        return "\n".join([*out, "VERDICT: the lookup is the finding; nothing else is graded."])

    header = (
        f"{'network':22s} {'axis':7s} {'groups':>6s} {'spp':>5s} {'drop':>5s} "
        f"{'largest':>8s} {'signal':>7s} {'coherence':>10s}"
    )
    out.append(header)
    for item in read.axes:
        mark = "" if item.interpretable else "  <- one group holds the panel"
        out.append(
            f"{item.source_id:22s} {item.axis:7s} {item.groups:6d} {item.species:5d} "
            f"{item.dropped:5d} {item.largest_share:7.0%} {item.signal:7.2f} "
            f"{item.coherence_corrected:10.3f}{mark}"
        )

    family_clears = [
        item
        for item in read.axes
        if item.axis == FAMILY and item.interpretable and item.clears_floor
    ]
    out += [
        "",
        "Species level, for comparison: signal 1.69, paired ratio 1.17 (Phase 1l), 1.15 at "
        "Phase 1m's group level",
        f"Paired ratio with families as the unit: {read.paired_ratio:.3f}",
        f"Phase 1m's descriptive axes cleared the {phase1m.ICC_FLOOR:.2f} floor in one network "
        "of three.",
        "",
        "Predictions are graded in the method note, not here.",
    ]
    best = read.best(FAMILY)
    verdict = (
        f"family clears the {phase1m.ICC_FLOOR:.2f} floor in {len(family_clears)} network(s)"
        + (f", best {best.coherence_corrected:.3f} at {best.source_id}" if best else "")
    )
    return "\n".join([*out, f"VERDICT: {verdict}"])


def subsampled_coherence(source_id: str, size: int, draws: int = 200) -> tuple[float, float]:
    """Family coherence on random subsets of one network, at a chosen panel size.

    UNREGISTERED, and labelled so wherever it prints. §4 asked for no such diagnostic and this could
    only ever confirm a suspicion, having been run after the pattern was seen.

    It is here because the pattern needs separating rather than flagging. Family coherence falls as
    the panel grows -- 0.346 at 127 species, 0.192 at 141, 0.094 at 459 -- and at least three things
    produce that ordering:

    * the noise-corrected estimate is biased upward when the between-group term is poorly
    determined,
      which is a property of the estimator and nothing to do with taxonomy;
    * `bbs` spans a continent while the Swedish networks span one country, so a family's members
      there experience far more different climates and genuinely disagree more -- which is biology,
      not bias;
    * the species pools are different families entirely, North American against European.

    **Thinning `bbs` to the Swedish panel size separates the first from the other two.** If a
    127-species draw from `bbs` returns something near 0.35, the ordering is sample size. If it
    stays
    near 0.09, the ordering is the continent or the pool, and family really does bind more tightly
    in
    Sweden.

    Returns the median and the 90th percentile across draws.
    """
    rank_table = ranks()
    slopes = _slopes(source_id)
    if slopes.is_empty() or rank_table.is_empty():
        return (float("nan"), float("nan"))
    joined = slopes.join(rank_table, on="taxon_key", how="left").drop_nulls(FAMILY)
    if joined.height <= size:
        return (float("nan"), float("nan"))

    rng = np.random.default_rng(SEED)
    found: list[float] = []
    for _ in range(draws):
        picked = joined[rng.choice(joined.height, size=size, replace=False)]
        sizes = picked.group_by(FAMILY).agg(members=pl.len())
        big = sizes.filter(pl.col("members") >= MIN_MEMBERS)[FAMILY]
        table = picked.filter(pl.col(FAMILY).is_in(big)).rename({FAMILY: "group"})
        if table.is_empty() or table["group"].n_unique() < 2:  # noqa: PLR2004
            continue
        _, corrected = phase1m._icc(table)  # noqa: SLF001 -- Phase 1m's own measure
        if np.isfinite(corrected):
            found.append(corrected)
    if not found:
        return (float("nan"), float("nan"))
    return (float(np.median(found)), float(np.percentile(found, 90)))
