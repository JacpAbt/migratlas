"""Phase 2e -- is where an animal moved the population's, rather than the sea's or the air's?

Pre-registered in ``docs/methods/phase2e-population-shifts.md`` before any abundance trend was
fitted. Every driver tried against *where* in this project has been a property of the environment;
this is the first that is a property of the population. A species whose numbers rise occupies new
cells and its centroid moves toward them; one whose numbers fall retreats toward wherever it
persists. Neither needs a degree of warming.

**Three quantities per unit**, the species in its survey, all on the consistent footprint the
latitude trend was fitted on: `L`, the published latitude trend; `N`, the slope per decade of the
log of the yearly index -- summed catch per unit effort over the year's sampling events, divided by
the number of events; `E`, the slope of the log of the number of consistent cells the species was
caught in.

**The instruments are borrowed, not rebuilt**: Phase 3j's terciles, spreads and within-survey nulls
with a population axis in place of a thermal one; Phase 1m's coherence; Phase 3k's species-against-
survey coherence with its permutation chance level. The one new thing is the control the
registration fixed with the test -- a rare species has a noisy `N` and a noisy `L`, and the
magnitude of a noisy estimate is inflated, so the abundance spread counts only if it exceeds the
same spread cut on the latitude trend's own precision.
"""

import logging
from dataclasses import dataclass
from typing import Final
from zlib import crc32

import numpy as np
import polars as pl
from scipy import stats

from migratlas.metrics import range as range_metrics
from migratlas.reports import phase3j, phase3k
from migratlas.reports.phase1m import _icc

log = logging.getLogger(__name__)

SEED: Final = 1
DRAWS: Final = 1_000

MARINE_MIN_YEARS: Final = 15
"""`marine-null`'s own floor on a latitude trend, applied to the index."""
BIRD_MIN_YEARS: Final = 20
"""Phase 1k's floor on a bird species' latitude trend, applied to the index."""
MIN_UNITS_PER_SURVEY: Final = 10
"""Below this a survey's within-survey correlation is not read."""

MARINE_NULL_MEDIAN: Final = -0.011
MARINE_TOLERANCE: Final = 5e-4

THERMAL_BEST: Final = 0.035
"""Phase 3j's most coherent thermal axis, depth. Prediction 6's bar."""

MARINE: Final = "fishglob"
BIRD_NETWORKS: Final[tuple[str, ...]] = ("bbs", "sbs_point_counts", "sbs_fixed_routes")

ABUNDANCE: Final = "abundance"
"""`N`, signed: the log-index slope per decade."""
SIZE: Final = "abundance_size"
"""`|N|`."""
PRECISION: Final = "precision"
"""The latitude trend's own standard error -- the control axis."""
EXTENT: Final = "extent"
"""`E`."""


@dataclass(frozen=True, slots=True)
class Axis:
    """One tercile cut of one response, with its null and its coherence."""

    name: str
    response: str
    """`|L|` or `L`."""
    units: int
    surveys: int
    spread: float
    """Top tercile's median response minus the bottom's."""
    null_95: float
    coherence_raw: float
    coherence_corrected: float

    @property
    def beats_null(self) -> bool:
        return abs(self.spread) > self.null_95


@dataclass(frozen=True, slots=True)
class Extent:
    """Prediction 2: does the number of occupied cells move with the numbers?"""

    units: int
    surveys: int
    rho: float
    """Correlation of within-survey ranks of `E` and `N`."""
    null_95: float

    @property
    def follows(self) -> bool:
        return self.rho > 0 and self.rho > self.null_95


@dataclass(frozen=True, slots=True)
class Leg:
    """One record's answer: the marine pairs, or one bird network's species."""

    name: str
    units: int
    surveys: int
    extent: Extent
    size: Axis
    """`|L|` cut by `|N|` -- the magnitude question."""
    precision: Axis
    """`|L|` cut by the trend's own standard error -- the control."""
    signed: Axis
    """`L` cut by signed `N` -- the direction question."""

    @property
    def size_survives_control(self) -> bool:
        """Prediction 3's whole condition: beats its null, and beats the precision spread."""
        return self.size.beats_null and abs(self.size.spread) > abs(self.precision.spread)

    @property
    def direction_follows(self) -> bool:
        """Prediction 5: growing species shift poleward more than declining ones."""
        return self.signed.spread > 0 and self.signed.beats_null


