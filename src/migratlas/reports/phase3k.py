"""Phase 3k -- is the marine signal a property of the species rather than of the sea?

Pre-registered in ``docs/methods/phase3k-species-not-seas.md`` on 2026-09-01, before any fit under
this design. Two unregistered diagnostics are why it exists, and the note says which of its
predictions are therefore checks rather than discoveries.

**A. The heterogeneity, with the drift in the design.** `seas-disagree` publishes Cochran's Q over
eighteen survey segments. A centroid is weighted by catch per unit effort, so where the hauls happen
moves it, and each survey's own mean haul latitude per year -- with no animal in it -- is a
covariate here, in the fit rather than regressed out afterwards. What survives is the between-survey
variation that is not the stations moving.

**B. The species, with a floor fixed in advance.** For taxa caught in at least five surveys, the
coherence of their latitude trends grouped by species against grouped by survey, both through
`phase1m._icc`, each with a survey-clustered bootstrap interval beside the naive one.

Both estimands are decompositions of one table rather than instruments, and nothing here is causal.
The calibration rung calls `phase3e` and `phase3b` themselves, so it cannot pass against a second
copy of the pipeline that produced the published numbers.
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final
from zlib import crc32

import numpy as np
import polars as pl
from scipy import stats

from migratlas.models.influence import Influence, leave_one_out
from migratlas.reports.phase1m import _icc
from migratlas.reports.phase3b import MIN_SEGMENT_YEARS, _trend_per_decade

if TYPE_CHECKING:
    from collections.abc import Sequence

    from migratlas.reports.phase3b import Unit

log = logging.getLogger(__name__)

SEED: Final = 1
DRAWS: Final = 1_000

MIN_SHARED_SURVEYS: Final = 5
"""Five rather than the diagnostic's three. Three surveys is where the question becomes askable at
all; five is where a species mean stops being two numbers and an outlier. Fixed in the registration
rather than against the count it admits."""

MIN_TAXA: Final = 120
"""Prediction 6's floor. Below it estimand B publishes as a coverage statement."""

COHERENCE_FLOOR: Final = 0.10
"""Phase 1m's registered floor, inherited so marine and terrestrial groupings are comparable."""

SPECIES_OVER_SURVEY: Final = 2.0
"""Prediction 5: the species coherence must be at least this many times the survey's."""

RESIDUAL_Q_CEILING: Final = 160.0
"""Prediction 3's bound on the residual heterogeneity, set above the diagnostic's post-hoc 130.9
as a bound rather than a target."""

# Calibration targets, quoted from `seas-disagree` as it publishes them: Q to one decimal, the
# warming slope and its half-width to three. Nothing above the calibration is read if any misses.
CALIBRATION_Q: Final = 235.7
CALIBRATION_SLOPE: Final = 0.039
CALIBRATION_CI: Final = 0.179
Q_TOLERANCE: Final = 0.05
SLOPE_TOLERANCE: Final = 5e-4

PARAMETERS: Final = 3
"""Intercept, drift, warming. The residual Q's chi-square bar loses one degree of freedom per
fitted parameter, where the plain Q's loses one for the pooled mean -- amendment B in the note."""

SPECIES: Final = "species"
SURVEY: Final = "survey"


@dataclass(frozen=True, slots=True)
class DriftUnit:
    """One of Phase 3e's units, with where its ships went added beside where its animals did."""

    survey: str
    latitude_trend: float
    latitude_ci: float
    warming_trend: float
    sampling_drift: float
    """Trend in the survey's mean haul latitude over the clipped years, °latitude per decade."""
    years: int


@dataclass(frozen=True, slots=True)
class DriftFit:
    """Estimand A: the registered cross-unit fit with the drift in the design."""

    units: int
    drift_slope: float
    drift_ci: float
    warming_slope: float
    warming_ci: float
    residual_q: float
    residual_bar: float
    residual_survives: bool
    """ADR 0016 extended to the residual Q: it still clears its recomputed bar with any one unit
    dropped."""
    drift_leverage: Influence | None
    warming_leverage: Influence | None

    @property
    def drift_positive(self) -> bool:
        """Prediction 2: positive, and the interval excludes zero."""
        return self.drift_slope - self.drift_ci > 0

    @property
    def warming_clears(self) -> bool:
        """Prediction 4 is that this stays False."""
        return abs(self.warming_slope) > self.warming_ci

    @property
    def residual_clears(self) -> bool:
        return self.residual_q > self.residual_bar

    @property
    def residual_margin(self) -> float:
        """How far the per-unit intervals can be understated before the residual Q stops clearing.

        `phase3b.Regression.q_robustness`'s arithmetic, on the residual: every weight falls by
        `k**2` when every interval is multiplied by `k`, and the bar does not move.
        """
        import math  # noqa: PLC0415 -- one caller, and the import documents the arithmetic

        if self.residual_bar <= 0:
            return float("nan")
        return math.sqrt(self.residual_q / self.residual_bar)


