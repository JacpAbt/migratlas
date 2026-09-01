"""Phase 3j -- is the marine null a mixture? Clusters by thermal exposure, not by taxon or ocean.

Pre-registered in ``docs/methods/phase3j-thermal-clusters.md`` before any cluster was formed.

`marine-null` publishes a median of -0.011 deg latitude per decade over ~2,240 species-survey pairs
with an interquartile range spanning zero, and `seas-disagree` has since established that the units
behind it disagree emphatically while the thermometer does not sort them. A warming that moved a
third of the pairs and left the rest alone produces exactly the number the ledger publishes, and
nothing had tested that.

**The primary quantity is coherence, not signal**, and Phase 1m is why: averaging seventeen species
raises the signal by roughly the square root of seventeen whether or not they belong together, and
its stop condition fired on exactly that. So the floor is Phase 1m's own 0.10, `_icc` is Phase 1m's
own function, and one axis clearing a null out of three with coherence under the floor is
pre-committed as not a finding.

**No axis is a property of the response.** Grouping on how much something moved and then measuring
how much the groups moved is the circularity Phase 1m named and Phase 3i refused.
"""

import logging
from dataclasses import dataclass
from typing import Final

import numpy as np
import polars as pl

from migratlas.metrics import range as range_metrics
from migratlas.metrics import thermal
from migratlas.models.influence import Influence, leave_one_out
from migratlas.reports.phase1m import _icc

log = logging.getLogger(__name__)

SEED: Final = 1
PERMUTATIONS: Final = 1_000

TERCILES: Final = 3
"""Three, not ten. The survey-level axes have about ten surveys each at three; ten groups would
leave three, and the count is fixed in the registration rather than against a result."""

COHERENCE_FLOOR: Final = 0.10
"""Phase 1m's registered floor, inherited so the two realms are comparable rather than each judged
against a bar chosen for it."""

MARINE_NULL_MEDIAN: Final = -0.011
MARINE_TOLERANCE: Final = 5e-4
"""Three significant figures, which is what the calibration promised."""

CLUSTERED_WIDENING: Final = 2.0
"""Prediction 5's bar: a survey-clustered interval should be at least this many times as wide as
a naive one over pairs."""

THERMAL: Final = "thermal position"
WARMING: Final = "warming rate"
DEPTH: Final = "haul depth"

AXES: Final[tuple[tuple[str, bool], ...]] = (
    # (name, varies within a survey). The third field of the design that matters: only the thermal
    # axis distinguishes pairs inside one trawl, so only it is free of "which survey contributed
    # most pairs", and only its null shuffles within survey.
    (THERMAL, True),
    (WARMING, False),
    (DEPTH, False),
)

TERCILE_NAMES: Final[tuple[str, ...]] = ("low", "mid", "high")


@dataclass(frozen=True, slots=True)
class Tercile:
    """One third of one axis."""

    name: str
    pairs: int
    surveys: int
    median: float


@dataclass(frozen=True, slots=True)
class AxisResult:
    """One axis: whether its terciles differ, and whether the grouping means anything."""

    axis: str
    within_survey: bool
    pairs: int
    surveys: int
    terciles: tuple[Tercile, ...]
    spread: float
    """High tercile's median minus the low tercile's, in deg latitude per decade."""
    null_95: float
    spread_p: float
    coherence_raw: float
    coherence_corrected: float
    naive_width: float
    clustered_width: float
    leverage: Influence | None

    @property
    def beats_null(self) -> bool:
        return abs(self.spread) > self.null_95

    @property
    def clears_floor(self) -> bool:
        return bool(np.isfinite(self.coherence_corrected)) and (
            self.coherence_corrected > COHERENCE_FLOOR
        )

    @property
    def widening(self) -> float:
        return self.clustered_width / self.naive_width if self.naive_width else float("nan")


@dataclass(frozen=True, slots=True)
class Phase3j:
    """The whole phase: the calibration and one result per axis."""

    calibration: float
    axes: tuple[AxisResult, ...]

    @property
    def calibrated(self) -> bool:
        return abs(self.calibration - MARINE_NULL_MEDIAN) < MARINE_TOLERANCE

    @property
    def best(self) -> AxisResult | None:
        """The most coherent axis, which is the only one prediction 4 is about."""
        usable = [axis for axis in self.axes if np.isfinite(axis.coherence_corrected)]
        return max(usable, key=lambda axis: axis.coherence_corrected) if usable else None


def _axis_seed(name: str) -> int:
    """A null is a property of its axis, not of its position in a list. Phase 3f's correction."""
    from zlib import crc32  # noqa: PLC0415 -- one caller, and the import documents the mixing

    return (crc32(name.encode()) ^ SEED) & 0x7FFF_FFFF