@dataclass(frozen=True, slots=True)
class Phase2e:
    """The whole phase."""

    calibration: float
    marine: Leg | None
    birds: tuple[Leg, ...]
    numbers: phase3k.SpeciesFit | None
    """Prediction 7: `N`'s coherence by species against by survey, with chance levels."""

    @property
    def calibrated(self) -> bool:
        return abs(self.calibration - MARINE_NULL_MEDIAN) < MARINE_TOLERANCE


def _seed(name: str) -> int:
    return (crc32(name.encode()) ^ SEED) & 0x7FFF_FFFF


# --- The panel ------------------------------------------------------------------------------


def yearly_index(restricted: pl.DataFrame, *, event_columns: list[str]) -> pl.DataFrame:
    """Per taxon per year: summed CPUE over the year's events divided by the number of events, and
    the number of consistent cells the taxon was caught in.

    Events are what the caller says they are -- a haul for a trawl, a route-run for a scheme -- and
    are counted from the *whole* restricted frame, not from the taxon's rows, so a year in which the
    survey worked and the species was absent still divides by the effort that was spent.
    """
    events = (
        restricted.select("year", *event_columns).unique().group_by("year").agg(events=pl.len())
    )
    return (
        restricted.filter(pl.col("cpue").is_not_null(), pl.col("cpue") > 0)
        .group_by("taxon_key", "taxon_label", "year")
        .agg(
            total=pl.col("cpue").sum(),
            cells=pl.struct("cell_longitude", "cell_latitude").n_unique(),
        )
        .join(events, on="year", how="inner")
        .with_columns(index=pl.col("total") / pl.col("events"))
        .select("taxon_key", "taxon_label", "year", "index", "cells")
    )


def log_trends(per_taxon: pl.DataFrame, *, min_years: int) -> pl.DataFrame:
    """`N` and `E` per taxon: slopes per decade of the log index and the log cell count.

    Over the years the taxon was caught, at least `min_years` of them. A year with no catch has no
    index and no cells, and a logarithm has no zero; the selection that follows is the same one the
    latitude trend's own floor imposes, and the note says so.
    """
    rows: list[dict[str, object]] = []
    keys = ["taxon_key", "taxon_label"]
    for (key, label), group in per_taxon.group_by(keys, maintain_order=True):
        usable = group.filter(pl.col("index") > 0).sort("year")
        if usable.height < min_years:
            continue
        years = usable["year"].to_numpy().astype(float)
        numbers = stats.linregress(years, np.log(usable["index"].to_numpy().astype(float)))
        extent = stats.linregress(years, np.log(usable["cells"].to_numpy().astype(float)))
        rows.append(
            {
                "taxon_key": str(key),
                "taxon_label": str(label),
                ABUNDANCE: float(numbers.slope * 10.0),
                "abundance_se": float(numbers.stderr * 10.0),
                EXTENT: float(extent.slope * 10.0),
                "index_years": usable.height,
            }
        )
    return pl.DataFrame(rows) if rows else pl.DataFrame()


def _with_axes(table: pl.DataFrame) -> pl.DataFrame:
    return table.with_columns(
        pl.col(ABUNDANCE).abs().alias(SIZE),
        pl.col("stderr").alias(PRECISION),
    )