@dataclass(frozen=True, slots=True)
class Coherence:
    """One grouping's between-group share, with both intervals on the corrected value."""

    grouping: str
    raw: float
    corrected: float
    naive: tuple[float, float]
    """Percentile bootstrap over pairs, as if every pair were independent."""
    clustered: tuple[float, float]
    """Percentile bootstrap over surveys, each carrying every pair it holds."""

    @property
    def widening(self) -> float:
        naive = self.naive[1] - self.naive[0]
        return (self.clustered[1] - self.clustered[0]) / naive if naive > 0 else float("nan")


@dataclass(frozen=True, slots=True)
class Chance:
    """UNREGISTERED. What a between-group share is worth once the number of groups is counted.

    `_icc`'s between-group share is a one-way ANOVA's unadjusted R-squared, and an unadjusted
    R-squared with `k` groups over `n` rows has a null expectation near `(k - 1) / n`. A grouping
    into 171 species over 1,148 pairs therefore *starts* at about 0.15 with the labels shuffled,
    where a grouping into 23 surveys starts near 0.02 -- so the two coherences the registration
    compares are not on one scale, and neither is any coherence this project has set against
    Phase 1m's fixed floor of 0.10. Found by reading this phase's own output: the point estimates
    sat below their own bootstrap intervals, which is what duplicated rows do to a variance share.

    The permutation below shuffles the grouping's labels *within the other grouping* -- species
    labels within each survey, survey labels within each species -- so each survey keeps its own
    slopes and each species keeps its own, and only the alignment being tested is broken.
    """

    grouping: str
    observed: float
    closed_form: float
    """The `(k - 1) / n` expectation, scaled by the same noise correction as the observed value."""
    null_median: float
    null_95: float

    @property
    def excess(self) -> float:
        """Observed coherence over its own permutation median. The comparable quantity."""
        return self.observed - self.null_median

    @property
    def beats_chance(self) -> bool:
        return self.observed > self.null_95


@dataclass(frozen=True, slots=True)
class SpeciesFit:
    """Estimand B: does the species explain the spread, or the sea?"""

    pairs: int
    taxa: int
    surveys: int
    pooled_median: float
    """The panel's own median before the five-survey filter -- a check that this is `marine-null`'s
    table, printed beside the registered calibration and graded nowhere."""
    by_species: Coherence
    by_survey: Coherence
    species_chance: Chance | None = None
    survey_chance: Chance | None = None

    @property
    def ratio(self) -> float:
        survey = self.by_survey.corrected
        return self.by_species.corrected / survey if survey > 0 else float("inf")

    @property
    def enough_taxa(self) -> bool:
        return self.taxa >= MIN_TAXA

    @property
    def species_leads(self) -> bool:
        """Prediction 5, on the point estimates."""
        return bool(np.isfinite(self.ratio)) and self.ratio >= SPECIES_OVER_SURVEY

    @property
    def floor_holds_clustered(self) -> bool:
        """The stop condition's instrument: the clustered lower bound stays above the floor."""
        return self.by_species.clustered[0] >= COHERENCE_FLOOR


@dataclass(frozen=True, slots=True)
class Phase3k:
    """The whole phase: the calibration, then the two estimands."""

    calibration_q: float
    calibration_slope: float
    calibration_ci: float
    drift: DriftFit | None
    species: SpeciesFit | None

    @property
    def calibrated(self) -> bool:
        return (
            abs(self.calibration_q - CALIBRATION_Q) < Q_TOLERANCE
            and abs(self.calibration_slope - CALIBRATION_SLOPE) < SLOPE_TOLERANCE
            and abs(self.calibration_ci - CALIBRATION_CI) < SLOPE_TOLERANCE
        )


