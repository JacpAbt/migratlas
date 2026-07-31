"""What the research established, as a document the globe can render.

The site showed three raw layers and no results, which is the wrong way round: the layers are
the input to the work, not the output. This is the output.

Two rules make it worth having rather than a page of prose that drifts:

- **Every number is computed here, from the lake, by the same functions the reports use.** A
  finding on the site is therefore the finding the pipeline produces, not a figure someone typed
  once and forgot to update. Slow on purpose -- it re-runs the analysis.
- **Every finding carries a limit, and the schema will not let it not.** A claim published
  without its scope and caveat is the failure mode this whole project is arranged against, so
  `Finding` makes both required and a test asserts they are non-empty.

Nulls are findings. "No global marine shift" and "0% of the time-series data is southern
hemisphere" are results, and a site that only showed the positive ones would be lying by
selection.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Final

import numpy as np
import polars as pl

from migratlas.evidence import EvidenceType, Realm, TaxonScope
from migratlas.lake.reader import scan, scan_dataset

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)

SCHEMA_VERSION: Final = 2

# The domains ROBITT asks about (Boyd et al. 2022, Methods in Ecology and Evolution 13:1497), a
# 17-question tool for risk of bias in studies of temporal trends, built on PRISMA's model. Adopted
# rather than invented, for the same reason the ethics gate implements GBIF's sensitive-species
# guidance instead of writing a policy: a published standard carries credibility an in-house
# checklist cannot, and this project turns out to have been answering these questions already.
#
# Every domain asks the same second question -- did coverage hold *over time* -- which is what makes
# it a temporal-trend tool rather than a general one.
BIAS_DOMAINS: Final[tuple[str, ...]] = (
    "geographic",
    "temporal",
    "taxonomic",
    "environmental",
    "detectability",
    "phenological",
)

# What the work did about a domain, in the four honest answers available.
BIAS_STATUSES: Final[tuple[str, ...]] = (
    # Tested, and the test came back clean enough to proceed.
    "addressed",
    # Not eliminated, but measured, and the claim narrowed to where it holds.
    "bounded",
    # Known, unresolved, and stated. The 2012 step lives here.
    "open",
    "not applicable",
)


@dataclass(frozen=True, slots=True)
class BiasDomain:
    """One ROBITT domain, and what happened when this claim was checked against it."""

    domain: str
    status: str
    finding: str
    """One line. Not "we considered this" -- what was done and what came back."""


@dataclass(frozen=True, slots=True)
class Finding:
    """One thing the work established, with everything needed to read it honestly."""

    key: str
    claim: str
    """One sentence, in the strongest form the evidence supports and no stronger."""

    value: str
    """The number, formatted for display, with its interval."""

    scope: str
    """Where and when it holds. A claim without this is a claim about the whole world."""

    caveat: str
    """What would make it wrong, or what it does not cover. Required, never blank."""

    method: str
    """Path to the pre-registered method note, relative to the repository root."""

    realm: str
    """`aerial`, `terrestrial`, `marine` or `freshwater`.

    Required, and required for a reason beyond tidiness. This project was built taxon-agnostic and
    then drifted: three consecutive sources were birds. Making the realm a field a claim cannot
    omit, and testing that the published set spans more than one, is the same kind of structural
    guarantee as the evidence-type core itself -- a convention would drift again.
    """

    taxon_scope: str
    """`exact`, `aggregate` or `unattributed`. The radar's is `unattributed`, and that is the point:
    it measures biomass, and a claim that quietly said "birds" would be overclaiming."""

    evidence_type: str
    """Which of the seven shapes the claim rests on, so a reader can see four are still unused."""

    bias: list[BiasDomain] = field(default_factory=list)
    """The ROBITT assessment. Required in practice -- a test refuses a claim without one."""

    direction: str = "neutral"
    """`change`, `null`, or `limit` -- so the frontend can group rather than parse the text."""

    supporting: list[str] = field(default_factory=list)
    """Tests the claim survived, each one line."""


def _domains(**findings: tuple[str, str]) -> list[BiasDomain]:
    """Build an assessment from `domain=(status, finding)` pairs, in ROBITT's order."""
    return [
        BiasDomain(domain=domain, status=findings[domain][0], finding=findings[domain][1])
        for domain in BIAS_DOMAINS
        if domain in findings
    ]