def _terciles(values: np.ndarray) -> np.ndarray:
    """Tercile index per value, by rank so unequal spacing cannot empty a group."""
    order = values.argsort().argsort().astype(float)
    index = np.clip((order / max(values.size, 1) * TERCILES).astype(int), 0, TERCILES - 1)
    return np.asarray(index, dtype=int)


def panel() -> pl.DataFrame:
    """Every species-survey pair, its latitude trend, and its three axis values.

    The response comes from `phase1b.analyse` itself -- the function `marine-null` publishes
    through -- so the calibration cannot pass against a second copy of the pipeline. The axis values
    are recomputed per survey on the same consistent footprint, because the footprint rule is
    deterministic and re-deriving it is cheaper than threading the restricted frames back out.

    Amendment A, written before any cluster existed: the warming rate is trended over **each
    survey's own window** rather than read from Phase 3e. Phase 3e's units are single-gear segments
    clipped to the satellite era, and pairing a driver measured over that window with a response
    measured over the whole record would compare two different stretches of time. The registration
    named Phase 3e as the source; using it verbatim would have been the error it warns against.
    """
    from migratlas.reports import phase1b, phase2a_thermal, phase3e  # noqa: PLC0415 -- heavy

    # Amendment B: the cells come through `phase2a_thermal.load`, which is the loader that attaches
    # the per-haul temperature. The first attempt built them from `phase1b` and every survey dropped
    # out, because `thermal.occupied` returns nothing when the temperature column is absent --
    # an empty panel that looked like a coverage problem and was a join. The registration named
    # `phase2a_thermal` as axis 1's source; going through its loader is what that means.
    #
    # The response is unaffected and the calibration is what says so: the join is a left join on the
    # haul, so no row is added or dropped, and `analyse` never touches temperature.
    cells = range_metrics.to_cells(phase2a_thermal.load())
    _, pooled, _ = phase1b.analyse(cells)
    if pooled.is_empty():
        return pl.DataFrame()

    oisst = phase3e._oisst_by_unit_year()  # noqa: SLF001 -- the published footprint-mean reader

    # Per-survey axis values, and per-pair thermal positions where a thermometer exists. Collected
    # first so that every pair `analyse` produced can be emitted below, with a missing axis value
    # rather than a missing row: the calibration is over *every* pair, and dropping the surveys that
    # never recorded their water would silently calibrate against a subset. The first run did
    # exactly that and came in at -0.0136 against -0.011, which is the calibration doing its job.
    survey_axes: dict[str, tuple[float, float]] = {}
    position: dict[tuple[str, str], float] = {}
    for (raw_unit,), survey in cells.group_by(["survey_unit"], maintain_order=True):
        unit = str(raw_unit)
        restricted, footprint = range_metrics.consistent_footprint(survey)
        if footprint.cells < range_metrics.MIN_CELLS:
            continue
        years = restricted["year"].to_numpy()
        start_year, end_year = int(years.min()), int(years.max())

        water = oisst.filter(
            pl.col("survey") == unit, pl.col("year").is_between(start_year, end_year)
        ).sort("year")
        warming = (
            float(np.polyfit(water["year"].to_numpy(), water["sst"].to_numpy(), 1)[0] * 10.0)
            if water.height >= range_metrics.MIN_CELLS
            else float("nan")
        )
        depths = restricted["site_depth_m"].drop_nulls().to_numpy()
        survey_axes[unit] = (
            warming,
            float(np.median(depths)) if depths.size else float("nan"),
        )

        occupied = thermal.occupied(restricted)
        if occupied.is_empty():
            log.info("%s: no bottom temperature on any caught haul, so no thermal position", unit)
            continue
        per_taxon = occupied.group_by("taxon_label").agg(pl.col("occupied").mean())
        levels = per_taxon["occupied"].to_numpy().astype(float)
        # A percentile *within the survey*: a Baltic species and a Gulf species are each compared
        # against their own water, which is the whole reason this axis is not a proxy for geography.
        ranks = levels.argsort().argsort() / max(levels.size - 1, 1)
        for label, rank in zip(per_taxon["taxon_label"].to_list(), ranks.tolist(), strict=True):
            position[(unit, str(label))] = float(rank)

    rows: list[dict[str, object]] = []
    for row in pooled.iter_rows(named=True):
        unit = str(row["survey_unit"])
        if unit not in survey_axes:
            continue
        warming, depth = survey_axes[unit]
        label = str(row["taxon_label"])
        rows.append(
            {
                "survey_unit": unit,
                "taxon_label": label,
                "slope": float(row["per_decade"]),
                "stderr": float(row["stderr"]),
                THERMAL: position.get((unit, label), float("nan")),
                WARMING: warming,
                DEPTH: depth,
            }
        )
    return pl.DataFrame(rows)