def _seed(name: str) -> int:
    """A bootstrap is a property of the quantity it is on, not of its position in a list."""
    return (crc32(name.encode()) ^ SEED) & 0x7FFF_FFFF


# --- Estimand A --------------------------------------------------------------------------


def drift_units(fitted: Sequence[Unit], cells: pl.DataFrame) -> list[DriftUnit]:
    """Phase 3e's units with each survey's own sampling drift over its own clipped segment.

    Amendment A: the covariate is trended over the same years as the response and over the
    distinct positions hauled in each year, not over catch rows. A mean over rows weights a haul by
    how many taxa it caught, and this is a question about where the ship went.
    """
    from migratlas.metrics import range as range_metrics  # noqa: PLC0415 -- report sibling

    out: list[DriftUnit] = []
    for unit in fitted:
        survey = cells.filter(pl.col("survey_unit") == unit.segment.survey)
        restricted, footprint = range_metrics.consistent_footprint(survey)
        if footprint.cells < range_metrics.MIN_CELLS:
            log.info("%s: footprint too small for a drift", unit.segment.survey)
            continue
        inside = restricted.filter(pl.col("year").is_between(unit.segment.start, unit.segment.end))
        positions = inside.select("year", "site_id", "site_latitude", "site_longitude").unique()
        per_year = (
            positions.group_by("year")
            .agg(latitude=pl.col("site_latitude").mean())
            .drop_nulls()
            .sort("year")
        )
        if per_year.height < MIN_SEGMENT_YEARS:
            log.info(
                "%s: %d years of haul positions, under the floor",
                unit.segment.survey,
                per_year.height,
            )
            continue
        drift, _ = _trend_per_decade(per_year["year"].to_numpy(), per_year["latitude"].to_numpy())
        out.append(
            DriftUnit(
                survey=unit.segment.survey,
                latitude_trend=unit.latitude_trend,
                latitude_ci=unit.latitude_ci,
                warming_trend=unit.temperature_trend,
                sampling_drift=drift,
                years=per_year.height,
            )
        )
    return out


def _weights(units: Sequence[DriftUnit]) -> np.ndarray:
    """Inverse-variance, exactly as `phase3b._solve` weights the published fit."""
    return np.array([1.0 / max((u.latitude_ci / 1.96) ** 2, 1e-6) for u in units])


def solve(units: Sequence[DriftUnit]) -> tuple[float, float, float, float, float, float]:
    """`latitude_trend ~ 1 + sampling_drift + warming_trend`, weighted, with the residual Q.

    Returns the drift slope and half-width, the warming slope and half-width, the residual Q and its
    chi-square bar. The residual Q is the weighted sum of squared residuals -- the same form as
    Cochran's Q with the fitted design in place of the pooled mean -- against a bar with one degree
    of freedom fewer per fitted parameter.
    """
    y = np.array([u.latitude_trend for u in units])
    weights = _weights(units)
    design = np.column_stack(
        [
            np.ones(len(y)),
            np.array([u.sampling_drift for u in units]),
            np.array([u.warming_trend for u in units]),
        ]
    )
    root = np.sqrt(weights)
    solution, *_ = np.linalg.lstsq(design * root[:, None], y * root, rcond=None)
    residuals = y - design @ solution
    dof = len(y) - design.shape[1]
    residual_q = float(np.sum(weights * residuals**2))
    sigma2 = residual_q / dof
    covariance = sigma2 * np.linalg.pinv(design.T @ (design * weights[:, None]))
    errors = np.sqrt(np.diag(covariance))
    return (
        float(solution[1]),
        float(1.96 * errors[1]),
        float(solution[2]),
        float(1.96 * errors[2]),
        residual_q,
        float(stats.chi2.ppf(0.95, dof)),
    )