def marine_panel() -> tuple[pl.DataFrame, float]:
    """Every species-survey pair with `L`, `N` and `E`, and the pooled median `L` to calibrate on.

    The response is `phase1b.analyse`'s own, so the calibration cannot pass against a copy; the
    index is built on the same consistent footprint from the same rows.
    """
    from migratlas.reports import phase1b  # noqa: PLC0415 -- heavy

    cells = range_metrics.to_cells(phase1b.survey_unit(phase1b.load()))
    _, pooled, _ = phase1b.analyse(cells)
    if pooled.is_empty():
        return pl.DataFrame(), float("nan")
    calibration = float(np.median(pooled["per_decade"].to_numpy().astype(float)))

    numbers: list[pl.DataFrame] = []
    for (unit,), survey in cells.group_by(["survey_unit"], maintain_order=True):
        restricted, footprint = range_metrics.consistent_footprint(survey)
        if footprint.cells < range_metrics.MIN_CELLS:
            continue
        trends = log_trends(
            yearly_index(restricted, event_columns=["site_id"]), min_years=MARINE_MIN_YEARS
        )
        if not trends.is_empty():
            numbers.append(trends.with_columns(survey_unit=pl.lit(str(unit))))
    if not numbers:
        return pl.DataFrame(), calibration

    table = pooled.select(
        survey_unit=pl.col("survey_unit").cast(pl.String),
        taxon_key=pl.col("taxon_key").cast(pl.String),
        taxon_label=pl.col("taxon_label").cast(pl.String),
        slope=pl.col("per_decade").cast(pl.Float64),
        stderr=pl.col("stderr").cast(pl.Float64),
    ).join(
        pl.concat(numbers).select("survey_unit", "taxon_key", ABUNDANCE, "abundance_se", EXTENT),
        on=["survey_unit", "taxon_key"],
        how="inner",
    )
    return _with_axes(table), calibration


def bird_panel(source_id: str) -> pl.DataFrame:
    """One network's species with `L` from Phase 1m's table and `N`, `E` from the same counts."""
    from migratlas.reports import phase1k, phase1l, phase1m  # noqa: PLC0415 -- heavy

    window = phase1l.shared_window()
    species = phase1m._species_table(source_id, window)  # noqa: SLF001 -- the project's own
    if species.is_empty():
        return pl.DataFrame()
    frame = phase1k.load_counts(source_id).filter(
        pl.col("period_start").dt.year().is_between(window[0], window[1])
    )
    kept, footprint = range_metrics.consistent_footprint(range_metrics.to_cells(frame))
    if footprint.cells < range_metrics.MIN_CELLS:
        return pl.DataFrame()
    trends = log_trends(
        yearly_index(kept, event_columns=["site_id", "period_start"]), min_years=BIRD_MIN_YEARS
    )
    if trends.is_empty():
        return pl.DataFrame()
    table = species.select(
        taxon_key=pl.col("taxon_key").cast(pl.String),
        slope=pl.col("slope").cast(pl.Float64),
        stderr=pl.col("stderr").cast(pl.Float64),
    ).join(
        trends.select("taxon_key", "taxon_label", ABUNDANCE, "abundance_se", EXTENT),
        on="taxon_key",
        how="inner",
    )
    return _with_axes(table.with_columns(survey_unit=pl.lit(source_id)))


# --- The questions --------------------------------------------------------------------------


def _within_ranks(table: pl.DataFrame, column: str) -> np.ndarray:
    """Ranks of `column` inside each survey, so a pooled correlation is a within-survey one."""
    return (
        table.select(pl.col(column).rank("average").over("survey_unit"))
        .to_series()
        .to_numpy()
        .astype(float)
    )


def extent_follows(table: pl.DataFrame, *, draws: int = DRAWS) -> Extent:
    """Prediction 2: the correlation of within-survey ranks of `E` and `N`, against a null that
    shuffles `N` inside each survey."""
    counts = table.group_by("survey_unit").agg(pl.len().alias("n"))
    enough = counts.filter(pl.col("n") >= MIN_UNITS_PER_SURVEY)["survey_unit"]
    usable = table.filter(pl.col("survey_unit").is_in(enough.implode()))
    if usable.height < MIN_UNITS_PER_SURVEY:
        return Extent(units=usable.height, surveys=0, rho=float("nan"), null_95=float("nan"))
    e = _within_ranks(usable, EXTENT)
    n = _within_ranks(usable, ABUNDANCE)
    rho = float(np.corrcoef(e, n)[0, 1])

    rng = np.random.default_rng(_seed("extent"))
    keys = usable["survey_unit"].to_numpy()
    blocks = [np.flatnonzero(keys == key) for key in np.unique(keys)]
    values = np.empty(draws, dtype=float)
    for draw in range(draws):
        shuffled = n.copy()
        for block in blocks:
            shuffled[block] = rng.permutation(n[block])
        values[draw] = float(np.corrcoef(e, shuffled)[0, 1])
    return Extent(
        units=usable.height,
        surveys=int(enough.len()),
        rho=rho,
        null_95=float(np.percentile(values, 95)),
    )


