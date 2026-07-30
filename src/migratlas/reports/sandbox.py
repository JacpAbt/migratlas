"""The confound sandbox: the same analysis with its safeguards switched off.

The claim ledger says a number and lists the tests it survived. This says something a reader can
check: **here is what the number becomes when you remove the correction.** Turning the effort rule
off and watching a null become a trend teaches more about ecological trend detection in twenty
seconds than a paragraph of caveats does in five minutes.

Two properties make it worth trusting rather than merely watching.

**No new science.** Every setting here is already a parameter of a function the reports call --
`consistent_footprint(consistency=)`, `load_conus_nights(quantity=)`, `specification_estimates`,
`permutation_null`. This module walks those parameters and records what comes out; it does not
reimplement a metric. If it did, the sandbox and the findings would be free to disagree.

**The default reproduces the published number exactly.** Each knob names which of its variants
the ledger publishes, and a test asserts the two agree. A sandbox whose "on" state did not match
the published one would be a toy.

The output is precomputed JSON, because the frontend has no lake and no Python -- and because these
variants take minutes: the marine one re-runs the whole Phase 1b analysis once per threshold.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Final

import numpy as np
import polars as pl

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)

SCHEMA_VERSION: Final = 1

# The band the aerial claim survives in, matching `reports/findings.py` and `phase2a_timing`.
CLAIM_BAND: Final[tuple[int, int]] = (37, 50)

# Effort thresholds for the marine footprint rule. 0.8 is what Phase 1b published and 0.6/0.95 are
# its pre-registered sensitivity checks; 0.0 is the one this module adds, and the one that matters
# for teaching -- it is the analysis with no effort correction at all.
FOOTPRINTS: Final[tuple[float, ...]] = (0.0, 0.6, 0.8, 0.95)


@dataclass(frozen=True, slots=True)
class Variant:
    """One setting of one knob, and the number it produces."""

    key: str
    label: str
    value: float
    unit: str
    n: int
    """Stations, or species-survey pairs, the number is averaged over. A variant that quietly
    analyses fewer units is not comparable, so the count travels with the value."""
    ci95: float | None = None
    note: str = ""
    """What this setting means, in the language of the thing being switched off."""


@dataclass(frozen=True, slots=True)
class Knob:
    """A safeguard the reader can switch off, and what happens when they do."""

    key: str
    question: str
    """Phrased as the reader's question -- "what if we ignored survey effort?" -- rather than as the
    name of a parameter. The parameter name is in `source`."""

    why: str
    """Why the safeguard exists. Without this the knob is a slider with no lesson attached."""

    claim: str
    """Which ledger finding this bears on, by key, so the two can be shown together."""

    source: str
    """The function and argument being varied, so a sceptical reader can go and read it."""

    default: str
    """The variant key the ledger publishes. A test asserts it reproduces the published number."""

    variants: list[Variant] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Refusal:
    """An analysis that was *not* run, with the evidence for why not.

    Distinct from a knob on purpose. A knob says "the correction changes the answer"; a refusal says
    "no correction is available, so the question cannot be answered with this data". The second is
    the harder lesson and the more common situation, and a sandbox with only knobs would imply that
    every confound has a switch.
    """

    key: str
    question: str
    """The analysis someone would reasonably want to run."""

    naive: str
    """What it would appear to show."""

    evidence: list[Variant]
    """The measurement that explains the appearance."""

    verdict: str
    method: str


@dataclass(frozen=True, slots=True)
class Sandbox:
    schema_version: int
    knobs: list[Knob]
    refusals: list[Refusal]


def _band(slopes: pl.DataFrame, *, season: str = "autumn", quantile: str = "q50_doy") -> pl.Series:
    """The per-station trends the aerial claim is made from.

    The same filter `findings.py` applies. Kept in one place and asserted equal to the ledger by
    a test, because two copies of a filter are two things that can drift.
    """
    return slopes.filter(
        pl.col("season") == season,
        pl.col("quantile") == quantile,
        pl.col("latitude").is_between(*CLAIM_BAND, closed="left"),
    )["days_per_decade"]


def _mean_ci(values: np.ndarray) -> tuple[float, float]:
    if values.size == 0:
        return (float("nan"), float("nan"))
    ci = 1.96 * float(values.std(ddof=1)) / np.sqrt(values.size) if values.size > 1 else 0.0
    return (float(values.mean()), ci)


def speed_weighting(max_year: int) -> Knob:
    """Does the aerial trend depend on the metric being weighted by how fast things were flying?

    `traffic` integrates reflectivity x speed x height, so a drift in flight speed moves a passage
    date with no change in biomass. `reflectivity_hours` drops the speed term entirely.
    """
    from migratlas.reports.phase1 import load_conus_nights, station_slopes  # noqa: PLC0415

    variants: list[Variant] = []
    for key, quantity, note in (
        (
            "speed-weighted",
            "reflectivity_traffic",
            "The published metric. Integrates reflectivity x speed x height, so it is a measure of "
            "traffic rather than of biomass.",
        ),
        (
            "speed-free",
            "reflectivity_hours",
            "Drops the speed term. If the trend were an artefact of birds flying faster, it would "
            "weaken or vanish here.",
        ),
    ):
        slopes = station_slopes(load_conus_nights(quantity=quantity), max_year=max_year)
        values = _band(slopes).to_numpy().astype(float)
        mean, ci = _mean_ci(values)
        variants.append(
            Variant(
                key=key,
                label=quantity.replace("_", " "),
                value=mean,
                ci95=ci,
                unit="days per decade",
                n=int(values.size),
                note=note,
            )
        )

    return Knob(
        key="speed-weighting",
        question="What if the metric were not weighted by flight speed?",
        why=(
            "A passage date is a cumulative sum of a speed-weighted quantity, so faster flight and "
            "earlier passage look alike. The control is to compute the same date from a quantity "
            "with no speed in it."
        ),
        claim="autumn-advance",
        source="reports.phase1.load_conus_nights(quantity=…)",
        default="speed-weighted",
        variants=variants,
    )


def break_specification(max_year: int) -> Knob:
    """How much does the answer depend on how the dual-polarisation upgrade is modelled?

    The upgrade rolled across the network around 2011-2013 and is a step change in the instrument.
    There is no single correct way to model it, which is exactly why four are reported.
    """
    from migratlas.metrics import breaks  # noqa: PLC0415
    from migratlas.reports.phase1 import load_conus_nights  # noqa: PLC0415
    from migratlas.reports.phase1_robustness import (  # noqa: PLC0415
        ROLLOUT,
        seasonal_series,
        specification_estimates,
    )

    nights = load_conus_nights("night")
    # Restricted to the claim band before fitting, because the ledger publishes the band and
    # `specification_estimates` otherwise reports the whole 143-station network. Comparing a
    # network-wide variant against a band-wide default would make the knob look like it moved the
    # number when all it changed was which stations were in it -- and the test that pins the default
    # to the ledger is what caught that.
    series = seasonal_series(nights, max_year=max_year).filter(
        pl.col("station_latitude").is_between(*CLAIM_BAND, closed="left")
    )
    outages = breaks.find_outages(
        nights,
        site_column="station_id",
        time_column="timestamp",
        window=ROLLOUT,
        min_days=4,
        max_days=40,
    )
    estimates = specification_estimates(series, {o.site: o.start for o in outages}, "autumn")

    variants = [
        Variant(
            key=estimate.label.replace(" ", "-"),
            label=estimate.label,
            value=estimate.days_per_decade,
            ci95=estimate.ci95,
            unit="days per decade",
            n=estimate.stations,
            note="",
        )
        for estimate in estimates
    ]
    return Knob(
        key="break-specification",
        question="What if the hardware upgrade were modelled differently?",
        why=(
            "The dual-polarisation upgrade is a step change in the instrument, and no single way "
            "of modelling it is correct. This is the knob where the answer moves most, and the "
            "direction of the movement is what matters: all four specifications agree on the sign, "
            "and *fitting* a break makes the advance larger rather than smaller. The published "
            "choice fits no break at all, so it sits at the conservative end of the four rather "
            "than the flattering one."
        ),
        claim="autumn-advance",
        source="reports.phase1_robustness.specification_estimates",
        default="no-break-term",
        variants=variants,
    )


def shuffled_years(max_year: int) -> Knob:
    """What does the same machinery produce when the time ordering is destroyed?

    The floor under everything else. If the observed estimate sits inside this null, the pipeline is
    manufacturing a trend out of the distribution of passage dates rather than out of their order.
    """
    from migratlas.reports.phase1 import load_conus_nights, station_slopes  # noqa: PLC0415
    from migratlas.reports.phase1_robustness import (  # noqa: PLC0415
        permutation_null,
        seasonal_series,
    )

    nights = load_conus_nights("night")
    observed = _band(station_slopes(nights, max_year=max_year)).to_numpy().astype(float)
    mean, ci = _mean_ci(observed)
    null_mean, low, high = permutation_null(seasonal_series(nights, max_year=max_year), "autumn")

    return Knob(
        key="shuffled-years",
        question="What if the years were shuffled?",
        why=(
            "Shuffling year labels within each station keeps every station's distribution of "
            "passage dates and destroys their order. Any trend that survives that is arithmetic, "
            "not biology."
        ),
        claim="autumn-advance",
        source="reports.phase1_robustness.permutation_null",
        default="observed",
        variants=[
            Variant(
                key="observed",
                label="years in order",
                value=mean,
                ci95=ci,
                unit="days per decade",
                n=int(observed.size),
                note="The published estimate.",
            ),
            Variant(
                key="shuffled",
                label="years shuffled",
                value=null_mean,
                ci95=(high - low) / 2,
                unit="days per decade",
                n=int(observed.size),
                note=(
                    f"200 permutations, 95% of them between {low:+.2f} and {high:+.2f}. The "
                    "observed estimate has to sit outside this to mean anything."
                ),
            ),
        ],
    )


def survey_effort() -> Knob:
    """What happens to the marine result if survey effort is ignored?

    The knob most worth having. A trawl survey's footprint moves over decades, and a centroid
    computed over a moving footprint measures where the ships went.
    """
    from migratlas.metrics import range as range_metrics  # noqa: PLC0415
    from migratlas.reports import phase1b  # noqa: PLC0415

    cells = range_metrics.to_cells(phase1b.survey_unit(phase1b.load()))
    variants: list[Variant] = []
    for consistency in FOOTPRINTS:
        _, pooled, _ = phase1b.analyse(cells, consistency=consistency)
        values = pooled["per_decade"].to_numpy().astype(float)
        variants.append(
            Variant(
                key=f"footprint-{consistency:g}",
                label=(
                    "no effort correction"
                    if consistency == 0
                    else f"cells sampled in {consistency:.0%} of years"
                ),
                value=float(np.median(values)) if values.size else float("nan"),
                unit="degrees latitude per decade",
                n=int(values.size),
                note=(
                    "Every cell a haul ever touched, so the centroid follows the fleet."
                    if consistency == 0
                    else "A cell counts only where it was sampled in this share of the survey's "
                    "years, so the footprint cannot drift underneath the centroid."
                ),
            )
        )

    return Knob(
        key="survey-effort",
        question="What if we ignored where the ships actually went?",
        why=(
            "A distribution centroid is a weighted mean of the places you looked. Widen the "
            "footprint over time and the centroid moves without a single fish moving, which is the "
            "single most common way a range shift is invented."
        ),
        claim="marine-null",
        source="metrics.range.consistent_footprint(consistency=…)",
        default="footprint-0.8",
        variants=variants,
    )


MEDIAN: Final = 50

# The year the OBIS start-year distribution is split at for the naive comparison. Chosen because
# the median first-recorded year is 2012, so it puts roughly half the cells on each side rather
# than being tuned to produce a difference.
RECENT_FROM: Final = 2010


def obis_refusal() -> Refusal:
    """The analysis Phase 1b decided not to run, and the measurement behind the decision.

    Kept as a refusal rather than a knob because OBIS carries no per-year sampling record: there is
    one row per taxon-cell with a min and max year, so there is nothing to compute a footprint rule
    from. The confound cannot be corrected, only demonstrated -- which is the harder and more common
    situation, and the reason this type exists.
    """
    from migratlas.evidence import EvidenceType  # noqa: PLC0415
    from migratlas.lake.reader import scan  # noqa: PLC0415

    frame = (
        scan(EvidenceType.ABUNDANCE_SURFACE, source_id="obis_speciesgrids")
        .select(
            start=pl.col("period_start").dt.year(),
            latitude=pl.col("cell_latitude"),
        )
        .collect()
    )
    starts = frame["start"].to_numpy().astype(float)
    evidence = [
        Variant(
            key=f"start-p{share:g}",
            label=f"{share:.0f}th percentile first-recorded year",
            value=float(np.percentile(starts, share)),
            unit="year",
            n=int(starts.size),
            note=(
                "Half of these cells were first recorded after this year: the record is mostly "
                "recent, so 'where a species was first seen' is largely a statement about when "
                "people started looking there."
                if share == MEDIAN
                else ""
            ),
        )
        for share in (10, 50, 90)
    ]
    north = float(np.mean(frame.filter(pl.col("start") >= RECENT_FROM)["latitude"].to_numpy()))
    early = float(np.mean(frame.filter(pl.col("start") < RECENT_FROM)["latitude"].to_numpy()))
    evidence.append(
        Variant(
            key="mean-latitude-shift",
            label="mean cell latitude, recent minus early first records",
            value=north - early,
            unit="degrees latitude",
            n=int(starts.size),
            note=(
                "The apparent poleward signal. It is the same size and sign whether the animals "
                "moved or the surveying did, and nothing in this dataset separates the two."
            ),
        )
    )

    return Refusal(
        key="obis-poleward",
        question="Did marine species' first-detection cells move polewards?",
        naive=(
            "Comparing cells first recorded recently against cells first recorded early makes the "
            "record look like it moved polewards."
        ),
        evidence=evidence,
        verdict=(
            "Not run, and not runnable. Survey effort expanded polewards over exactly the period "
            "the hypothesis is about, so the dominant confound points the same way as the "
            "prediction — and OBIS carries one row per taxon-cell with a first and last year, so "
            "there is no per-year sampling record to build an effort correction from. The right "
            "answer is a different dataset, which is why FISHGLOB was ingested."
        ),
        method="docs/methods/phase1b-marine.md",
    )


def collect(max_year: int = 2025) -> Sandbox:
    """Walk every knob. Slow: it re-runs the analyses, the marine one once per threshold."""
    knobs = []
    for build in (speed_weighting, break_specification, shuffled_years):
        log.info("computing %s", build.__name__)
        knobs.append(build(max_year))
    log.info("computing survey_effort across %d thresholds", len(FOOTPRINTS))
    knobs.append(survey_effort())

    log.info("computing the OBIS refusal")
    return Sandbox(schema_version=SCHEMA_VERSION, knobs=knobs, refusals=[obis_refusal()])


def render(sandbox: Sandbox) -> str:
    return json.dumps(asdict(sandbox), indent=1)


def write(destination: Path, computed: Sandbox | None = None) -> int:
    """Write the sandbox document, computing it only if the caller has not already."""
    payload = render(computed if computed is not None else collect())
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(payload + "\n", encoding="utf-8")
    return len(payload)