def fit_drift(units: list[DriftUnit]) -> DriftFit | None:
    """Estimand A end to end, with ADR 0016 on both coefficients and on the residual Q."""
    if len(units) <= PARAMETERS + 1:
        log.warning("phase3k: %d units cannot carry a three-parameter fit", len(units))
        return None
    drift_slope, drift_ci, warming_slope, warming_ci, residual_q, residual_bar = solve(units)

    residual_survives = True
    for index in range(len(units)):
        rest = [unit for position, unit in enumerate(units) if position != index]
        one_q, one_bar = solve(rest)[4:]
        if one_q <= one_bar:
            log.info(
                "dropping %s takes the residual Q to %.1f against %.1f",
                units[index].survey,
                one_q,
                one_bar,
            )
            residual_survives = False

    return DriftFit(
        units=len(units),
        drift_slope=drift_slope,
        drift_ci=drift_ci,
        warming_slope=warming_slope,
        warming_ci=warming_ci,
        residual_q=residual_q,
        residual_bar=residual_bar,
        residual_survives=residual_survives,
        drift_leverage=leave_one_out(
            units, lambda subset: solve(subset)[:2], name=lambda u: u.survey
        ),
        warming_leverage=leave_one_out(
            units, lambda subset: solve(subset)[2:4], name=lambda u: u.survey
        ),
    )


# --- Estimand B --------------------------------------------------------------------------


def shared_panel(pooled: pl.DataFrame) -> pl.DataFrame:
    """`marine-null`'s pair table, restricted to taxa caught in at least five surveys.

    Keyed on `taxon_key` rather than on the label, because 95 keys carry two or more verbatim
    names across sources (TASKS #3) and a species split by spelling would look like two species that
    disagree.
    """
    if pooled.is_empty():
        return pooled
    counts = pooled.group_by("taxon_key").agg(surveys=pl.col("survey_unit").n_unique())
    shared = counts.filter(pl.col("surveys") >= MIN_SHARED_SURVEYS)["taxon_key"]
    return pooled.filter(pl.col("taxon_key").is_in(shared.implode())).select(
        slope=pl.col("per_decade").cast(pl.Float64),
        stderr=pl.col("stderr").cast(pl.Float64),
        species=pl.col("taxon_key").cast(pl.String),
        survey=pl.col("survey_unit").cast(pl.String),
    )


def bootstrap(
    table: pl.DataFrame, grouping: str, *, clustered: bool, draws: int = DRAWS
) -> tuple[float, float]:
    """A percentile interval on the corrected coherence, over pairs or over surveys.

    Every pair inside one survey shares that survey's gear, footprint and water, so a resample over
    pairs admits far less dependence than there is. Phase 3j measured the price at three times on
    this record; here it is measured again rather than assumed, on the quantity that decides the
    phase.
    """
    rng = np.random.default_rng(_seed(f"{grouping}:{'clustered' if clustered else 'naive'}"))
    keys = table[SURVEY].to_numpy()
    blocks = [np.flatnonzero(keys == key) for key in np.unique(keys)]
    values = np.empty(draws, dtype=float)
    for draw in range(draws):
        if clustered:
            picked = rng.integers(0, len(blocks), size=len(blocks))
            rows = np.concatenate([blocks[index] for index in picked])
        else:
            rows = rng.integers(0, table.height, size=table.height)
        values[draw] = _icc(table[rows].rename({grouping: "group"}))[1]
    low, high = np.nanpercentile(values, [2.5, 97.5])
    return (float(low), float(high))


def coherence(table: pl.DataFrame, grouping: str, *, draws: int = DRAWS) -> Coherence:
    """One grouping: the point estimates and both intervals."""
    raw, corrected = _icc(table.rename({grouping: "group"}))
    return Coherence(
        grouping=grouping,
        raw=raw,
        corrected=corrected,
        naive=bootstrap(table, grouping, clustered=False, draws=draws),
        clustered=bootstrap(table, grouping, clustered=True, draws=draws),
    )