def axis(table: pl.DataFrame, name: str, *, response: str) -> Axis | None:
    """One tercile cut, through Phase 3j's machinery unchanged.

    `response` is `L` (the signed latitude trend, for the direction question) or `|L|` (for the
    magnitude question and its control); the column `_spread` reads is `slope`, so the frame handed
    to Phase 3j carries the chosen response under that name.
    """
    frame = table.with_columns(
        slope=pl.col("slope").abs() if response == "|L|" else pl.col("slope")
    )
    assigned = phase3j._assign(frame, name, within_survey=True)  # noqa: SLF001 -- the project's own
    if assigned.is_empty() or assigned["group"].n_unique() < phase3j.TERCILES:
        return None
    raw, corrected = _icc(assigned)
    return Axis(
        name=name,
        response=response,
        units=assigned.height,
        surveys=assigned["survey_unit"].n_unique(),
        spread=phase3j._spread(assigned),  # noqa: SLF001
        null_95=phase3j._null_spread(assigned, name, within_survey=True),  # noqa: SLF001
        coherence_raw=raw,
        coherence_corrected=corrected,
    )


def leg(name: str, table: pl.DataFrame, *, draws: int = DRAWS) -> Leg | None:
    """One record, all four questions.

    The table is sorted first. Phase 3f's correction 1, met again: every null here draws its
    permutations from a stream seeded by the axis name, and a join's row order is not stable between
    runs, so the same seed landed on differently ordered rows and the null bars moved in their third
    decimal while every observed spread stayed put. The first two runs of this phase found it.
    """
    if table.is_empty():
        return None
    # All three keys: 95 taxon keys carry two or more verbatim labels (TASKS #3), and a sort on
    # the key alone left those rows tied and the bird nulls still moving in their third decimal.
    table = table.sort(["survey_unit", "taxon_key", "taxon_label"])
    size = axis(table, SIZE, response="|L|")
    precision = axis(table, PRECISION, response="|L|")
    signed = axis(table, ABUNDANCE, response="L")
    if size is None or precision is None or signed is None:
        log.info("%s: a tercile could not be formed", name)
        return None
    return Leg(
        name=name,
        units=table.height,
        surveys=table["survey_unit"].n_unique(),
        extent=extent_follows(table, draws=draws),
        size=size,
        precision=precision,
        signed=signed,
    )


def numbers_by_species(table: pl.DataFrame, *, draws: int = DRAWS) -> phase3k.SpeciesFit | None:
    """Prediction 7: is a change in numbers the species' or the sea's?

    Phase 3k's estimand B, on `N` rather than on `L`.
    """
    pooled_like = table.sort(["survey_unit", "taxon_key", "taxon_label"]).select(
        per_decade=pl.col(ABUNDANCE),
        stderr=pl.col("abundance_se"),
        taxon_key=pl.col("taxon_key"),
        survey_unit=pl.col("survey_unit"),
    )
    return phase3k.fit_species(pooled_like, draws=draws)


# --- The phase -------------------------------------------------------------------------------


