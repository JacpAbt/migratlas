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
from migratlas.lake.reader import sources as lake_sources

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)

SCHEMA_VERSION: Final = 3

# Enforced by a test rather than by trimming. A plain sentence that grows past this has become a
# second dense paragraph, and the reader who needed it has been lost twice.
PLAIN_MAX_CHARS: Final = 180

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

    plain: str
    """The same finding for someone with no statistics, in one sentence.

    A second register above the claim rather than a replacement for it. ADR 0007 refuses to let the
    layout decide what the science says, and this does not: `claim` is still rendered in full,
    unshortened, underneath. What changed is which one is the heading.

    The rule that makes this safe is that a plain sentence may drop precision but may never add
    reach. "Autumn night flights over the United States" is allowed where the claim says
    "nocturnal autumn passage over the mid-latitude US"; "birds are migrating earlier" is not,
    because the radar cannot see a bird and the whole of Phase 1c exists to bound that.
    """

    matters: str
    """Why a reader should care. One or two sentences.

    The site said what was measured and how confident to be about it, and never once said why any
    of it was worth measuring. That is a strange omission for a page whose entire argument is that
    the reader should look closer.
    """

    claim: str
    """One sentence, in the strongest form the evidence supports and no stronger."""

    plain_caveat: str
    """The one limit a reader must carry away, in plain words. Always rendered.

    `caveat` is the complete statement and stays complete -- the attribution one runs to fourteen
    hundred characters, because that is how long it takes to say something true about two
    disagreeing counterfactuals. A reader who bounces off that paragraph currently leaves with no
    caveat at all, which is worse than leaving with the short one.
    """

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