def chance_level(table: pl.DataFrame, grouping: str, *, draws: int = DRAWS) -> Chance:
    """UNREGISTERED: the coherence a grouping reaches with its labels shuffled.

    Shuffled within the *other* grouping, so the structure not under test is preserved. Cannot be a
    graded prediction -- §3 asked for no null on the coherence, and this was written after the
    bootstrap intervals were seen sitting above their own point estimates.
    """
    other = SURVEY if grouping == SPECIES else SPECIES
    rng = np.random.default_rng(_seed(f"{grouping}:chance"))
    labels = table[grouping].to_numpy().copy()
    keys = table[other].to_numpy()
    blocks = [np.flatnonzero(keys == key) for key in np.unique(keys)]
    values = np.empty(draws, dtype=float)
    for draw in range(draws):
        shuffled = labels.copy()
        for block in blocks:
            shuffled[block] = rng.permutation(labels[block])
        values[draw] = _icc(table.with_columns(group=pl.Series(shuffled)))[1]

    raw, corrected = _icc(table.rename({grouping: "group"}))
    scale = corrected / raw if raw > 0 and np.isfinite(corrected) else float("nan")
    groups = table[grouping].n_unique()
    # A panel whose spread is all estimation error has no corrected variance to apportion, and
    # `_icc` says so with NaN on every draw. Read as "no chance level" rather than warned about.
    finite = values[np.isfinite(values)]
    return Chance(
        grouping=grouping,
        observed=corrected,
        closed_form=float((groups - 1) / table.height * scale),
        null_median=float(np.median(finite)) if finite.size else float("nan"),
        null_95=float(np.percentile(finite, 95)) if finite.size else float("nan"),
    )


def fit_species(pooled: pl.DataFrame, *, draws: int = DRAWS) -> SpeciesFit | None:
    """Estimand B end to end, with the unregistered chance level beside each coherence."""
    table = shared_panel(pooled)
    if table.is_empty():
        log.warning("phase3k: no taxon is caught in %d surveys", MIN_SHARED_SURVEYS)
        return None
    return SpeciesFit(
        pairs=table.height,
        taxa=table[SPECIES].n_unique(),
        surveys=table[SURVEY].n_unique(),
        pooled_median=float(np.median(pooled["per_decade"].to_numpy().astype(float))),
        by_species=coherence(table, SPECIES, draws=draws),
        by_survey=coherence(table, SURVEY, draws=draws),
        species_chance=chance_level(table, SPECIES, draws=draws),
        survey_chance=chance_level(table, SURVEY, draws=draws),
    )


# --- The phase ---------------------------------------------------------------------------


def collect() -> Phase3k | None:
    """Calibrate against the published fit, then both estimands on the same units and pairs."""
    from migratlas.metrics import range as range_metrics  # noqa: PLC0415 -- heavy
    from migratlas.reports import phase1b, phase3b, phase3e  # noqa: PLC0415 -- heavy

    fitted, _, calibration = phase3e.units_3e()
    if not calibration.passes or len(fitted) < phase3b.MIN_UNITS:
        log.warning("phase3k: Phase 3e's own gate did not pass; nothing to calibrate to")
        return None
    published = phase3b.regression(fitted)

    cells = range_metrics.to_cells(phase1b.survey_unit(phase1b.load()))
    drift = fit_drift(drift_units(fitted, cells))
    _, pooled, _ = phase1b.analyse(cells)
    species = fit_species(pooled)
    return Phase3k(
        calibration_q=published.q_statistic,
        calibration_slope=published.temp_slope,
        calibration_ci=published.temp_ci,
        drift=drift,
        species=species,
    )


def _leverage_line(label: str, influence: Influence | None) -> str:
    if influence is None:
        return f"  ADR 0016 on {label}: fewer than three units, nothing to drop"
    worst = influence.worst()
    named = f"; furthest is {worst[0]} at {worst[1]:+.3f} ± {worst[2]:.3f}" if worst else ""
    return (
        f"  ADR 0016 on {label}: clears zero {'yes' if influence.clears_at_full else 'no'}, "
        f"publishable {'yes' if influence.publishable else 'NO'}{named}"
    )