# The assessments live here rather than inside `collect` so they read as a document. Every line is a
# re-expression of something already in a method note under docs/methods/ -- none of it is new
# analysis, and that is the point: the work was ROBITT-shaped before the framework was known.
AUTUMN_ADVANCE_BIAS: Final = _domains(
    geographic=(
        "bounded",
        "Survives only at 37-50°N. The southern bands carry an unexplained 2012 step and are "
        "excluded, so this is a regional result and 'continental' is not available.",
    ),
    temporal=(
        "open",
        "A latitude-graded step change at 2012 is still unexplained: truncation, panel "
        "composition, curvature and drought were each tested and each failed to explain it.",
    ),
    taxonomic=(
        "bounded",
        "The instrument measures aerial biomass, not birds. Bats and insects are not "
        "excluded; mean autumn airspeed of 8.65 m/s sits in the songbird range, which bounds the "
        "drift without identifying the taxa.",
    ),
    environmental=(
        "bounded",
        "Stations sit where weather radar was funded, not on a sample of habitat, so the panel is "
        "not environmentally representative of the continent it covers.",
    ),
    detectability=(
        "addressed",
        "The dataset's own rain screening steps at 2012, and independent ERA5 precipitation "
        "shows no matching drying, so the step is instrumental rather than meteorological. "
        "Dropping the speed weighting leaves the trend unchanged (-0.09 +/- 0.14, r = 0.86).",
    ),
    phenological=(
        "addressed",
        "The passage window and the quantile definition were matched to the published metric "
        "before any extension, so the replication is of the same quantity, not a similar one.",
    ),
)

MARINE_NULL_BIAS: Final = _domains(
    geographic=(
        "bounded",
        "29 surveys across North America and Europe: 0% southern hemisphere and 0% tropics, "
        "so this is a null for the northern temperate zone and not for the ocean.",
    ),
    temporal=(
        "addressed",
        "A cell enters only where it was sampled consistently across the window, and a gear-change "
        "break term is fitted for every survey that changed gear.",
    ),
    taxonomic=(
        "addressed",
        "Around 2,000 species, and the unit of analysis is the species in its region rather "
        "than the ocean: pooling destroys the finding, since surveys disagree in sign.",
    ),
    environmental=(
        "bounded",
        "A bottom-trawl survey samples trawlable ground. Rocky, protected and untrawlable "
        "habitat is absent by construction, and species that live there cannot appear.",
    ),
    detectability=(
        "addressed",
        "Three Alaskan surveys publish catch per unit area rather than raw catch; effort is "
        "recorded as prestandardised so the centroid weighting stays correct rather than wrong.",
    ),
    phenological=(
        "bounded",
        "Surveys run in fixed seasons, so a species that shifted its seasonal timing rather "
        "than its position would not show up here at all.",
    ),
)

COMPOSITION_BIAS: Final = _domains(
    temporal=(
        "open",
        "Spring behaves differently: airspeed rose +0.50 +/- 0.13 m/s per decade, either a "
        "real change or migrants flying above the fixed 925 hPa wind level. Separating them needs "
        "the vertical profiles, so spring carries no trend claim.",
    ),
    taxonomic=(
        "addressed",
        "This is the taxonomic test. Autumn airspeed is flat and sits in the songbird range "
        "rather than the 0-5 m/s insect range, and deleting the 293,497 non-bird nights outright "
        "moves the advance only from -0.56 to -0.42.",
    ),
    environmental=(
        "bounded",
        "Wind comes from a 32 km reanalysis at a single pressure level, so a station near a "
        "coast or a mountain front is represented worse than an inland one.",
    ),
    detectability=(
        "addressed",
        "The wind is from an independent regional reanalysis rather than from the radar, so the "
        "airspeed estimate does not inherit the radar's own errors.",
    ),
    phenological=(
        "addressed",
        "Airspeed is computed per station-night inside the same August-November window as the "
        "passage metric, so the two describe the same nights.",
    ),
)

ATTRIBUTION_BIAS: Final = _domains(
    geographic=(
        "bounded",
        "37-50°N, and the models are 1-2°, so the human fraction is regional rather than local to "
        "any one station.",
    ),
    temporal=(
        "bounded",
        "CMIP6 `historical` ends in 2014 while the observed record runs to 2025, so the "
        "fraction is measured over an earlier window than the magnitude it scales. That mismatch "
        "is why it is built as a ratio rather than a difference.",
    ),
    taxonomic=(
        "bounded",
        "Inherits the radar's caveat whole. This attributes the *warming*, not the animals, "
        "and says nothing about which taxa responded.",
    ),
    environmental=(
        "addressed",
        "Sampled at the radar stations rather than globally, so the fraction is local to where the "
        "counting actually happened.",
    ),
    detectability=(
        "addressed",
        "A synthetic null — the same machinery run on two halves of one experiment — returns 3% of "
        "the forced difference, which bounds how much could be internal variability.",
    ),
    phenological=(
        "addressed",
        "The June-July pre-season window is the one the response function was fitted on, and "
        "it does not overlap the August-November response it predicts.",
    ),
)

