"""Phase 1m — is there a level between one species and all of them?

Pre-registered in ``docs/methods/phase1m-species-groups.md`` before any group was formed. The
owner's proposal, on Phase 3h's reasoning: one species is too noisy to read (median slope 1.69
standard errors from zero) and a whole network is a mixture, so the question is whether the species
axis has a middle the way the spatial axis did.

**The grouping is not the outcome, and the reason is arithmetic rather than assertion.**
``shift_per_decade`` centres the year before fitting, so intercept and slope are estimated
orthogonally. Grouping on where a species lives and measuring how it moved shares no estimation
error. Grouping on the trend itself would make every group coherent by construction, which is the
thing Phase 3h and Phase 3i both refused.
"""

import logging
from dataclasses import dataclass
from typing import Final

import numpy as np
import polars as pl

from migratlas.metrics import range as range_metrics
from migratlas.reports import phase1k, phase1l

log = logging.getLogger(__name__)

# Ten, chosen against Phase 3h's experience rather than tuned: eleven units carried a median there
# and could not carry a count, and ten of roughly seventeen species gives a fourfold noise reduction
# inside a group while leaving enough groups to measure spread between them.
GROUPS: Final = 10

# Below this a group is not measured, and below eight such groups the phase stops.
MIN_MEMBERS: Final = 5
MIN_GROUPS: Final = 8

# What Phase 1l measured at species level, quoted so the predictions are graded against numbers.
SPECIES_SIGNAL: Final = 1.69
SPECIES_RATIO: Final = 1.17
ICC_FLOOR: Final = 0.10


@dataclass(frozen=True, slots=True)
class GroupLevel:
    """One network's answer at group level, and the check that the grouping earned it."""

    source_id: str
    axis: str
    """Which grouping was used: where the species lives, or how widely it is spread."""
    groups: int
    members_median: int
    signal: float
    """Median |group slope| over its own standard error. Species level was 1.69."""
    icc: float
    """Between-group share of species-level variance, with estimation error removed."""
    icc_raw: float


def _species_table(source_id: str, window: tuple[int, int]) -> pl.DataFrame:
    """Per-species slope, its error, and the two grouping axes -- all from one pass.

    The mean latitude comes from the same centroid series the slope is fitted to, which is the
    point: it is that fit's intercept, estimated orthogonally to its slope.
    """
    frame = phase1k.load_counts(source_id).filter(
        pl.col("period_start").dt.year().is_between(window[0], window[1])
    )
    cells = range_metrics.to_cells(frame)
    kept, _ = range_metrics.consistent_footprint(cells)
    if kept.is_empty():
        return pl.DataFrame()
    series = range_metrics.centroids(kept)
    if series.is_empty():
        return pl.DataFrame()

    shifts = range_metrics.shift_per_decade(
        series, column="mean_latitude", min_years=phase1k.MIN_YEARS
    )
    if shifts.is_empty():
        return pl.DataFrame()

    # Where it lives, and how widely -- the two registered axes, neither of them the trend.
    where = series.group_by("taxon_key").agg(
        lives=pl.col("mean_latitude").mean(),
        spread=pl.col("mean_latitude").std(),
    )
    return (
        shifts.join(where, on="taxon_key", how="inner")
        .drop_nulls(["per_decade", "stderr", "lives"])
        .select(
            taxon_key=pl.col("taxon_key").cast(pl.String),
            slope=pl.col("per_decade"),
            stderr=pl.col("stderr"),
            lives=pl.col("lives"),
            spread=pl.col("spread"),
        )
    )


def _binned(table: pl.DataFrame, axis: str) -> pl.DataFrame:
    """Deciles of one axis, as a group label per species."""
    values = table[axis].to_numpy().astype(float)
    edges = np.percentile(values, np.linspace(0, 100, GROUPS + 1)[1:-1])
    return table.with_columns(group=pl.Series(np.digitize(values, edges)))


def _icc(table: pl.DataFrame) -> tuple[float, float]:
    """Between-group share of variance, raw and with estimation error removed.

    The correction is Phase 1l's: raw scatter across species carries each fit's own error, so a
    between-group share computed against the raw total flatters the grouping. Removing the same
    error term from the denominator is the only comparison that means anything.
    """
    slopes = table["slope"].to_numpy().astype(float)
    errors = table["stderr"].to_numpy().astype(float)
    total = float(np.var(slopes, ddof=1))
    if total <= 0:
        return (float("nan"), float("nan"))

    means = table.group_by("group").agg(mean=pl.col("slope").mean(), members=pl.len())
    weights = means["members"].to_numpy().astype(float)
    centres = means["mean"].to_numpy().astype(float)
    grand = float(np.average(centres, weights=weights))
    between = float(np.average((centres - grand) ** 2, weights=weights))

    noise = float(np.mean(errors**2))
    corrected = total - noise
    return (between / total, between / corrected if corrected > 0 else float("nan"))