def _assign(frame: pl.DataFrame, axis: str, *, within_survey: bool) -> pl.DataFrame:
    """Tercile per pair: within each survey for the thermal axis, across surveys for the others."""
    usable = frame.filter(pl.col(axis).is_not_nan(), pl.col(axis).is_not_null())
    if usable.is_empty():
        return usable
    if within_survey:
        out = []
        for (_,), survey in usable.group_by(["survey_unit"], maintain_order=True):
            index = _terciles(survey[axis].to_numpy().astype(float))
            out.append(survey.with_columns(group=pl.Series([TERCILE_NAMES[i] for i in index])))
        return pl.concat(out)
    # One value per survey, so the terciles are of surveys and a survey enters exactly one.
    per_survey = usable.group_by("survey_unit").agg(pl.col(axis).first())
    index = _terciles(per_survey[axis].to_numpy().astype(float))
    mapping = dict(
        zip(per_survey["survey_unit"].to_list(), [TERCILE_NAMES[i] for i in index], strict=True)
    )
    return usable.with_columns(
        group=pl.col("survey_unit").replace_strict(mapping, default=None, return_dtype=pl.String)
    ).drop_nulls("group")


def _spread(table: pl.DataFrame) -> float:
    """High tercile's median minus the low one's. Empty either side and there is no spread."""
    medians = {
        str(name): float(np.median(part["slope"].to_numpy().astype(float)))
        for (name,), part in table.group_by(["group"])
    }
    if TERCILE_NAMES[0] not in medians or TERCILE_NAMES[-1] not in medians:
        return float("nan")
    return medians[TERCILE_NAMES[-1]] - medians[TERCILE_NAMES[0]]


def _null_spread(table: pl.DataFrame, axis: str, *, within_survey: bool) -> float:
    """The 95th percentile of |spread| with the cluster labels shuffled.

    Shuffled *within survey* for the thermal axis and *across surveys* for the other two, which is
    what keeps each null a statement about the axis rather than about the panel: reassigning a
    survey-level value inside one survey would leave every pair where it was.
    """
    rng = np.random.default_rng(_axis_seed(axis))
    draws = np.empty(PERMUTATIONS, dtype=float)
    if within_survey:
        keys = table["survey_unit"].to_numpy()
        blocks = [np.flatnonzero(keys == key) for key in np.unique(keys)]
    else:
        keys = table["survey_unit"].to_numpy()
        surveys = np.unique(keys)
        blocks = [np.flatnonzero(keys == key) for key in surveys]
    labels = table["group"].to_numpy()
    for draw in range(PERMUTATIONS):
        shuffled = labels.copy()
        if within_survey:
            for block in blocks:
                shuffled[block] = rng.permutation(labels[block])
        else:
            # One label per survey, permuted across surveys, then written back to every pair.
            per_survey = np.array([labels[block][0] for block in blocks])
            drawn = rng.permutation(per_survey)
            for block, value in zip(blocks, drawn, strict=True):
                shuffled[block] = value
        draws[draw] = abs(_spread(table.with_columns(group=pl.Series(shuffled))))
    return float(np.nanpercentile(draws, 95))


def _interval(table: pl.DataFrame, *, clustered: bool, axis: str) -> float:
    """Width of a percentile bootstrap interval on the spread, over pairs or over surveys.

    Prediction 5's instrument. Every pair inside one survey shares that survey's water, gear and
    footprint, so a resample over pairs admits far less dependence than there is -- and the price of
    ignoring that is what this measures rather than assumes.
    """
    rng = np.random.default_rng(_axis_seed(axis) ^ int(clustered))
    keys = table["survey_unit"].to_numpy()
    surveys = np.unique(keys)
    blocks = [np.flatnonzero(keys == key) for key in surveys]
    draws = np.empty(PERMUTATIONS, dtype=float)
    for draw in range(PERMUTATIONS):
        if clustered:
            picked = rng.integers(0, len(blocks), size=len(blocks))
            rows = np.concatenate([blocks[index] for index in picked])
        else:
            rows = rng.integers(0, table.height, size=table.height)
        draws[draw] = _spread(table[rows])
    low, high = np.nanpercentile(draws, [2.5, 97.5])
    return float(high - low)