COVERAGE_BIAS: Final = _domains(
    geographic=(
        "open",
        "This claim *is* the geographic bias. Every source with a usable time axis is northern "
        "temperate; the two with global reach cannot support a trend.",
    ),
    temporal=(
        "bounded",
        "Measured from the lake rather than asserted, and recomputed on every build, so the day a "
        "southern source lands the number moves on its own.",
    ),
    taxonomic=(
        "open",
        "The terrestrial realm is entirely birds — three sources, one class. Four of the seven "
        "evidence types are unused, and they are where mammals, reptiles and insects live.",
    ),
    environmental=(
        "open",
        "Long digitised radar and trawl series exist where they were funded, so the environmental "
        "space this project covers is a funding history rather than a sample.",
    ),
)


def _radar_coverage() -> tuple[int, int, int]:
    """Stations, first and last year of the radar record, read from the lake."""
    frame = (
        scan(EvidenceType.FLUX, source_id="darkecology_daily")
        .select(
            station=pl.col("station_id"),
            year=pl.col("timestamp").dt.year(),
        )
        .collect()
    )
    years = frame["year"].to_numpy()
    return frame["station"].n_unique(), int(years.min()), int(years.max())


def _southern_share() -> dict[str, float]:
    """Share of each time-series source's rows south of the equator.

    Computed rather than quoted, because this is the finding most likely to become false
    silently -- the day a southern source lands, a hardcoded 0% would be a lie on the site.
    """
    shares: dict[str, float] = {}
    for source, latitude in (
        ("darkecology_daily", "station_latitude"),
        ("fishglob", "site_latitude"),
    ):
        evidence = EvidenceType.FLUX if source == "darkecology_daily" else EvidenceType.SURVEY_INDEX
        frame = scan(evidence, source_id=source).select(pl.col(latitude).alias("lat")).collect()
        values = frame["lat"].to_numpy()
        shares[source] = float((values < 0).mean()) if values.size else float("nan")
    return shares


def _wind_coverage() -> tuple[int, int, int]:
    """Station-nights of wind, and the span, for the composition finding."""
    frame = (
        scan_dataset("driver_samples", source_id="narr")
        .select(year=pl.col("period_start").dt.year())
        .collect()
    )
    years = frame["year"].to_numpy()
    return frame.height, int(years.min()), int(years.max())