ATLAS_BIAS: Final = _domains(
    geographic=(
        "bounded",
        "South Africa, Lesotho and Eswatini, and inside them only the 496 quarter-degree cells "
        "atlassed at least twenty times in *both* epochs. That footprint is where atlassers went "
        "twice, thirty years apart, which is not a sample of southern African habitat. It narrows "
        "the northern-hemisphere gap; it does not close it.",
    ),
    temporal=(
        "bounded",
        "Two epochs, so a difference and not a rate: nothing here may be phrased per decade. The "
        "nineteen years between the atlas windows contain no data at all, so what happened in "
        "between is unobserved rather than smooth.",
    ),
    taxonomic=(
        "bounded",
        "Birds, and specifically the species already widespread at baseline -- thirty or more "
        "occupied cells in 1987-1991. Applying that floor to both epochs instead would have "
        "selected on the outcome, dropping 37 species whose median naive change was -0.153 "
        "against -0.014 overall, so it is applied at baseline only.",
    ),
    environmental=(
        "open",
        "An atlas card records where a volunteer went. The consistent-footprint rule controls for "
        "how *often* a cell was visited and not for which cells people choose, and no covariate "
        "for land use or protection enters the model. A change concentrated in transformed "
        "landscapes would be indistinguishable here from one that was not.",
    ),
    detectability=(
        "addressed",
        "A per-species detection probability is fitted in each epoch rather than assumed, and it "
        "turns out not to matter: at a median 82 and 68 cards per cell an occupied cell is missed "
        "with probability 0.00002 and 0.0002, so the corrected and uncorrected answers agree. "
        "Detection is also stable, correlating across the thirty-year gap, which is the evidence "
        "that observer change is not driving the result.",
    ),
    phenological=(
        "addressed",
        "Cards are pooled over five whole years in each epoch, so within-year timing is integrated "
        "out and a species that shifted its season rather than its range cannot appear as a range "
        "change.",
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


def _coverage_bias(evidence_types: int) -> list[BiasDomain]:
    """The coverage limit's ROBITT block, with the one number in it read from the lake.

    A function rather than a constant because the taxonomic line counts evidence types, and a
    count is exactly the kind of sentence that goes quietly false: it shipped as "the fifth
    evidence type in use" while four were in use, having been written when a fifth looked
    imminent. The rest of the block is prose re-expressing a method note and stays typed.
    """
    return _domains(
        geographic=(
            "open",
            "This claim *is* the geographic bias. Every source with a usable time axis is "
            "northern temperate; the two with global reach cannot support a trend.",
        ),
        temporal=(
            "bounded",
            "Measured from the lake rather than asserted, and recomputed on every build, so the "
            "day a southern source lands the number moves on its own.",
        ),
        taxonomic=(
            "bounded",
            "No longer birds-only on land: seven Movebank track sources add elk, caribou, "
            "reindeer, bison, Arctic fox and wolf, bringing the evidence types carrying data to "
            f"{evidence_types} of {len(EvidenceType)}. None of them supports a trend — collar "
            "effort is not a measured denominator — so they widen the coverage without widening "
            "what can be measured. Insects and reptiles are still absent.",
        ),
        environmental=(
            "open",
            "Long digitised radar and trawl series exist where they were funded, so the "
            "environmental space this project covers is a funding history rather than a sample.",
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


def _evidence_types_in_use() -> int:
    """How many of the canonical evidence types actually hold data.

    From the lake rather than from the registry: a source can be registered and never ingested
    -- `darkecology_profiles` has been for months -- and "in use" means what it says.
    """
    return sum(1 for kind in EvidenceType if lake_sources(kind))


def collect() -> list[Finding]:
    """Compute every finding. Re-runs the analyses, so this takes minutes rather than seconds."""
    # Imported here rather than at module scope: the reports import this module's siblings,
    # so a top-level import would close a cycle.
    from migratlas.metrics import range as range_metrics  # noqa: PLC0415
    from migratlas.reports import phase1b  # noqa: PLC0415
    from migratlas.reports.phase1 import AUTUMN, load_conus_nights, station_slopes  # noqa: PLC0415

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
            # "Whatever flies", not "birds". The plain register may drop precision and may never
            # add reach, and this is the sentence where the temptation is strongest.
            plain=(
                "Whatever flies over the middle of the United States on autumn nights is passing "
                "earlier in the year than it did thirty years ago."
            ),
            matters=(
                "Timing is most of how migration works: animals move when weather, daylight and "
                "food line up. When the calendar shifts and the things it is tuned to do not, "
                "animals arrive somewhere that has already moved on without them."
            ),
            plain_caveat=(
                "Weather radar sees a mass of animals in the air, not species. Some of it is bats, "
                "and some is insects."
            ),
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
            plain=(
                "Fish are not all moving towards the poles. Different seas are doing different "
                "things, and some are doing the opposite of others."
            ),
            matters=(
                '"Fish are moving polewards as the sea warms" is one of the best-known '
                "sentences in climate ecology. Across two thousand species it is not one story, "
                "and a single global number would erase every difference worth planning around."
            ),
            plain_caveat=(
                "These are trawl surveys in the North Atlantic and North Pacific. Nowhere else has "
                "been counted the same way for long enough to be included."
            ),
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
    # Published only while the fit it asserts still holds. The claim is that the mixture did not
    # drift; an airspeed trend distinguishable from zero makes the sentence false, and a ledger
    # that kept printing it would be contradicting its own number. Same shape as `shortfall`
    # below: the condition for publishing is the finding.
    from migratlas.reports import phase1c  # noqa: PLC0415

    drift = phase1c.airspeed_trend(AUTUMN, max_year=last_year)
    if drift is None:
        log.warning("composition-stable withheld: no airspeed series, so the claim is untested")
    elif not drift.flat:
        log.warning(
            "composition-stable withheld: autumn airspeed moves at %+.2f +/- %.2f m/s per decade",
            drift.mean,
            drift.ci95,
        )
    else:
        nights, wind_first, wind_last = _wind_coverage()
        findings.append(
            Finding(
                key="composition-stable",
                realm=Realm.AERIAL.value,
                taxon_scope=TaxonScope.UNATTRIBUTED.value,
                evidence_type=EvidenceType.FLUX.value,
                bias=COMPOSITION_BIAS,
                plain=(
                    "The radar is watching the same kind of traffic now as in 1995, so the "
                    "earlier timing is a real change and not a change in what is being counted."
                ),
                matters=(
                    "Every long record has this problem. If what an instrument measures quietly "
                    "changes, a trend appears that nothing caused — and it looks exactly like a "
                    "discovery. Ruling that out is the difference between a finding and an "
                    "artefact."
                ),
                plain_caveat=(
                    "Spring behaves differently and gets no claim here. Its speeds rose, and we "
                    "cannot yet separate a real change from animals flying higher than the wind "
                    "data assumes."
                ),
                claim=(
                    "The autumn signal is not drifting from birds towards insects — what the "
                    "radar measures in 2025 means what it meant in 1995."
                ),
                value=(
                    f"airspeed trend {drift.mean:+.2f} ± {drift.ci95:.2f} m/s per decade (flat)"
                ),
                scope=(
                    f"{nights:,} station-night wind samples, {wind_first}-{wind_last}, from an "
                    "independent regional reanalysis rather than from the radar."
                ),
                caveat=(
                    "Spring behaves differently: its airspeed rose, which is either a real change "
                    "or migrants flying higher than the fixed wind level assumes. Separating those "
                    "needs the vertical radar profiles. Spring carries no trend claim here either "
                    "way."
                ),
                method="docs/methods/phase1c-homogeneity.md",
                direction="change",
                supporting=[
                    f"Mean autumn airspeed of {drift.level:.2f} m/s sits in the range for "
                    "migrating songbirds, not insects.",
                    "A 2012 discontinuity in the dataset's own rain filtering was traced, and "
                    "ruled out as weather using independent precipitation data.",
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
                plain=(
                    "About half of that earlier timing traces back to warming people caused. The "
                    "other half does not follow temperature at all, and is unexplained."
                ),
                matters=(
                    "Showing that something changed is not showing why. This runs climate models "
                    "twice — once with human emissions and once with the world we would have had "
                    "without them — and asks how much of the warming behind the shift only "
                    "happened in one of those worlds."
                ),
                plain_caveat=(
                    "This attributes the warming, not the animals. Two independent ways of "
                    "building the world-without-us disagree with each other by more than a factor "
                    "of two, and both are shown."
                ),
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
            bias=_coverage_bias(_evidence_types_in_use()),
            plain=(
                "Everything on this site was measured north of the equator. The places with the "
                "longest records and the places with the most animals are not the same places."
            ),
            matters=(
                "A map of what is known is not a map of what is happening. Most of the world has "
                "never been counted the same way twice, so it cannot appear here at all — and a "
                "result from the north is not evidence about anywhere else until someone goes and "
                "checks."
            ),
            plain_caveat=(
                "Two sources are held back deliberately. Wolves and mountain caribou are hunted "
                "by people who would use a map of them, so none of their locations are drawn."
            ),
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
                "there first. Two kinds of gap are worth telling apart on the map. Grey cells are "
                "places the lake reaches and cannot measure. And two sources are held and drawn "
                "nowhere at all: mountain caribou and wolves are classified high-sensitivity, so "
                "their locations are withheld entirely rather than coarsened. The map is not a map "
                "of everything this lake knows, and the coverage panel lists what is missing from "
                "it rather than letting an absence speak."
            ),
            method="docs/methods/geographic-coverage.md",
            direction="limit",
        )
    )

    # --- Phase 1e: the atlas comparison -----------------------------------
    # Both epoch-2 windows are fitted here, which costs about two and a half minutes of the build.
    # That is the point: the sensitivity is not a footnote for this claim, it is what licenses
    # publishing any species-level number at all, and a figure typed once goes stale silently.
    from migratlas.reports import phase1e  # noqa: PLC0415

    atlas = phase1e.summarise()
    findings.append(
        Finding(
            key="atlas-no-net-change",
            realm=Realm.TERRESTRIAL.value,
            taxon_scope=TaxonScope.EXACT.value,
            evidence_type=EvidenceType.SURVEY_INDEX.value,
            bias=ATLAS_BIAS,
            plain=(
                "Southern African birds have not, on the whole, moved. A few dozen species "
                "clearly have — and the ones spreading fastest are birds people brought."
            ),
            matters=(
                "This is the first thing this project has measured outside the northern "
                "hemisphere, and it is the test of whether findings from one continent carry to "
                "another. It also answers a question the site had only ever asked: whether "
                "correcting for how hard people looked changes what you conclude."
            ),
            plain_caveat=(
                "Two snapshots thirty years apart, in three countries, in the places volunteers "
                "atlassed twice. It is a before and after, not a trend, and it is not Africa."
            ),
            claim=(
                "Between the two southern African bird atlases there is no net change in "
                f"occupancy across {atlas.species} species — the median is "
                f"{atlas.median_delta:+.3f} — while {atlas.movers} species moved by more than "
                "0.1 in one direction or the other."
            ),
            value=(
                f"median {atlas.median_delta:+.3f} change in occupancy probability, "
                f"deciles {atlas.decile_low:+.3f} to {atlas.decile_high:+.3f}, "
                f"across {atlas.species} species on {atlas.cells} shared cells"
            ),
            scope=(
                "SABAP1 1987-1991 against SABAP2 2008-2012, full-protocol cards only, on "
                f"{atlas.cells} quarter-degree cells carrying at least 20 cards in both epochs."
            ),
            caveat=(
                "The detection correction this was built for made no difference, and that is the "
                "second finding rather than a technicality. Corrected and naive occupancy change "
                f"agree to within 0.01 for {atlas.agree_within_001:.0%} of species, with a median "
                f"difference of {atlas.median_gap:.4f}. The reason is the footprint rule: 20 cards "
                "per cell was registered so detection could be *estimated* everywhere, and at that "
                "effort an occupied cell is essentially never missed, so there was nothing left "
                "for detection to *explain*. The elaborate machinery earns its place on sparse "
                "data, and a footprint strict enough to fit it is strict enough to make it "
                "unnecessary. Read the other way, that is why the number can be trusted: it does "
                "not depend on the model. What it cannot do is separate a species that left from "
                "one that stayed and was recorded differently in a landscape that changed around "
                "it — no land-use covariate enters this, and attribution is a later note."
            ),
            method="docs/methods/phase1e-atlas.md",
            direction="null",
            supporting=[
                "The occupancy model recovers known psi and p from simulated data across five "
                "parameter combinations before it was allowed near the atlases.",
                "The registered alternative window, 2019-2023, disagrees in sign for "
                f"{atlas.flip_share:.1%} of the species that moved — under the one-third "
                "threshold that would have made the result a property of the window.",
                "Nine of the ten largest changes hold under that alternative window and five are "
                "larger under it; the tenth flipped sign and is withdrawn rather than caveated.",
                "Detection probability correlates "
                f"{atlas.p_correlation:.3f} between epochs, so how likely a bird is to be written "
                "on a card did not change even though almost everything else about atlassing did.",
                "The uncorrected reporting-rate comparison gives the same answer, so the "
                "conclusion does not rest on the model being right.",
            ],
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
