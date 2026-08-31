"""Phase 1l — when two programmes count the same birds, how much of the difference is the counting?

Pre-registered in ``docs/methods/phase1l-paired-protocols.md`` before any paired difference was
computed. Phase 1k compared two Swedish networks' medians and found them 3x apart; the owner's
correction was that comparing two averages of *different species mixtures* is the error that
comparison was warning about. This pairs by species instead, so composition cannot contribute.

**The headline is a ratio**, not a difference: the spread of paired differences over the spread of
the slopes themselves. Below 1 and the method matters less than which animal you look at, so the
project's comparative claims are informative. Near or above 1 and every cross-unit claim here is
partly reporting its instruments.
"""

import logging
from dataclasses import dataclass
from typing import Final

import numpy as np
import polars as pl

from migratlas.metrics import range as range_metrics
from migratlas.reports import phase1k

log = logging.getLogger(__name__)

PAIR: Final[tuple[str, str]] = ("sbs_point_counts", "sbs_fixed_routes")

# Phase 1k's unpaired gap, quoted so prediction 1 is graded against a published number.
UNPAIRED_GAP: Final = 0.0633

# Registered floors. Below either, the phase publishes as coverage and claims no ratio.
MIN_SHARED_SPECIES: Final = 100
MIN_SHARED_YEARS: Final = 15


@dataclass(frozen=True, slots=True)
class Paired:
    """The paired answer, and everything the stop conditions read."""

    species: int
    shared_years: tuple[int, int]
    median_difference: float
    difference_iqr: tuple[float, float]
    slope_iqr: tuple[float, float]
    ratio: float
    """Spread of paired differences over spread of slopes. The headline."""
    sign_disagreements: int
    """Species whose two networks disagree about the direction of movement."""


def _slopes(source_id: str, years: tuple[int, int]) -> pl.DataFrame:
    """One network's per-species slopes, inside a shared window.

    The window is applied to the rows before cells are formed, so the consistency rule is evaluated
    on the restricted years too -- a footprint computed over 1975-2024 and then trimmed would keep
    cells that are not consistent inside the window actually fitted.
    """
    frame = phase1k.load_counts(source_id).filter(
        pl.col("period_start").dt.year().is_between(years[0], years[1])
    )
    cells = range_metrics.to_cells(frame)
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
        years=pl.col("years"),
    )


def shared_window() -> tuple[int, int]:
    """The years both networks cover, read from the lake rather than from the registry."""
    spans = []
    for source_id in PAIR:
        years = (
            phase1k.load_counts(source_id)
            .select(year=pl.col("period_start").dt.year())
            .drop_nulls()
        )
        # Through numpy rather than polars' scalar accessor, whose return type is a union wide
        # enough that `int()` cannot be typed against it.
        column = years["year"].to_numpy()
        spans.append((int(column.min()), int(column.max())))
    return (max(s[0] for s in spans), min(s[1] for s in spans))


def paired() -> Paired | None:
    """The 173-species paired comparison, with composition removed by construction."""
    window = shared_window()
    if window[1] - window[0] + 1 < MIN_SHARED_YEARS:
        log.info("shared window %s is under %d years", window, MIN_SHARED_YEARS)
        return None

    first, second = (_slopes(source_id, window) for source_id in PAIR)
    if first.is_empty() or second.is_empty():
        log.info("a network has no qualifying species inside the shared window")
        return None

    both = first.join(second, on="taxon_key", how="inner", suffix="_other")
    if both.height < MIN_SHARED_SPECIES:
        log.info("only %d shared species, under the floor of %d", both.height, MIN_SHARED_SPECIES)
        return None

    difference = (both["slope"] - both["slope_other"]).to_numpy().astype(float)
    # The slopes themselves, pooled across both networks: the denominator of the ratio is how much
    # species differ from each other, which is what the method effect has to be compared against.
    slopes = np.concatenate(
        [both["slope"].to_numpy().astype(float), both["slope_other"].to_numpy().astype(float)]
    )

    def spread(values: np.ndarray) -> float:
        low, high = np.percentile(values, [25, 75])
        return float(high - low)

    slope_spread = spread(slopes)
    disagree = int(both.filter(pl.col("slope").sign() != pl.col("slope_other").sign()).height)
    return Paired(
        species=both.height,
        shared_years=window,
        median_difference=float(np.median(difference)),
        difference_iqr=phase1k.iqr(difference),
        slope_iqr=phase1k.iqr(slopes),
        ratio=spread(difference) / slope_spread if slope_spread else float("nan"),
        sign_disagreements=disagree,
    )


@dataclass(frozen=True, slots=True)
class Decomposition:
    """Why the two programmes disagree, split into the parts that can be told apart."""

    species: int
    observed_variance: float
    """Variance of the paired differences, as measured."""
    noise_variance: float
    """What the two fits' own standard errors predict that variance would be with no method effect
    at all: the mean of ``se_one ** 2 + se_two ** 2``."""
    noise_share: float
    """``noise_variance / observed_variance``. At or above 1 the disagreement is estimation
    error."""
    method_sd: float | None
    """Square root of whatever variance is left over. None when nothing is left."""
    species_sd: float | None
    """Between-species scatter with its own estimation error removed, so that the method effect is
    compared variance to variance rather than an sd against an interquartile range."""
    flips: int
    flips_explained: int
    """Sign disagreements where at least one of the two slopes cannot be told apart from zero."""
    slope_vs_stderr: float
    """Median |slope| over its own standard error. Below about two, a single species' trend is not
    individually distinguishable from no trend at all."""


# Two standard errors either side of an estimate: the width inside which it cannot be told apart
# from zero, and so the width inside which a sign flip needs no explaining.
STRADDLES_ZERO: Final = 1.96