def collect() -> list[Finding]:
    """Compute every finding. Re-runs the analyses, so this takes minutes rather than seconds."""
    # Imported here rather than at module scope: the reports import this module's siblings,
    # so a top-level import would close a cycle.
    from migratlas.metrics import range as range_metrics  # noqa: PLC0415
    from migratlas.reports import phase1b  # noqa: PLC0415
    from migratlas.reports.phase1 import load_conus_nights, station_slopes  # noqa: PLC0415

    _, first_year, last_year = _radar_coverage()
    southern = _southern_share()

    findings: list[Finding] = []

    # --- The headline -------------------------------------------------------
    slopes = station_slopes(load_conus_nights(), max_year=last_year)
    autumn = slopes.filter(
        pl.col("season") == "autumn",
        pl.col("quantile") == "q50_doy",
        pl.col("latitude").is_between(37, 50, closed="left"),
    )
    values = autumn["days_per_decade"].to_numpy().astype(float)
    mean = float(values.mean())
    ci = 1.96 * float(values.std(ddof=1)) / np.sqrt(values.size)
    findings.append(
        Finding(
            key="autumn-advance",
            realm=Realm.AERIAL.value,
            taxon_scope=TaxonScope.UNATTRIBUTED.value,
            evidence_type=EvidenceType.FLUX.value,
            bias=AUTUMN_ADVANCE_BIAS,
            claim="Nocturnal autumn passage over the mid-latitude US is happening earlier.",
            value=f"{mean:+.2f} ± {ci:.2f} days per decade",
            scope=(
                f"{autumn.height} US weather-radar stations between 37°N and 50°N, "
                f"{first_year}-{last_year}. Not the whole continent: the southern bands carry a "
                "step change at 2012 that four candidate explanations have failed to account for."
            ),
            caveat=(
                "The radar measures aerial biomass, not birds — it cannot separate birds from "
                "bats from insects. Bats in particular are not excluded."
            ),
            method="docs/methods/phase1-phenology.md",
            direction="change",
            supporting=[
                "Reproduces a published result on its own window before extending it.",
                "Survives four break specifications, a mid-winter placebo and a permutation null.",
                "Unchanged when the speed weighting is removed from the metric.",
                "Unchanged when the non-bird nights are deleted outright.",
            ],
        )
    )

    # --- The null that matters just as much --------------------------------
    # Through the same three steps `phase1b.render` uses, in the same order: the survey unit has
    # to be recovered from the site id before cells are formed, or `analyse` has nothing to group
    # by. Calling the report's own functions rather than restating them is the point -- a second
    # copy of the data preparation is a second thing that can drift from the published method.
    _, pooled, _ = phase1b.analyse(range_metrics.to_cells(phase1b.survey_unit(phase1b.load())))
    shift = pooled["per_decade"].to_numpy().astype(float)
    findings.append(
        Finding(
            key="marine-null",
            realm=Realm.MARINE.value,
            taxon_scope=TaxonScope.EXACT.value,
            evidence_type=EvidenceType.SURVEY_INDEX.value,
            bias=MARINE_NULL_BIAS,
            claim=(
                "There is no single global poleward shift in fish distribution — surveys "
                "disagree even in its direction."
            ),
            value=(
                f"median {float(np.median(shift)):+.3f} °latitude per decade "
                f"across {shift.size:,} species-survey pairs"
            ),
            scope=(
                "29 harmonised scientific bottom-trawl surveys, North America and Europe, "
                "on consistently sampled cells only."
            ),
            caveat=(
                "A pooled median hides the variation worth predicting: individual surveys reach "
                "-0.22 and +0.26 °latitude per decade in opposite directions. The unit of "
                "analysis has to be the species in its region, not the ocean."
            ),
            method="docs/methods/phase1b-marine.md",
            direction="null",
        )
    )

    # --- The measurement itself, audited ----------------------------------
    nights, wind_first, wind_last = _wind_coverage()
    findings.append(
        Finding(
            key="composition-stable",
            realm=Realm.AERIAL.value,
            taxon_scope=TaxonScope.UNATTRIBUTED.value,
            evidence_type=EvidenceType.FLUX.value,
            bias=COMPOSITION_BIAS,
            claim=(
                "The autumn signal is not drifting from birds towards insects — what the radar "
                "measures in 2025 means what it meant in 1995."
            ),
            value="airspeed trend -0.06 ± 0.08 m/s per decade (flat)",
            scope=(
                f"{nights:,} station-night wind samples, {wind_first}-{wind_last}, from an "
                "independent regional reanalysis rather than from the radar."
            ),
            caveat=(
                "Spring behaves differently: its airspeed rose, which is either a real change or "
                "migrants flying higher than the fixed wind level assumes. Separating those needs "
                "the vertical radar profiles. Spring carries no trend claim here either way."
            ),
            method="docs/methods/phase1c-homogeneity.md",
            direction="change",
            supporting=[
                "Mean autumn airspeed sits in the range for migrating songbirds, not insects.",
                "A 2012 discontinuity in the dataset's own rain filtering was traced, and ruled "
                "out as weather using independent precipitation data.",
            ],
        )
    )

    # --- The causal step ----------------------------------------------------
    # Published only if the model ensemble is whole. `shortfall` exists because a third of it can
    # go missing on a calendar error and still produce a plausible number, and a site is the last
    # place that should be quoting one.
    from migratlas.reports import phase2a_attribution as attribution  # noqa: PLC0415

    simulations = attribution.simulated()
    seen = attribution.observed()
    windows = [
        found
        for window in attribution.WINDOWS
        if (found := attribution.fraction(simulations, window)) is not None
    ]
    if seen is not None and windows and not attribution.shortfall(simulations):
        primary = attribution.chosen(windows)
        days = primary.ensemble * seen.explained
        bracket = sorted(found.ensemble for found in windows)

        # A second counterfactual, built from observations rather than models, attributes a much
        # smaller advance. That is not a competing estimate of this number and it is not averaged
        # into it -- but it changes how "almost all" here should be read, so it goes in the caveat
        # rather than staying in a methods note nobody opens.
        from migratlas.reports import phase2a_attrici  # noqa: PLC0415

        second = phase2a_attrici.attributed(seen.sensitivity, seen.sensitivity_ci95)
        variability = (
            ' Read "almost all" as a share of the forced warming as the ensemble mean has it, '
            f"though: averaging {primary.models} models cancels the year-to-year weather, so what "
            "the ratio divides into is close to a pure forced signal rather than the trend a "
            "thermometer at one station recorded. An independent counterfactual built from the "
            "observations themselves, with no model in it (ATTRICI), removes only "
            f"{second.share_of_factual:.0%} of each station's own warming and so attributes "
            f"{second.advance:+.2f} days per decade against this finding's {days:+.2f}. Neither is "
            "wrong and they are not averaged: the distance between them says that roughly "
            f"{1 - abs(second.advance / days):.0%} of the warming at these stations over "
            f"{second.window[0]}-{second.window[1]} does not move with the global mean at all. "
            "Over twenty-five years at one half-degree cell that is mostly weather leaning one "
            "way — but it also holds any forcing that does not scale with the global average, so "
            "it is an upper bound on the chance part rather than a measurement of it. Either "
            "way: human forcing caused nearly all of the warming signal, and that is not the "
            "same thing as nearly all of the warming these stations measured."
            if second is not None
            else ""
        )
        findings.append(
            Finding(
                key="anthropogenic-share",
                realm=Realm.AERIAL.value,
                taxon_scope=TaxonScope.UNATTRIBUTED.value,
                evidence_type=EvidenceType.FLUX.value,
                bias=ATTRIBUTION_BIAS,
                claim=(
                    # "the animals", not "the birds". This claim's taxon scope is
                    # `unattributed` and the margin next to it says so, while `autumn-advance`
                    # two cards over says the radar cannot separate birds from bats from
                    # insects. It was the one claim in the ledger contradicting the rest of it.
                    "Human forcing accounts for almost all of the pre-season warming the animals "
                    "are responding to, and so for about half of the observed advance."
                ),
                value=f"{days:+.2f} days per decade of the {seen.advance:+.2f} observed",
                scope=(
                    f"{primary.models} CMIP6 models with both a historical and a hist-nat run, "
                    f"sampled at the {seen.stations} radar stations between 37°N and 50°N over "
                    f"{primary.window[0]}-{primary.window[1]}."
                ),
                caveat=(
                    "This attributes the warming, not the migration. It says what caused the "
                    "temperature change the record tracked — the other half of the advance does "
                    "not track temperature at all and is unexplained here. The models' human "
                    "share "
                    f"spans {bracket[0]:.2f} to {bracket[-1]:.2f} depending on the window fitted, "
                    "and CMIP6's historical runs stop in 2014 while the radar record runs to 2025."
                    + variability
                ),
                method="docs/methods/phase2a-attribution.md",
                direction="change",
                supporting=[
                    "The counterfactual runs warm at "
                    f"{primary.natural:+.2f} °C per decade against {primary.historical:+.2f} "
                    "with human forcing included.",
                    "The ensemble reproduces the observed pre-season warming it is calibrated "
                    "against, which is the check that licenses using it.",
                    "Members are averaged within a model before models are averaged, so two "
                    "models with fifty runs each cannot carry the answer.",
                ],
            )
        )

    # --- The limit, published rather than buried --------------------------
    findings.append(
        Finding(
            key="coverage-bias",
            # Every realm at once, so the field names the whole lake rather than picking one.
            realm="all",
            taxon_scope="all",
            evidence_type="all",
            bias=COVERAGE_BIAS,
            claim=(
                "Everything above is northern-hemisphere. The data that can measure change and "
                "the data that covers the globe are, so far, different data."
            ),
            value=(
                f"{southern.get('darkecology_daily', float('nan')):.1%} of the radar record and "
                f"{southern.get('fishglob', float('nan')):.1%} of the survey record lie south of "
                "the equator"
            ),
            scope="Every source in this project that has a usable time axis.",
            caveat=(
                "Inherited rather than chosen — long digitised radar and trawl series exist where "
                "they were funded — but it bounds every claim here to the northern temperate zone, "
                "and no model trained on it should be trusted elsewhere without being tested "
                "there first."
            ),
            method="docs/methods/geographic-coverage.md",
            direction="limit",
        )
    )

    return findings


def render(findings: list[Finding]) -> str:
    """The findings document, as JSON for the frontend."""
    return json.dumps(
        {"schema_version": SCHEMA_VERSION, "findings": [asdict(item) for item in findings]},
        indent=1,
    )


def write(destination: Path, computed: list[Finding] | None = None) -> int:
    """Write the findings document, computing it only if the caller has not already.

    The parameter exists because `collect` re-runs the analyses and takes minutes: a caller that
    wants to both save and display the findings must not pay for them twice.
    """
    payload = render(computed if computed is not None else collect())
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(payload + "\n", encoding="utf-8")
    return len(payload)