def collect(*, draws: int = DRAWS) -> Phase2e | None:
    """The calibration, the marine leg, the three bird legs, and the numbers' coherence."""
    marine, calibration = marine_panel()
    if not np.isfinite(calibration):
        log.warning("phase2e: no marine pairs, so nothing to calibrate to")
        return None
    birds = tuple(
        result
        for source_id in BIRD_NETWORKS
        if (result := leg(source_id, bird_panel(source_id), draws=draws)) is not None
    )
    return Phase2e(
        calibration=calibration,
        marine=leg(MARINE, marine, draws=draws),
        birds=birds,
        numbers=numbers_by_species(marine, draws=draws) if not marine.is_empty() else None,
    )


def _axis_lines(label: str, item: Axis) -> list[str]:
    return [
        f"  {label}: spread {item.spread:+.4f} against a null bar of {item.null_95:.4f} -- "
        f"{'BEATS' if item.beats_null else 'inside'}; coherence {item.coherence_corrected:.3f} "
        f"corrected ({item.coherence_raw:.3f} raw); {item.units:,} units, {item.surveys} surveys",
    ]


def _leg_lines(item: Leg) -> list[str]:
    return [
        f"{item.name} -- {item.units:,} units in {item.surveys} surveys",
        f"  extent follows abundance: within-survey rank correlation {item.extent.rho:+.3f} "
        f"against a null bar of {item.extent.null_95:.3f} over {item.extent.units:,} units -- "
        f"{'FOLLOWS' if item.extent.follows else 'does NOT follow'}",
        *_axis_lines("|L| by |N|", item.size),
        *_axis_lines("|L| by precision (control)", item.precision),
        f"  magnitude survives the control: {'YES' if item.size_survives_control else 'NO'}",
        *_axis_lines("L by signed N", item.signed),
        f"  growing species shift poleward more: {'YES' if item.direction_follows else 'NO'}",
        "",
    ]


def render() -> str:
    """Calibration, every leg, the numbers' coherence, one verdict line."""
    out = [
        "Phase 2e -- is where an animal moved the population's?",
        "=" * 78,
        "Pre-registered in docs/methods/phase2e-population-shifts.md before any abundance trend",
        "was fitted. Terciles, spreads and nulls are Phase 3j's; coherence is Phase 1m's; the",
        "species-against-survey question is Phase 3k's. Predictions are graded in the note.",
        "",
    ]
    read = collect()
    if read is None:
        return "\n".join([*out, "VERDICT: nothing to read -- see the log."])
    out += [
        f"Calibration -- pooled marine median {read.calibration:+.4f} against "
        f"{MARINE_NULL_MEDIAN:+.3f}: {'PASS' if read.calibrated else 'FAIL'}",
        "",
    ]
    if not read.calibrated:
        return "\n".join([*out, "VERDICT: calibration FAILED -- nothing above it is interpreted."])

    if read.marine is not None:
        out += _leg_lines(read.marine)
    else:
        out += ["fishglob -- no leg could be formed", ""]
    for item in read.birds:
        out += _leg_lines(item)

    if read.numbers is not None:
        n = read.numbers
        out.append(
            f"N by species against by survey -- {n.pairs:,} pairs, {n.taxa} taxa in {n.surveys} "
            f"surveys: {n.by_species.corrected:.3f} against {n.by_survey.corrected:.3f} corrected"
        )
        for chance in (n.species_chance, n.survey_chance):
            if chance is not None:
                out.append(
                    f"  chance level by {chance.grouping}: {chance.null_median:.3f} "
                    f"(95th {chance.null_95:.3f}); observed {chance.observed:.3f} is "
                    f"{chance.excess:+.3f} over chance"
                )
        out.append("")

    verdict: list[str] = []
    if read.marine is not None:
        verdict.append(
            f"marine |L| by |N| {'beats' if read.marine.size.beats_null else 'inside'} its null "
            f"and {'survives' if read.marine.size_survives_control else 'FAILS'} the control"
        )
        verdict.append(
            f"direction {'follows' if read.marine.direction_follows else 'does not follow'}"
        )
    verdict.append(
        f"birds surviving the control: {sum(1 for b in read.birds if b.size_survives_control)} "
        f"of {len(read.birds)}"
    )
    return "\n".join([*out, "VERDICT: " + "; ".join(verdict)])