def at_group_level(source_id: str, axis: str, window: tuple[int, int]) -> GroupLevel | None:
    """One network, one grouping axis: does a group's trend read where a species' did not?"""
    table = _species_table(source_id, window)
    if table.is_empty():
        return None
    binned = _binned(table, axis)

    rows = binned.group_by("group").agg(
        members=pl.len(),
        slope=pl.col("slope").mean(),
        # Propagated: the mean of k independent estimates has 1/k**2 of the summed variance.
        stderr=(pl.col("stderr").pow(2).sum().sqrt() / pl.len()),
    )
    usable = rows.filter(pl.col("members") >= MIN_MEMBERS)
    if usable.height < MIN_GROUPS:
        log.info("%s/%s: only %d groups carry members", source_id, axis, usable.height)
        return None

    ratios = np.abs(usable["slope"].to_numpy().astype(float)) / usable["stderr"].to_numpy().astype(
        float
    )
    raw, corrected = _icc(binned)
    return GroupLevel(
        source_id=source_id,
        axis=axis,
        groups=usable.height,
        members_median=int(np.median(usable["members"].to_numpy())),
        signal=float(np.median(ratios[np.isfinite(ratios)])),
        icc=corrected,
        icc_raw=raw,
    )


def paired_at_group_level(window: tuple[int, int]) -> tuple[float, int] | None:
    """Phase 1l's method-to-species ratio, recomputed with groups as the unit.

    The one question averaging might not fix: if two programmes differ in the same direction for
    every species, their group means differ by the same amount and this does not improve.
    """
    first, second = (_species_table(source_id, window) for source_id in phase1l.PAIR)
    if first.is_empty() or second.is_empty():
        return None
    both = first.join(second, on="taxon_key", how="inner", suffix="_other")
    if both.is_empty():
        return None

    # Grouped on the first network's axis, so one label per species rather than two.
    binned = _binned(both, "lives")
    grouped = binned.group_by("group").agg(
        members=pl.len(),
        one=pl.col("slope").mean(),
        two=pl.col("slope_other").mean(),
    )
    usable = grouped.filter(pl.col("members") >= MIN_MEMBERS)
    if usable.height < MIN_GROUPS:
        return None

    one = usable["one"].to_numpy().astype(float)
    two = usable["two"].to_numpy().astype(float)

    def spread(values: np.ndarray) -> float:
        low, high = np.percentile(values, [25, 75])
        return float(high - low)

    denominator = spread(np.concatenate([one, two]))
    return (spread(one - two) / denominator if denominator else float("nan"), usable.height)


def render() -> str:
    """The three registered quantities, per network and per axis."""
    out = [
        "Phase 1m -- a level between one species and all of them",
        "=" * 78,
        "Pre-registered in docs/methods/phase1m-species-groups.md before any group was formed.",
        f"Species level, from Phase 1l: signal {SPECIES_SIGNAL}, method-to-species ratio "
        f"{SPECIES_RATIO}.",
        "",
    ]
    window = phase1l.shared_window()
    out.append(f"  window: {window[0]}-{window[1]}")
    out.append("")

    for axis, label in (("lives", "where it lives"), ("spread", "how widely spread")):
        out.append(f"Grouped by {label} ({axis})")
        for source_id in (*phase1l.PAIR, "bbs"):
            result = at_group_level(source_id, axis, window)
            if result is None:
                out.append(f"  {source_id}: too few groups carry members -- coverage only")
                continue
            out += [
                f"  {source_id}: {result.groups} groups, "
                f"median {result.members_median} species each",
                f"    group signal (median |slope|/se): {result.signal:.2f}"
                f"   [species level {SPECIES_SIGNAL}]",
                f"    ICC corrected: {result.icc:.3f}   raw: {result.icc_raw:.3f}"
                f"   [floor {ICC_FLOOR}]",
            ]
        out.append("")

    paired = paired_at_group_level(window)
    if paired is None:
        out.append("Paired at group level: too few groups -- not computed")
    else:
        ratio, groups = paired
        out += [
            "Paired at group level, where it lives",
            f"  method-to-species ratio across {groups} groups: {ratio:.2f}"
            f"   [species level {SPECIES_RATIO}]",
        ]

    out += ["", "Predictions are graded in the method note, not here."]
    return "\n".join(out)