def render() -> str:
    """The calibration, both estimands, and one verdict line. Predictions are graded in the note."""
    out = [
        "Phase 3k -- is the marine signal a property of the species rather than of the sea?",
        "=" * 78,
        "Pre-registered in docs/methods/phase3k-species-not-seas.md before any fit under this",
        "design. Estimand A puts each survey's own sampling drift in the fit; estimand B asks",
        "whether the species or the survey explains the spread, at a five-survey floor.",
        "",
    ]
    read = collect()
    if read is None:
        return "\n".join([*out, "VERDICT: Phase 3e's gate did not pass; nothing to calibrate to."])

    out += [
        f"Calibration -- Q {read.calibration_q:.1f} against {CALIBRATION_Q}, warming "
        f"{read.calibration_slope:+.3f} ± {read.calibration_ci:.3f} against "
        f"{CALIBRATION_SLOPE:+.3f} ± {CALIBRATION_CI:.3f}: {'PASS' if read.calibrated else 'FAIL'}",
        "",
    ]
    if not read.calibrated:
        return "\n".join([*out, "VERDICT: calibration FAILED -- nothing above it is interpreted."])

    if read.drift is None:
        out += ["Estimand A -- too few units carried a drift; not fitted.", ""]
    else:
        fit = read.drift
        out += [
            f"Estimand A -- latitude ~ 1 + sampling_drift + warming over {fit.units} units",
            f"  sampling drift {fit.drift_slope:+.3f} ± {fit.drift_ci:.3f} ° animal per ° ship"
            f" -- {'positive and clear of zero' if fit.drift_positive else 'NOT clear of zero'}",
            f"  warming {fit.warming_slope:+.3f} ± {fit.warming_ci:.3f} °lat per °C"
            f" -- {'CLEARS zero' if fit.warming_clears else 'null, as registered'}",
            f"  residual Q {fit.residual_q:.1f} against a bar of {fit.residual_bar:.1f}"
            f" ({fit.units} - {PARAMETERS} degrees of freedom) -- "
            f"{'clears' if fit.residual_clears else 'does NOT clear'}; "
            f"{'below' if fit.residual_q < RESIDUAL_Q_CEILING else 'ABOVE'} the "
            f"{RESIDUAL_Q_CEILING:.0f} bound",
            f"  residual Q survives losing any unit: {'yes' if fit.residual_survives else 'NO'}; "
            f"weight margin {fit.residual_margin:.2f}x",
            _leverage_line("the drift slope", fit.drift_leverage),
            _leverage_line("the warming slope", fit.warming_leverage),
            "",
        ]

    if read.species is None:
        out += ["Estimand B -- no taxon in five surveys; coverage statement.", ""]
    else:
        sp = read.species
        out += [
            f"Estimand B -- {sp.pairs:,} pairs over {sp.taxa} taxa in {sp.surveys} surveys "
            f"(floor {MIN_TAXA} taxa: {'met' if sp.enough_taxa else 'NOT met'}); "
            f"panel median {sp.pooled_median:+.4f} before the filter",
        ]
        for part in (sp.by_species, sp.by_survey):
            out.append(
                f"  by {part.grouping}: {part.corrected:.3f} corrected ({part.raw:.3f} raw); "
                f"naive [{part.naive[0]:.3f}, {part.naive[1]:.3f}], "
                f"survey-clustered [{part.clustered[0]:.3f}, {part.clustered[1]:.3f}] "
                f"({part.widening:.1f}x)"
            )
        out += [
            f"  species over survey {sp.ratio:.2f}x against {SPECIES_OVER_SURVEY:.0f}x -- "
            f"{'species leads' if sp.species_leads else 'does NOT lead by two'}",
            f"  species coherence clears {COHERENCE_FLOOR:.2f} under the clustered interval: "
            f"{'yes' if sp.floor_holds_clustered else 'NO'}",
        ]
        for chance in (sp.species_chance, sp.survey_chance):
            if chance is None:
                continue
            out.append(
                f"  UNREGISTERED chance level, by {chance.grouping}: labels shuffled give "
                f"{chance.null_median:.3f} (95th {chance.null_95:.3f}; closed form "
                f"{chance.closed_form:.3f}); observed {chance.observed:.3f} is "
                f"{chance.excess:+.3f} over chance and "
                f"{'BEATS' if chance.beats_chance else 'does NOT beat'} its 95th percentile"
            )
        out.append("")

    verdict = []
    if read.drift is not None:
        verdict.append(
            f"warming {'CLEARS' if read.drift.warming_clears else 'null'} with drift in the design"
        )
        verdict.append(
            f"residual Q {read.drift.residual_q:.1f} "
            f"{'clears' if read.drift.residual_clears else 'FAILS'}"
        )
    if read.species is not None:
        verdict.append(
            f"species {read.species.by_species.corrected:.3f} vs survey "
            f"{read.species.by_survey.corrected:.3f}, clustered floor "
            f"{'holds' if read.species.floor_holds_clustered else 'FAILS'}"
        )
    return "\n".join([*out, "VERDICT: " + "; ".join(verdict)])