def _axis(frame: pl.DataFrame, axis: str, *, within_survey: bool) -> AxisResult | None:
    """One axis, end to end."""
    table = _assign(frame, axis, within_survey=within_survey)
    if table.is_empty() or table["group"].n_unique() < TERCILES:
        log.info("%s: fewer than three terciles carried pairs", axis)
        return None

    spread = _spread(table)
    null_95 = _null_spread(table, axis, within_survey=within_survey)
    raw, corrected = _icc(table)

    terciles = tuple(
        Tercile(
            name=name,
            pairs=part.height,
            surveys=part["survey_unit"].n_unique(),
            median=float(np.median(part["slope"].to_numpy().astype(float))),
        )
        for name in TERCILE_NAMES
        if (part := table.filter(pl.col("group") == name)).height
    )

    # ADR 0016 on the quantity that carries the verdict. A spread that does not survive losing one
    # survey is a spread about that survey, and the survey-level axes are squarely inside the rule's
    # floor at about thirty units.
    def refit(subset: list[str]) -> tuple[float, float]:
        kept = table.filter(pl.col("survey_unit").is_in(subset))
        if kept.is_empty() or kept["group"].n_unique() < TERCILES:
            return (float("nan"), float("inf"))
        return (
            _spread(kept),
            _null_spread(kept, axis, within_survey=within_survey),
        )

    surveys = sorted(table["survey_unit"].unique().to_list())
    leverage = leave_one_out(surveys, lambda subset: refit(list(subset)), name=str)

    return AxisResult(
        axis=axis,
        within_survey=within_survey,
        pairs=table.height,
        surveys=len(surveys),
        terciles=terciles,
        spread=spread,
        null_95=null_95,
        spread_p=float("nan"),
        coherence_raw=raw,
        coherence_corrected=corrected,
        naive_width=_interval(table, clustered=False, axis=axis),
        clustered_width=_interval(table, clustered=True, axis=axis),
        leverage=leverage,
    )


def collect() -> Phase3j | None:
    """The calibration and all three axes."""
    frame = panel()
    if frame.is_empty():
        log.warning("phase3j: no pair carried an axis value")
        return None
    calibration = float(np.median(frame["slope"].to_numpy().astype(float)))
    axes = tuple(
        result
        for axis, within in AXES
        if (result := _axis(frame, axis, within_survey=within)) is not None
    )
    return Phase3j(calibration=calibration, axes=axes)


def render() -> str:
    """Every registered prediction graded, the calibration first, one verdict line at the end."""
    out = [
        "Phase 3j -- is the marine null a mixture?",
        "=" * 78,
        "Pre-registered in docs/methods/phase3j-thermal-clusters.md before any cluster was formed.",
        "The primary quantity is coherence, not signal: averaging raises a signal whether or not a",
        "group belongs together, which is what fired Phase 1m's stop condition.",
        "",
    ]
    read = collect()
    if read is None:
        return "\n".join([*out, "VERDICT: no panel -- nothing to read."])

    out += [
        f"Calibration -- pooled median {read.calibration:+.4f} against marine-null's "
        f"{MARINE_NULL_MEDIAN:+.3f}: {'PASS' if read.calibrated else 'FAIL'}",
        "",
    ]
    if not read.calibrated:
        return "\n".join([*out, "VERDICT: calibration FAILED -- no axis is interpreted."])

    for axis in read.axes:
        scale = "within survey" if axis.within_survey else "across surveys"
        out += [
            f"{axis.axis} ({scale}) -- {axis.pairs:,} pairs over {axis.surveys} surveys",
            "  "
            + "  ".join(
                f"{t.name} {t.median:+.4f} ({t.pairs:,}p/{t.surveys}s)" for t in axis.terciles
            ),
            f"  spread {axis.spread:+.4f} against a null bar of {axis.null_95:.4f} -- "
            f"{'BEATS' if axis.beats_null else 'inside'} its null",
            f"  coherence {axis.coherence_corrected:.3f} corrected ({axis.coherence_raw:.3f} raw) "
            f"against a floor of {COHERENCE_FLOOR:.2f} -- "
            f"{'clears' if axis.clears_floor else 'BELOW'}",
            f"  interval width: {axis.naive_width:.4f} over pairs, {axis.clustered_width:.4f} over "
            f"surveys ({axis.widening:.1f}x)",
        ]
        if axis.leverage is not None:
            out.append(
                f"  ADR 0016: spread survives dropping any one survey: "
                f"{'yes' if axis.leverage.publishable else 'NO'}"
            )
        out.append("")

    best = read.best
    beat = [axis for axis in read.axes if axis.beats_null]
    out += ["Predictions are graded in the method note, not here."]
    if best is None:
        return "\n".join([*out, "VERDICT: no axis carried a coherence -- nothing to interpret."])
    verdict = (
        f"{len(beat)} of {len(read.axes)} axes beat their null; most coherent is {best.axis} at "
        f"{best.coherence_corrected:.3f}, which "
        f"{'clears' if best.clears_floor else 'does NOT clear'} the 0.10 floor"
    )
    return "\n".join([*out, f"VERDICT: {verdict}"])