def split_difference(
    slope_one: np.ndarray,
    slope_two: np.ndarray,
    se_one: np.ndarray,
    se_two: np.ndarray,
) -> Decomposition:
    """The decomposition's arithmetic, apart from the lake read so it can be checked.

    Two unbiased estimates of one quantity differ by their own errors **plus** any real difference
    in what they estimate, and those add in variance. So subtracting the first from the observed
    difference variance leaves the second. The null that makes this trustworthy is testable and
    tested: readings differing only by their stated errors must leave nothing over.
    """
    difference = slope_one - slope_two
    observed = float(np.var(difference, ddof=1))
    noise = float(np.mean(se_one**2 + se_two**2))
    left = observed - noise

    # The denominator gets the same treatment. Raw scatter across species also carries each fit's
    # error, so comparing a noise-corrected numerator against a raw denominator would flatter the
    # method effect -- the correction has to be applied to both or to neither.
    slopes = np.concatenate([slope_one, slope_two])
    errors = np.concatenate([se_one, se_two])
    species_left = float(np.var(slopes, ddof=1)) - float(np.mean(errors**2))

    # A sign flip is unremarkable where either estimate straddles zero: two draws from one near-zero
    # truth land either side of it as a matter of course, and no protocol difference is needed.
    flipped = np.sign(slope_one) != np.sign(slope_two)
    straddles = (np.abs(slope_one) < STRADDLES_ZERO * se_one) | (
        np.abs(slope_two) < STRADDLES_ZERO * se_two
    )
    ratios = np.concatenate([np.abs(slope_one) / se_one, np.abs(slope_two) / se_two])

    return Decomposition(
        species=int(slope_one.size),
        observed_variance=observed,
        noise_variance=noise,
        noise_share=noise / observed if observed else float("nan"),
        method_sd=float(np.sqrt(left)) if left > 0 else None,
        species_sd=float(np.sqrt(species_left)) if species_left > 0 else None,
        flips=int(flipped.sum()),
        flips_explained=int((flipped & straddles).sum()),
        slope_vs_stderr=float(np.median(ratios[np.isfinite(ratios)])),
    )


def decompose() -> Decomposition | None:
    """Split the paired disagreement into estimation error and anything else.

    Phase 1l measured two programmes disagreeing about one species more than species disagree with
    each other, and registered that its design could not say which of two readings held: the method
    matters more than the species, or each slope is too noisy to compare. This separates them, from
    the standard errors the fits were already computing and throwing away.

    If nothing is left over, the instruments do not disagree at all and what limits this project's
    comparisons is noise rather than protocol.
    """
    window = shared_window()
    first, second = (_slopes(source_id, window) for source_id in PAIR)
    if first.is_empty() or second.is_empty():
        return None
    both = first.join(second, on="taxon_key", how="inner", suffix="_other").drop_nulls(
        ["slope", "slope_other", "stderr", "stderr_other"]
    )
    if both.height < MIN_SHARED_SPECIES:
        log.info("only %d shared species carry both standard errors", both.height)
        return None

    return split_difference(
        both["slope"].to_numpy().astype(float),
        both["slope_other"].to_numpy().astype(float),
        both["stderr"].to_numpy().astype(float),
        both["stderr_other"].to_numpy().astype(float),
    )


def render() -> str:
    """The paired comparison, as text."""
    out = [
        "Phase 1l -- two programmes, one country's birds, paired by species",
        "=" * 78,
        "Pre-registered in docs/methods/phase1l-paired-protocols.md before any pairing.",
        "",
    ]
    result = paired()
    if result is None:
        out.append("A stop condition fired. Published as a coverage statement; no ratio claimed.")
        return "\n".join(out)

    out += [
        f"  shared window: {result.shared_years[0]}-{result.shared_years[1]}",
        f"  species measured by both: {result.species}",
        "",
        f"  paired median difference: {result.median_difference:+.4f} deg/decade "
        f"(unpaired gap was {UNPAIRED_GAP:+.4f})",
        f"  paired difference IQR: [{result.difference_iqr[0]:+.4f}, "
        f"{result.difference_iqr[1]:+.4f}]",
        f"  slope IQR across species: [{result.slope_iqr[0]:+.4f}, {result.slope_iqr[1]:+.4f}]",
        "",
        f"  RATIO (method spread / species spread): {result.ratio:.3f}",
        f"  sign disagreements: {result.sign_disagreements} of {result.species} "
        f"({100.0 * result.sign_disagreements / result.species:.1f}%)",
        "",
    ]

    split = decompose()
    if split is None:
        out.append("  decomposition unavailable: too few species carry both standard errors")
    else:
        left = (
            f"  method effect left over: sd {split.method_sd:.4f} deg/decade"
            if split.method_sd is not None
            else "  method effect left over: NONE -- noise accounts for all of it"
        )
        out += [
            "Why they disagree",
            f"  species carrying both standard errors: {split.species}",
            f"  observed variance of paired differences: {split.observed_variance:.5f}",
            f"  variance the two fits' own errors predict: {split.noise_variance:.5f}",
            f"  NOISE SHARE: {split.noise_share:.3f}",
            left,
            (
                f"  between-species scatter, same correction: sd {split.species_sd:.4f}"
                if split.species_sd is not None
                else "  between-species scatter, same correction: none left"
            ),
            (
                f"  METHOD vs SPECIES, both corrected: {split.method_sd / split.species_sd:.2f}"
                if split.method_sd is not None and split.species_sd
                else "  METHOD vs SPECIES: not comparable"
            ),
            f"  sign flips with a slope straddling zero: {split.flips_explained} of {split.flips}",
            f"  median |slope| / its own standard error: {split.slope_vs_stderr:.2f}",
            "",
        ]

    out.append("Predictions are graded in the method note, not here.")
    return "\n".join(out)
