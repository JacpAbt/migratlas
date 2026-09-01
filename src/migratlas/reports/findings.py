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
from typing import TYPE_CHECKING, Final, NamedTuple

import numpy as np
import polars as pl

from migratlas.evidence import EvidenceType, Realm, TaxonScope
from migratlas.lake.reader import scan, scan_dataset
from migratlas.lake.reader import sources as lake_sources

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)

SCHEMA_VERSION: Final = 4

# Enforced by a test rather than by trimming. A plain sentence that grows past this has become a
# second dense paragraph, and the reader who needed it has been lost twice.
PLAIN_MAX_CHARS: Final = 180

# How long a plain method may run before it has stopped being the thing it was added for. Longer
# than a plain sentence because a method is a sequence and a sequence needs clauses, and short
# enough that it cannot turn into the method note it stands in front of.
HOW_MAX_CHARS: Final = 620

# There is no character cap on the pages, and one was tried and refuted rather than not considered.
# `value`, `scope` and `caveat` share a page 826 pixels tall, and `web/tests/book.spec.ts` fails on
# three pixels of overflow -- twelve minutes after the fact, which is what made a cap attractive.
# The measurement says it cannot work: `anthropogenic-share` fits at 1,584 characters (821 pixels,
# five to spare) while `protocol-disagreement` overflowed at **1,573**, because three fields of
# different word lengths reflow into different numbers of lines. No threshold passes the first and
# fails the second, and a guard that cannot fail before the browser does is decoration. The browser
# guard is the authority; when it reports an overflow, move a sentence to a page with room rather
# than trimming words until the pixels agree.

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

    plain_how: str
    """How it was measured, for someone who will not open the method note. Always rendered.

    The owner's reading order is what we found, then *how we found it*, then a picture, then the
    numbers -- and this was the missing register. `method` is a path to a pre-registration and
    `caveat` is what would make the number wrong; neither of them tells a reader what was actually
    done, and a claim whose method is a filename is a claim asking to be taken on trust.

    Bound by the same rule as `plain`: it may drop precision and it may not add reach. It must
    describe the procedure that produced *this* value -- the instrument, the unit, the comparison --
    and it must not name a taxon the evidence cannot resolve, which is why the same creature check
    that guards the plain sentence guards this one.

    It also must not restate the figures. `value` and `scope` carry them, computed, and a count
    typed into a sentence here is a count that goes stale silently -- the defect this whole module
    re-runs the analysis to avoid.
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

    specimen_key: int | None = None
    """GBIF key of one animal whose own card is this claim's argument in miniature.

    None where no single animal carries it, which is most claims: a radar measurement has no
    animal to name, and naming one anyway would be the overclaim the plates rule refuses.
    """

    specimen: str = ""
    """The invitation the claim card prints on the way to that animal. Authored here, like all
    frontend prose, and empty exactly when `specimen_key` is None."""

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

DISPLACEMENT_BIAS: Final = _domains(
    geographic=(
        "bounded",
        "Two populations: elk of one Canadian mountain valley, reindeer of one Arctic "
        "archipelago. Chosen by who collared them, and nothing here speaks for anywhere else.",
    ),
    temporal=(
        "bounded",
        "Seventeen and thirteen years of animal-years, unevenly spread; six of the seventeen elk "
        "years rest on fewer than ten animals, short of the majority that would have stopped it.",
    ),
    taxonomic=(
        "addressed",
        "Two named populations of two named species. The claim reaches exactly that far, and "
        "the site draws these herds under the same names.",
    ),
    environmental=(
        "bounded",
        "A national-park elk range and a protected archipelago: managed landscapes, whose "
        "stability is part of what any flat trend includes.",
    ),
    detectability=(
        "addressed",
        "The confound is the finding: path length tracks the fix interval at rho -0.879 across a "
        "104-fold sampling change, and the displacement measure's independence was demonstrated "
        "by construction -- thin the track and the displacement must not move, and it does not.",
    ),
    phenological=(
        "open",
        "The season windows are fixed calendar blocks, so a herd that shifted *when* it moves "
        "rather than how far is invisible here -- the trade the method note makes explicitly, "
        "because timing is what Phase 1d proved a changing collar record cannot measure.",
    ),
)

PROTOCOL_BIAS: Final = _domains(
    geographic=(
        "bounded",
        "Sweden, and only Sweden. It is the one place in this lake where two independent "
        "programmes count the same populations, so it is the only place the question can be asked "
        "at all -- which is itself a fact about the holding rather than about birds.",
    ),
    temporal=(
        "addressed",
        "Both programmes restricted to their shared window, 1996-2024, before any slope was "
        "fitted. Window cannot contribute to the disagreement.",
    ),
    taxonomic=(
        "addressed",
        "Paired species by species. The comparison is one animal against itself, so the species "
        "mixture -- which is what made the first version of this diagnosis wrong -- cannot "
        "contribute either.",
    ),
    environmental=(
        "open",
        "Footprints still differ: 33 consistently sampled cells against 84. Part of the residual "
        "may be real geography rather than method, and restricting to shared cells is the "
        "successor's first job.",
    ),
    detectability=(
        "open",
        "This is a measurement *of* a detectability difference and cannot correct for one. A point "
        "count and a fixed route weight a species' detectability differently by construction; "
        "which of the two is closer to the truth is not answerable from the pair.",
    ),
    phenological=(
        "not applicable",
        "A latitude centroid over a breeding season carries no timing claim.",
    ),
)

FLIGHT_BIAS: Final = _domains(
    geographic=(
        "bounded",
        "The United Kingdom's transect network, 3,144 sites. A phenological response measured "
        "where volunteers walk, which is not a sample of anywhere else.",
    ),
    temporal=(
        "addressed",
        "1973-2021, and the unit qualifies only with fifteen years of its own. Long enough that a "
        "decadal rate is not an artefact of two endpoints.",
    ),
    taxonomic=(
        "bounded",
        "59 taxa, resolved to name, and the great majority resident. This is a flight-period "
        "response and not a migration timing shift -- the two are different behaviours and the "
        "claim is only about the first.",
    ),
    environmental=(
        "open",
        "No driver enters this. That the advance tracks warming is the literature's expectation "
        "and is not tested here, so the finding is a change and not an attribution.",
    ),
    detectability=(
        "addressed",
        "The estimand is a date, not an abundance, so no effort denominator is needed -- and the "
        "source carries none. A year with fewer visits gives a noisier date, not a biased one.",
    ),
    phenological=(
        "bounded",
        "Mean flight date is one summary of a flight period. A species whose season lengthened at "
        "one end without moving its centre would report no change here.",
    ),
)

SKILL_SPARSE_BIAS: Final = _domains(
    geographic=(
        "bounded",
        "The continental-US radar network, and only it: the one region on Earth with three "
        "decades of nightly aerial biomass at this density. Nothing here speaks for anywhere "
        "the instrument does not stand.",
    ),
    temporal=(
        "bounded",
        "One era split, fixed in advance: trained on the first seven-tenths of each station's "
        "years, tested once on the rest. Thirty-one years total, so the test era is roughly a "
        "decade and a station's verdict rests on five to ten test points.",
    ),
    taxonomic=(
        "addressed",
        "Deliberately unattributed: the radar measures aerial biomass, and a skill claim about "
        "'birds' would smuggle in the attribution Phase 1c refused.",
    ),
    environmental=(
        "bounded",
        "Seven covariates, fixed before any fit: season and pre-season temperature, season "
        "precipitation, and four climate modes. A driver outside that list -- wind fields, "
        "insect emergence, land use -- had no chance to show skill, and the claim is scoped to "
        "the list.",
    ),
    detectability=(
        "addressed",
        "The 2012 instrument step sits inside every station's training era, and the mode-only "
        "comparison (prediction 5) measures how much apparent skill is shared signal rather "
        "than local weather: +0.007 marginal against +0.018 solo where the modes already "
        "predict.",
    ),
    phenological=(
        "bounded",
        "The response is the season's median passage day through fixed calendar windows -- the "
        "same windows every phase uses, with the same blindness to a season that moves its "
        "own boundaries.",
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

TRANSFER_BIAS: Final = _domains(
    geographic=(
        "open",
        "Three places, so three points: a North American radar network, eighteen shelf-sea trawl "
        "surveys, and one southern African atlas footprint. Hemisphere, realm, instrument and "
        "decade all differ together and none of them can be held fixed. The two records that "
        "*agreed* are the ones on opposite sides of the equator, which is evidence against "
        "hemisphere being the axis that matters, and not evidence for any particular alternative.",
    ),
    temporal=(
        "bounded",
        "Each leg carries its own window -- 1995-2025 for the radar, the trawl surveys' own spans, "
        "and two five-year epochs thirty years apart in the south. A tracking ratio is a rate over "
        "a rate, so unequal windows do not make the units incomparable, but a realm sampled only "
        "either side of a gap cannot show what happened inside it.",
    ),
    taxonomic=(
        "open",
        "Unattributed biomass, marine species, and terrestrial birds. The comparison is between "
        "*records*, and no step establishes that the animals in them respond alike.",
    ),
    environmental=(
        "open",
        "Temperature only. Every leg divides by a thermal quantity and none carries land use, "
        "fishing pressure, wind or protection, so a realm whose animals were moved by something "
        "other than temperature reports that as a failure to track.",
    ),
    detectability=(
        "bounded",
        "Inherited from each leg rather than assessed again here, and they are not equally strong: "
        "the atlas leg fits a per-species detection probability in each epoch, the trawl leg has "
        "none, and the radar leg cannot identify an animal at all. A ratio cannot be more reliable "
        "than the shift in its numerator.",
    ),
    phenological=(
        "open",
        "This is the domain the result landed on. Two legs measure where an animal is and the "
        "third measures when it passes, and the conversion between them needs a seasonal "
        "temperature slope that a spatial leg never has to compute. The pre-registration's list of "
        "confounds did not name response type, and the correction is recorded in the method note "
        "rather than edited into it.",
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
            "This claim *is* the geographic bias, and it has moved without closing. Two atlases "
            "put a third of the time-series record south of the equator, in three countries; "
            "every other source with a usable time axis is northern temperate, the two with "
            "global reach cannot support a trend, and the driver record is northern but for water "
            "and temperature over those same atlas cells.",
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


SEAS_DISAGREE_BIAS: Final = _domains(
    geographic=(
        "bounded",
        "Eighteen shelf surveys of the North Atlantic and North Pacific. 0% southern hemisphere "
        "and 0% tropics, so this is a statement about northern shelf seas and not about the ocean.",
    ),
    temporal=(
        "addressed",
        "The unit is a survey's longest unbroken run under one gear, clipped to the satellite era, "
        "so no break term is needed anywhere: the segment is the break handling. A deterministic "
        "gear rule replaced one whose tie order was unstable between runs.",
    ),
    taxonomic=(
        "addressed",
        "Around 1,400 species-survey pairs summarised per survey by their median. The "
        "heterogeneity is measured between surveys, which is the level a pooled median destroys.",
    ),
    environmental=(
        "open",
        "The warming driver is a satellite reading the sea surface at a quarter degree, and these "
        "are bottom trawls. Where both waters exist they agree in direction at +0.216 across ten "
        "surveys, which is modest, and that correlation is the whole of what bounds the "
        "substitution.",
    ),
    detectability=(
        "bounded",
        "A trawl samples trawlable ground, and a survey that recorded no haul depth cannot enter "
        "the registered regression at all rather than being given a substituted depth.",
    ),
    phenological=(
        "bounded",
        "Surveys run in fixed seasons, so a species that shifted its timing rather than its "
        "position does not appear here.",
    ),
)


def _seas_finding() -> Finding | None:
    """Phase 3e's established result, owed to the ledger since the presentation arc closed.

    Two halves and the note calls them inseparable: the seas differ emphatically, and the
    thermometer does not sort which of them moved. Publishing either alone would be a different
    claim -- the heterogeneity without the null reads as "warming redistributes fish unevenly",
    and the null without the heterogeneity reads as "warming does nothing".
    """
    from migratlas.reports import phase3b, phase3e  # noqa: PLC0415 -- heavy, and only this claim

    fitted, coverage, calibration = phase3e.units_3e()
    if not calibration.passes or len(fitted) < phase3b.MIN_UNITS:
        return None
    fit = phase3b.regression(fitted)
    if not fit.heterogeneous:
        return None
    # ADR 0016, extended to Q by this phase because that ADR deferred it here. Q is a sum over
    # units, so one extreme sea could carry it exactly as one carried Phase 3g's slope -- and a
    # heterogeneity claim that rests on a single sea is a claim about that sea.
    if not fit.q_survives:
        log.warning("seas-disagree withheld: Q does not survive dropping one unit")
        return None

    return Finding(
        key="seas-disagree",
        plain_how=(
            "The same research trawls, cut a different way. Instead of asking how far fish moved "
            "on average, we asked whether the seas agree with each other at all — a formal test of "
            "whether eighteen surveys are one population with noise or genuinely different places. "
            "Then we asked whether the seas that warmed fastest were the seas whose fish moved "
            "furthest, using satellite temperature over each survey's own footprint."
        ),
        realm=Realm.MARINE.value,
        taxon_scope=TaxonScope.EXACT.value,
        evidence_type=EvidenceType.SURVEY_INDEX.value,
        bias=SEAS_DISAGREE_BIAS,
        plain=(
            "Different fish move differently, and that matters more than which sea they are in. "
            "How fast a sea warmed tells you almost nothing about whether its fish moved."
        ),
        matters=(
            "A single number for the ocean would erase this, and a single number is what a reader "
            "wants. But the useful half of the answer is which way to cut it: the animal explains "
            "far more than the place, so a plan made sea by sea is planning on the weaker axis. "
            "And the obvious explanation for who moved — whose water warmed most — is measured "
            "here and is not the answer."
        ),
        plain_caveat=(
            "This says the seas differ and that temperature alone does not sort them. It does not "
            "say what does. A warming that moved some kinds of fish and left others alone would "
            "look like this too, and that has not been tested yet."
        ),
        claim=(
            f"Across {fit.units} shelf-survey segments the latitude trends are heterogeneous far "
            f"beyond sampling — Cochran's Q {fit.q_statistic:.1f} against a chi-square bar of "
            f"{fit.q_bar:.1f} — while warming does not predict which segments moved: "
            f"{fit.temp_slope:+.3f} ± {fit.temp_ci:.3f} °latitude per °C, both per decade. Two "
            "things qualify that heterogeneity and both were measured after it was published: "
            "about 45% of it is the surveys' own stations having drifted, which takes Q to 131, "
            "and for the 297 species caught in three or more surveys the species explains 2.8 "
            "times what the survey does."
        ),
        value=(
            f"Q {fit.q_statistic:.1f} against a bar of {fit.q_bar:.1f} across {fit.units} "
            f"segments; warming {fit.temp_slope:+.3f} ± {fit.temp_ci:.3f} °lat per °C"
        ),
        scope=(
            f"{fit.units} bottom-trawl survey segments, each its longest unbroken run under one "
            f"gear clipped to the satellite era at twenty years or more, against a footprint-mean "
            f"satellite sea-surface temperature. {len(coverage)} surveys published as coverage "
            f"instead."
        ),
        caveat=(
            "The warming null is an average over units that emphatically disagree, so it rules out "
            "warming as the sorter *on this axis at this unit* and not as a driver: something that "
            "moved a third of the pairs and left the rest alone produces this number, and the "
            "cluster test for that has since run: cut into thirds by thermal position, warming "
            "rate and depth, no third of the pairs moved differently beyond its own null and no "
            "axis explained more than a twentieth of the variation, so the null is not hiding a "
            "subset along any axis this lake can define. The registered depth interaction came out "
            f"{fit.interaction_slope:+.3f} ± {fit.interaction_ci:.3f}, the opposite sign to the "
            "prediction, and is reported as the graded failure it is rather than turned around "
            "into a story. The driver is a satellite reading the surface where the fish are on the "
            "bottom, bounded only by the two waters agreeing in direction at "
            f"{calibration.correlation:+.3f} across {calibration.units} surveys. And a segment is "
            "shorter than its survey's record, so the most recent years of the longest series go "
            "unused by this design."
        ),
        method="docs/methods/phase3e-marine-oisst.md",
        direction="limit",
        supporting=[
            "The heterogeneity survives ADR 0016: dropping any one of the segments leaves Q above "
            "its own recomputed bar, so this is not one extreme sea carrying a statistic.",
            "It does not survive intact as a claim about oceans. Each survey's own mean haul "
            "latitude was trended with no fish in it, and it correlates with that survey's fish "
            "trend at +0.70 across eighteen surveys, with a slope near a half -- which is what an "
            "effort-weighted centroid should give if the stations move and the fish do not follow. "
            "Regressing it out takes Q from 236 to 131. The finding is smaller and it is about "
            "surveys rather than seas.",
            "The strongest explanatory axis in this project turned out to be sitting inside this "
            "source unexamined: grouped by species rather than by survey, the coherence is 0.430 "
            "against 0.156 -- higher than anything else measured here, and it says fish carry "
            "consistent movement tendencies across the seas they live in.",
            f"Its margin against the weights is narrower than that, and is stated rather than "
            f"left implicit: Q clears while each survey's interval is understated by less than "
            f"{fit.q_robustness:.2f} times. Those intervals treat the species inside a survey as "
            f"independent when they share its gear, footprint and water, and the comparable "
            f"corrections this project has measured elsewhere run 2.4 to 4.5 times. Nobody has "
            f"measured the factor for this quantity, so the honest position is that the "
            f"heterogeneity is large and its clearance is not comfortable.",
            "The warming null has no verdict for a single unit to overturn, and the furthest any "
            "one segment moves it leaves it a null as well.",
            "Five of five registered predictions were graded and two came back false, including "
            "the warming one this claim reports — the design was built to be able to say so.",
            "The satellite substitution was gated on a calibration fixed before any value was "
            "read: where a survey recorded its own water, the two had to agree in direction or "
            "nothing below was interpreted.",
            "An earlier version of this phase died on its own floor, with ten units against a "
            "registered twelve, because it required each survey to have recorded its own "
            "temperature. The salvage is what made eighteen possible and it is priced in the note.",
        ],
    )


PROJECTION_MASK_BIAS: Final = _domains(
    geographic=(
        "bounded",
        "The 78 radar stations between 37°N and 50°N, which is where the response function is "
        "published and nowhere else. Nothing here is projected outside that band, and the whole "
        "point of the claim is that a fitted line does not travel.",
    ),
    temporal=(
        "open",
        "Every model's anomaly is taken against its own 1995-2014 baseline, which ends where "
        "CMIP6's historical runs end. The response it multiplies was fitted over 1995-2025, so the "
        "two windows do not coincide and the ratio construction is what makes that tolerable.",
    ),
    taxonomic=(
        "open",
        "The response is aerial reflectivity, which cannot tell a bird from a bat from an insect. "
        "A projection inherits that whole and adds nothing to it.",
    ),
    environmental=(
        "open",
        "Wind, land use, light and the unexplained half of the observed advance are all held at no "
        "change, which is a claim about the future and not a neutral choice.",
    ),
    detectability=(
        "addressed",
        "Every row carries whether that station has any interannual skill at all, because a "
        "scenario response read forwards is not a year-ahead forecast and a reader who confuses "
        "them has been misled by presentation.",
    ),
    phenological=(
        "bounded",
        "The response is a passage date, so this projects timing and nothing about abundance, "
        "route or destination.",
    ),
)


def _projection_finding() -> Finding | None:
    """Forecast A's deliverable, which is the mask and never the shift.

    The note's own closing words: *"a successor should also consider reporting the sayable share as
    the headline number rather than any shift."* Done here, and the reason is arithmetic -- masking
    keeps exactly the cells bunched against the envelope's upper edge, so the median sayable shift
    sits near a day in every scenario at every horizon. Four scenarios differing by four degrees of
    warming cannot imply the same shift; what they share is the edge of the mask.
    """
    from migratlas.reports import forecast_a  # noqa: PLC0415 -- heavy, and only this claim

    read = forecast_a.mask()
    if read is None:
        return None

    return Finding(
        key="projection-mask",
        plain_how=(
            "No new measurement and no model of our own. The relationship between a warm "
            "pre-season and an earlier passage was already fitted from thirty years of "
            "observations, over a range of temperatures those thirty years actually contained. We "
            "took published climate projections, asked how much warmer each scenario makes each "
            "station's pre-season, and then asked the only question that matters: is that warming "
            "inside the range the relationship was measured over? Where it is not, nothing is "
            "drawn."
        ),
        realm=Realm.AERIAL.value,
        taxon_scope=TaxonScope.UNATTRIBUTED.value,
        evidence_type=EvidenceType.FLUX.value,
        bias=PROJECTION_MASK_BIAS,
        plain=(
            "Under strong mitigation, about half these places stay inside the range we measured. "
            "Under every other scenario the warming runs off the end of it, and there we decline "
            "to guess."
        ),
        matters=(
            "A projection three degrees outside the range it was fitted in is not a cautious "
            "estimate. It is arithmetic wearing the clothes of evidence, and it is the single "
            "commonest way this kind of forecasting goes wrong. Publishing where the answer runs "
            "out is the result here, and it is a smaller map than anyone wants."
        ),
        plain_caveat=(
            "This projects only the part of the timing shift that follows temperature, which is "
            "about half of it. And it is not a forecast for any particular year — a response read "
            "forwards under a scenario and a prediction of next autumn are different things."
        ),
        claim=(
            f"Of the scenario-and-horizon frames projected across {read.stations} stations in the "
            f"claim band, {read.unsayable} of {read.total_frames} have nothing sayable in them at "
            f"all: the multi-model median warming reaches {read.worst_delta:+.2f} °C against a "
            f"fitted envelope whose upper bound is {read.envelope_high:+.2f} °C. The best-covered "
            f"frame is {read.best_scenario} at {read.best_window}, sayable at "
            f"{read.best_share:.0%} of stations, and the largest sayable shift anywhere is "
            f"{read.largest_shift:.2f} days per the fitted response."
        ),
        value=(
            f"{read.best_share:.0%} sayable at best ({read.best_scenario}, {read.best_window}); "
            f"{read.unsayable} of {read.total_frames} frames entirely unsayable"
        ),
        scope=(
            f"{read.stations} radar stations between 37°N and 50°N, four SSPs and two twenty-year "
            "windows, each model's June-July anomaly against its own 1995-2014 baseline, masked "
            "against the 5th-to-95th band of the within-station departures the response was fitted "
            "over."
        ),
        caveat=(
            "The number a reader will reach for is the projected shift, and it is the one number "
            "here that misleads: masking removes every cell warmer than the envelope's edge, so "
            "the surviving cells are bunched against that edge and the median sayable shift sits "
            "near a day in every scenario at every horizon. Four scenarios that differ by four "
            "degrees of warming cannot imply the same shift — what they share is the mask. Read it "
            "as a bound on the thermal component, never as an expectation. That component is also "
            "only about half of the observed advance and the response behind it can be fitted on "
            "two timescales, so it carries its own range before any scenario is applied. Nothing "
            "here says the response stays linear outside the band, which is exactly what the mask "
            "declines to assert, and the model spread is wider than the response's own interval — "
            "which model you pick matters more than how well the response is known. And this is "
            "not a year-ahead forecast: interannual skill is absent at most of these stations, and "
            "a standing annual prediction was tested and refused on measured grounds."
        ),
        method="docs/methods/forecast-a.md",
        direction="limit",
        supporting=[
            "The mask was applied before any projected value was reported, not after inspecting "
            "them, and the envelope, the windows, the member cap and the baseline were all fixed "
            "before a single scenario store was opened.",
            "Four of five registered predictions held. The one that failed was the mid-century "
            "share under strong mitigation, short of a bar chosen for its roundness by one "
            "station, and it is recorded as false rather than rounded up.",
            "The response function is read from the published fit rather than re-estimated here, "
            "so the projection and the ledger cannot disagree about the coefficient they share.",
            "Every projected row carries whether its station has any interannual skill at all, "
            "because a scenario response and a year-ahead forecast are different objects and the "
            "difference is presentation's responsibility.",
        ],
    )


def _optional(finding: Finding | None, *, withheld: str) -> list[Finding]:
    """One finding, or none with the reason logged.

    Three claims are conditional on their own data clearing a registered floor, and each wrote the
    same four lines. A withheld finding must leave a trace -- silence is how a claim disappears
    without anybody deciding to drop it.
    """
    if finding is not None:
        return [finding]
    log.warning(withheld)
    return []


def _idle_network_findings() -> list[Finding]:
    """Phase 1k and 1l's publishable half, which is not the half that was expected.

    1l's stop condition fired -- two protocols disagree about one species more than species disagree
    with each other -- so 1k's three latitude medians are withheld and the bound 1l measured stands
    in their place. The butterfly timing leg makes no cross-network comparison and is unaffected.

    Its own function rather than eight statements in `collect`, which was already at its limit.
    """
    return [
        *_optional(
            _protocol_finding(),
            withheld="protocol-disagreement withheld: the paired panel fell below its floor",
        ),
        *_optional(
            _flight_finding(),
            withheld="flight-advance withheld: no series cleared the registered floor",
        ),
        *_optional(
            _seas_finding(),
            withheld=(
                "seas-disagree withheld: the calibration, the unit floor or the heterogeneity "
                "test did not hold"
            ),
        ),
        *_optional(
            _projection_finding(),
            withheld="projection-mask withheld: no scenario frame carried a station",
        ),
    ]


def _protocol_finding() -> Finding | None:
    """The bound Phase 1l measured on this project's own comparative method.

    Published because Phase 1l's stop condition fired: its ratio came back above 1, so Phase 1k's
    three latitude medians are withheld and this is what stands in their place. A project that
    compares realms, legs and networks has to publish what it measured about the reliability of
    comparing.
    """
    from migratlas.reports import phase1l  # noqa: PLC0415 -- heavy, and only this claim

    paired = phase1l.paired()
    split = phase1l.decompose()
    if paired is None or split is None:
        return None

    noise = 100.0 * split.noise_share
    corrected = (
        split.method_sd / split.species_sd
        if split.method_sd is not None and split.species_sd
        else float("nan")
    )
    return Finding(
        key="protocol-disagreement",
        realm=Realm.TERRESTRIAL.value,
        taxon_scope=TaxonScope.EXACT.value,
        evidence_type=EvidenceType.SURVEY_INDEX.value,
        bias=PROTOCOL_BIAS,
        plain=(
            "Two bird surveys counting the same species often disagree about which way it is "
            "moving, and mostly because neither can measure one species precisely enough to tell."
        ),
        matters=(
            "Almost everything on this site is a comparison: one place against another, one kind "
            "of animal against another, one method against another. All of it assumes that how "
            "you counted matters less than what you counted. Here that assumption was tested for "
            "the first time and it did not hold -- the two matter about equally. The useful half "
            "of the answer is why: a single species counted by a single programme is too faint a "
            "signal to compare, which is a reason to read the pages that follow as being about "
            "many animals at once rather than about any one of them."
        ),
        plain_caveat=(
            "This is one country and one kind of survey. It does not prove the same is true of "
            "radar or of fishing nets, and it cannot say which of the two surveys is closer to "
            "right. Averaging species together makes each reading sharper without bringing the "
            "two surveys any closer, so the disagreement is not something more counting fixes."
        ),
        plain_how=(
            "Sweden runs two independent bird-counting programmes side by side. We took every "
            "species counted by both, cut the records back to the years the two share, and worked "
            "out how far north that species had moved according to each one. Then we compared the "
            "two answers for the same animal, so that differences between species could not be "
            "the explanation, and asked whether the gap between methods was smaller or larger "
            "than the gap between species."
        ),
        claim=(
            f"On the one population pair this lake can check, between-protocol disagreement in a "
            f"species' latitudinal trend is comparable to between-species dispersion once each "
            f"side's own estimation error is removed from both: {corrected:.2f} to one. Only "
            f"{noise:.0f}% of the raw paired disagreement is that error, so most of what "
            f"separates the two programmes is a real difference in what they measure rather than "
            f"noise in how well they measure it."
        ),
        value=(
            f"method-to-species scatter {corrected:.2f}x, estimation error removed from both; "
            f"{noise:.0f}% of the raw disagreement is that error"
        ),
        scope=(
            f"Two Swedish bird programmes, {paired.shared_years[0]}-{paired.shared_years[1]}, "
            f"{paired.species} species qualifying in both at twenty years each, paired species by "
            f"species with the window held common, of which {split.species} carry a standard "
            f"error on both sides and enter the decomposition."
        ),
        caveat=(
            f"The two readings a paired difference allows have been separated rather than left "
            f"open, from the standard errors the fits were already computing: {noise:.0f}% of the "
            f"raw disagreement is the two fits' own estimation error, so the remainder is a real "
            f"difference in what the programmes measure. It is not geography: matching the two "
            f"footprints cell for cell leaves the ratio where it was, because the smaller "
            f"programme's cells turn out to be 97% nested inside the larger one's rather than "
            f"beside them. And the remainder is a constant offset -- point counts read about a "
            f"sixth of a degree per decade more northward movement than fixed routes, by the same "
            f"amount whether a species is easy to count or hard, northern or southern. The sign "
            f"disagreements are softer than they read: {split.flips_explained} of "
            f"{split.flips} involve at least one estimate that cannot be told apart from zero, "
            f"which two weak readings of a near-zero trend do as a matter of course. The reason "
            f"is in the third figure: a median species trend here is "
            f"{split.slope_vs_stderr:.2f} standard errors from zero, short of the two a single "
            f"estimate needs, so these networks do not measure one species' movement precisely "
            f"enough to compare. And agreement would have licensed comparison, never accuracy -- "
            f"two programmes in one country can share a bias and agree while both are wrong."
        ),
        method="docs/methods/phase1l-paired-protocols.md",
        direction="limit",
        supporting=[
            "The pairing was run because an earlier version of this diagnosis compared two "
            "network averages over different species mixtures, which is the error it was warning "
            "about; removing the mixture made the disagreement larger rather than smaller.",
            "Two of the phase's four registered predictions were graded false, and they fired "
            "the stop condition that withholds the distribution results this claim replaces.",
            "A successor grouped the same species by where they live and recomputed the ratio "
            "with groups as the unit, which is how a difference that averages away is told from "
            "one that does not. It did not move, so the remainder is systematic rather than "
            "species-specific -- the more serious of the two possibilities, and the reason the "
            "withholding stands on firmer ground than when it fired.",
            "The window was made common before any slope was fitted, so the disagreement is not "
            "two programmes describing two different periods.",
            f"The headline moved in the correcting, and the earlier figure is kept here rather "
            f"than replaced quietly: {paired.ratio:.2f} compared interquartile ranges with both "
            f"sides' estimation error left in, and {corrected:.2f} compares standard deviations "
            f"with that error removed from each. Two changes at once, so the fall is not "
            f"attributable to the correction alone.",
        ],
    )


def _flight_finding() -> Finding | None:
    """The largest timing signal in this lake, and the first from an insect series.

    The comparison to the radar is published only while the flight curve's *shape* is flat. That is
    Phase 1j's prediction 6, whose registered consequence is that a shape trend withdraws the
    comparison rather than caveating it. The reason is that the two records summarise their season
    differently -- a count-weighted mean here against a traffic-weighted median there -- so a
    constant offset between them cancels in a ratio of trends and only a trend in the shape can
    bias it. The standalone advance is unaffected either way and keeps its own sentence.
    """
    from migratlas.reports import phase1k  # noqa: PLC0415 -- heavy, and only this claim

    flight = phase1k.timing()
    if flight is None:
        return None

    published_width = flight.interval[1] - flight.interval[0]
    widening = (flight.widest[1] - flight.widest[0]) / published_width if published_width else 1.0
    shape = phase1k.flight_shape()
    moved = [trend for trend in shape if not trend.flat]
    # An unevaluated guard is not a guard that passed: with no shape series the comparison is
    # unlicensed, which is the direction the registration points.
    licensed = bool(shape) and not moved

    comparison = ""
    guard = ""
    if licensed:
        radar, _ = phase1k.calibrate_timing()
        ratio = abs(flight.median / radar) if radar else float("nan")
        # The plain sentence says "nearly four times" in words, as every plain sentence here is
        # worded rather than numbered. A word is still a published figure, so it is published only
        # while the recomputed ratio is one the word describes -- the README status line and
        # `coverage-bias` were both wrong for days because a figure was typed once.
        verbal_low, verbal_high = 3.5, 4.5
        if verbal_low <= ratio <= verbal_high:
            comparison = " and the shift is nearly four times the one measured in the night sky"
        else:
            log.warning(
                "flight-advance: the radar ratio is %.2f, which 'nearly four times' no longer "
                "describes, so the plain sentence drops the comparison",
                ratio,
            )
        guard = (
            " That ratio rests on a guard graded before it was quoted: a mean and a median are "
            "commensurable only while the curve's shape holds still, and neither measure of it "
            "moved."
        )
        supporting_comparison = (
            f"The advance is {ratio:.1f} times the radar's autumn slope, recomputed from the lake "
            f"rather than quoted, and Phase 1j's registered guard on the comparison holds: "
            f"{'; '.join(trend.label for trend in shape)}."
        )
    else:
        guard = (
            " No ratio between the two is published: a mean and a median are commensurable only "
            "while the curve's shape holds still, and it did not. Withdrawing rather than "
            "caveating is Phase 1j's registered consequence."
        )
        supporting_comparison = (
            "The comparison to the radar is withheld, and by a condition registered in Phase 1j "
            "before either number existed. What moved: "
            + (
                "; ".join(trend.label for trend in moved)
                if moved
                else "nothing measurable -- the shape series is unavailable, so the guard could "
                "not be evaluated at all"
            )
            + ". The interval resamples units as if independent, so it is if anything too tight -- "
            "which withholds more than a wider one would, and is the safe direction for a guard."
        )

    return Finding(
        key="flight-advance",
        realm=Realm.TERRESTRIAL.value,
        taxon_scope=TaxonScope.EXACT.value,
        evidence_type=EvidenceType.SURVEY_INDEX.value,
        bias=FLIGHT_BIAS,
        plain=(f"British butterflies are flying about two days earlier every decade{comparison}."),
        matters=(
            "Timing is where a warming year shows up first. This is the same question the radar "
            "answers over North America, asked of a completely different kind of animal with a "
            "completely different instrument, on a panel eighty times bigger."
        ),
        plain_caveat=(
            "Most of these are butterflies that stay put, so this is when they emerge rather than "
            "when they travel. It is one country, and it is volunteers walking transects."
        ),
        plain_how=(
            "Volunteers have walked the same transects in Britain since the scheme began, "
            "recording what they see. For each species at each site, the scheme records the middle "
            "of its flight period, and we asked whether that date has moved -- one straight line "
            "per site-species series, and only where fifteen years of it exist. Every series was "
            "also compared against itself with the years shuffled, so a series only counts if it "
            "beats its own noise."
        ),
        claim=(
            f"Mean flight date across UK monitoring transects has advanced by "
            f"{abs(flight.median):.2f} days per decade (median across {flight.units:,} "
            f"site-species-generation series, 95% CI "
            f"{flight.widest[0]:+.2f} to {flight.widest[1]:+.2f} with taxa resampled rather than "
            f"series), with {flight.significant:,} series beating their own year-shuffle null "
            f"against a chance bar of {flight.bar:,}."
        ),
        value=(
            f"{flight.median:+.2f} days per decade across {flight.units:,} series "
            f"(IQR {flight.iqr[0]:+.1f} to {flight.iqr[1]:+.1f})"
        ),
        scope=(
            f"UK Butterfly Monitoring Scheme transects, 1973-2021, {flight.units:,} "
            "site-species-generation series clearing fifteen years each, split generations kept "
            "apart from pooled-brood rows."
        ),
        caveat=(
            "The median hides a spread that is wider than itself: the interquartile range runs "
            f"{flight.iqr[0]:+.1f} to {flight.iqr[1]:+.1f} days per decade, so a substantial "
            "minority of series are flying later, and this is a summary of series doing different "
            "things rather than one behaviour. No driver enters the fit, so it is a change and not "
            "an attribution -- that warming is the cause is the literature's expectation and is "
            "untested here. A mean flight date is one summary of a flight period, and a species "
            "whose season lengthened at one end without moving its centre reports nothing. And a "
            "flight period is not a migration: the comparison to nocturnal passage is a comparison "
            f"of thermal tracking, not of the same behaviour. No individual series is readable "
            f"here: the median one sits {flight.slope_vs_stderr:.2f} standard errors from zero, "
            f"short of the two a single estimate needs, so this is a statement about a network and "
            f"never about a site or a species.{guard}"
        ),
        method="docs/methods/phase1k-idle-networks.md",
        direction="change",
        supporting=[
            "The phase's estimator reproduced two of this project's published numbers before "
            "touching a new source -- the marine median to three significant figures and the "
            "aerial slope to two -- by calling those reports rather than a copy of them.",
            supporting_comparison,
            "The estimand had to be reconstructed because the lake stores no flight date, and the "
            "first implementation fitted the wrong quantity; the correction is recorded in the "
            "method note rather than edited away.",
            f"The interval published here is {widening:.1f} times the one a resample over series "
            f"gives, and it is the wider of two clusterings rather than the convenient one: "
            f"{flight.units:,} series rest on {flight.taxa} taxa and one national spring, so "
            f"treating them as independent was the error. Registered as a prediction before it was "
            f"measured, and it came in above the bracket's floor.",
        ],
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


# Every evidence type that carries a time axis, and the column its positions live in.
#
# The previous version of this hardcoded a list of two *sources* while computing their shares from
# the lake, and its docstring named the exact failure it then suffered: "the day a southern source
# lands, a hardcoded 0% would be a lie on the site." SABAP1 and SABAP2 landed on 2026-07-30 and the
# site went on publishing 0.0% southern over 19.7 million southern rows.
#
# So the sources are enumerated and only the *types* are named -- and a type holding data that
# appears in neither map stops the build rather than being skipped.
TIME_AXIS: Final = {
    EvidenceType.FLUX: "station_latitude",
    EvidenceType.SURVEY_INDEX: "site_latitude",
    EvidenceType.TRACK: "latitude",
}

# Pooled over their whole period, so they cannot measure change and are not part of this claim.
POOLED: Final = frozenset({EvidenceType.ABUNDANCE_SURFACE})


@dataclass(frozen=True, slots=True)
class Coverage:
    """How much of what this project can measure change with lies south of the equator."""

    rows: int
    southern: int
    sources: int
    southern_sources: int
    driver_rows: int
    southern_drivers: int

    @property
    def share(self) -> float:
        return self.southern / self.rows if self.rows else float("nan")

    @property
    def driver_share(self) -> float:
        return self.southern_drivers / self.driver_rows if self.driver_rows else float("nan")


def _coverage() -> Coverage:
    """Count the southern share of the lake's time-series record, and of its drivers.

    Two numbers rather than one, and the gap between them is the finding now. Evidence and drivers
    moved apart when the atlases landed: a third of the rows this project can measure change with
    are southern, and none of the temperature it would explain them with is.
    """
    live = [kind for kind in EvidenceType if lake_sources(kind)]
    unhandled = [kind for kind in live if kind not in TIME_AXIS and kind not in POOLED]
    if unhandled:
        msg = (
            f"{[str(kind) for kind in unhandled]} hold data and this claim does not know whether "
            f"they carry a time axis or where their positions live. Decide, and add them to "
            f"TIME_AXIS or POOLED -- skipping one is how this went on reporting 0% southern."
        )
        raise ValueError(msg)

    rows = southern = sources = southern_sources = 0
    for kind, column in TIME_AXIS.items():
        for source in sorted(lake_sources(kind)):
            values = (
                scan(kind, source_id=source).select(lat=pl.col(column)).collect()["lat"].to_numpy()
            )
            below = int((values < 0).sum())
            rows += int(values.size)
            southern += below
            sources += 1
            southern_sources += 1 if below else 0

    drivers = (
        scan_dataset("driver_samples", source_id=None).select(lat=pl.col("latitude")).collect()
    )
    latitudes = drivers["lat"].to_numpy()
    return Coverage(
        rows=rows,
        southern=southern,
        sources=sources,
        southern_sources=southern_sources,
        driver_rows=int(latitudes.size),
        southern_drivers=int((latitudes < 0).sum()),
    )


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


class Timescale(NamedTuple):
    """The three pieces of prose the timescale bracket contributes to the attribution claim."""

    share: str
    """Appended to `value`: the bracket as a percentage range, or empty."""
    caveat: str
    """Appended to the caveat: why the share is a range and why it cannot be narrowed."""
    supporting: str
    """A supporting line, whether or not the check could run."""


def _timescale(sensitivity: float, ensemble: float) -> Timescale:
    """Bracket the attributed share over the two timescales the response can be fitted on.

    The published response function carries no time term, so it absorbs the shared trend of passage
    date and temperature and reproduces part of the advance by construction. Phase 2c refits with
    one; the ledger carries both ends rather than the end that happens to be published.
    """
    from migratlas.reports import phase2c  # noqa: PLC0415 -- heavy, and only this claim

    timescale = phase2c.bracket()
    if timescale is None:
        log.warning("anthropogenic-share: no timescale bracket, so the share is published as one")
        return Timescale(
            share="",
            caveat="",
            supporting=(
                "The response function's timescale could not be checked on this build, so the "
                "share is published as a point estimate rather than as the range it should be."
            ),
        )

    low = ensemble * timescale.low
    high = ensemble * timescale.high
    moved = abs(sensitivity - timescale.interannual) / timescale.interannual_ci
    return Timescale(
        share=f", {low:.0%}-{high:.0%} of it",
        # Short on purpose, and the coefficients live in `supporting` rather than here. The record
        # page carrying value, scope and caveat overflowed by 43px with them in it, and the fix is
        # the one the last overrun taught: move the sentence to a page with room rather than trim
        # words until the pixels agree.
        caveat=(
            " The share is a range because the response can be fitted on two timescales and this "
            "record cannot choose between them."
        ),
        supporting=(
            f"The response function was refitted with a time term in it, because without one it "
            f"absorbs the shared trend of passage date and temperature and would reproduce part of "
            f"the advance by construction. Adding one moves the sensitivity from "
            f"{sensitivity:+.3f} to {timescale.interannual:+.3f} days per °C across "
            f"{timescale.units} stations — "
            f"{moved:.2f} of its own interval — and the attributed share from {high:.0%} to "
            f"{low:.0%}. That is why this number survived the check rather than being withdrawn. "
            f"The record cannot narrow the range further: a response acting over decades and a "
            f"non-thermal process that trends the same way are the same column of that design "
            f"matrix."
        ),
    )


def collect() -> list[Finding]:
    """Compute every finding. Re-runs the analyses, so this takes minutes rather than seconds."""
    # Imported here rather than at module scope: the reports import this module's siblings,
    # so a top-level import would close a cycle.
    from migratlas.metrics import range as range_metrics  # noqa: PLC0415
    from migratlas.reports import phase1b  # noqa: PLC0415
    from migratlas.reports.phase1 import AUTUMN  # noqa: PLC0415

    _, first_year, last_year = _radar_coverage()
    coverage = _coverage()

    findings: list[Finding] = []

    # --- The headline -------------------------------------------------------
    findings.append(_autumn_advance(first_year, last_year))

    # --- The null that matters just as much --------------------------------
    # Through the same three steps `phase1b.render` uses, in the same order: the survey unit has
    # to be recovered from the site id before cells are formed, or `analyse` has nothing to group
    # by. Calling the report's own functions rather than restating them is the point -- a second
    # copy of the data preparation is a second thing that can drift from the published method.
    _, pooled, _ = phase1b.analyse(range_metrics.to_cells(phase1b.survey_unit(phase1b.load())))
    shift = pooled["per_decade"].to_numpy().astype(float)
    exemplar = _two_way_specimen(pooled)
    findings.append(
        Finding(
            key="marine-null",
            plain_how=(
                "Government research ships have been dragging the same nets over the same "
                "seabed for decades. For each species in each survey we followed the middle of "
                "where it was caught, year by year, and fitted how fast that middle was moving "
                "north or south. Then we looked at all of those fits together instead of "
                "collapsing them into one — the disagreement between them is the result."
            ),
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
                "analysis has to be the species in its region, not the ocean. And this null was "
                "tested for a mixture rather than left as an average: cut into thirds by where a "
                "species sits in its own survey's water, by how fast that water warmed, and by how "
                "deep it lives, no third moved differently from the others beyond what shuffling "
                "the labels produces, and no grouping explained more than a twentieth of the "
                "variation between pairs. A warming that hit some and spared the rest would look "
                "like this median, and along these three axes it is not what is here. What does "
                "carry the spread is the animal: for the 297 species caught in three or more of "
                "these surveys, grouping by species explains 2.8 times what grouping by survey "
                "does, so a fish's movement tendency travels with it between seas better than any "
                "property of the water tested here."
            ),
            method="docs/methods/phase1b-marine.md",
            direction="null",
            specimen_key=exemplar[0] if exemplar else None,
            specimen=(
                f"{exemplar[1]} went north in one survey and south in another. Watch it happen."
                if exemplar
                else ""
            ),
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
                plain_how=(
                    "If a different mix of animals had taken over the night sky, it would fly "
                    "at a different speed. The radar gives speed over the ground, and a "
                    "separate weather record gives the wind on that night at that place; taking "
                    "one from the other leaves how fast the animals were flying through the "
                    "air. That figure has not moved, which is what makes the earlier passage a "
                    "change in timing rather than a change in who is passing."
                ),
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
        from migratlas.reports import phase2a_attrici  # noqa: PLC0415 -- heavy, and only here

        timescale = _timescale(seen.sensitivity, primary.ensemble)
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
                plain_how=(
                    "Climate models can be run twice: once with the last century as it "
                    "happened, and once with human emissions taken out of it. We sampled both "
                    "runs at the same radar stations and over the same years, put each one's "
                    "temperature through the relationship between warmth and passage date that "
                    "the observations themselves fitted, and took the difference. What is left "
                    "is the part of the shift a world without us does not produce."
                ),
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
                value=(
                    f"{days:+.2f} days per decade of the {seen.advance:+.2f} observed"
                    f"{timescale.share}"
                ),
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
                    + timescale.caveat
                    + variability
                ),
                method="docs/methods/phase2a-attribution.md",
                direction="change",
                supporting=[
                    timescale.supporting,
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
            plain_how=(
                "No new measurement — a count of what this project holds. Every source with a "
                "time axis was tallied by hemisphere, separating the records that describe "
                "animals from the records of weather and vegetation used to explain them. The "
                "two shares are nothing like each other, and that gap bounds every question "
                "that needs both halves at once."
            ),
            # Every realm at once, so the field names the whole lake rather than picking one.
            realm="all",
            taxon_scope="all",
            evidence_type="all",
            bias=_coverage_bias(_evidence_types_in_use()),
            plain=(
                "A third of what this site measures is now southern, and none of the weather "
                "that would explain it is. Describing a place and explaining it are different "
                "problems."
            ),
            matters=(
                "A map of what is known is not a map of what is happening. Most of the world has "
                "never been counted the same way twice — and where it has, the records that would "
                "say *why* often still do not reach. A result from one hemisphere is not evidence "
                "about the other until someone goes and checks."
            ),
            plain_caveat=(
                "Two sources are held back deliberately. Wolves and mountain caribou are hunted "
                "by people who would use a map of them, so none of their locations are drawn."
            ),
            claim=(
                f"{coverage.share:.1%} of the rows this project can measure change with lie south "
                f"of the equator, from {coverage.southern_sources} of {coverage.sources} sources "
                f"— and {coverage.driver_share:.2%} of its driver record does. The evidence has "
                "crossed the equator and the data that would explain it has barely started."
            ),
            value=(
                f"{coverage.southern:,} of {coverage.rows:,} time-series rows are southern "
                f"({coverage.share:.1%}), against {coverage.southern_drivers:,} of "
                f"{coverage.driver_rows:,} driver samples ({coverage.driver_share:.2%})"
            ),
            scope="Every source in this project that has a usable time axis.",
            caveat=(
                "The southern share is two bird atlases in three countries, so it is a large "
                "number from a small place and not coverage of a hemisphere. What has not moved "
                "has barely moved is the driver record, and what little of it is southern arrived "
                "only to answer this. Every wind field and every counterfactual in this lake was "
                "taken over North America; the southern share is surface water and monthly "
                "temperature over one atlas footprint, fetched for two five-year windows thirty "
                "years apart. That is enough to ask whether those birds tracked the warming and "
                "nothing like enough to explain them: no wind, no counterfactual, and nineteen "
                "unobserved years in the middle. Inherited rather than chosen — long digitised "
                "radar and trawl series exist where they were funded — but no model trained on "
                "this should be trusted elsewhere without being tested "
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
            plain_how=(
                "Two atlases thirty years apart, built from the same kind of volunteer "
                "checklist in the same map squares. Volunteers looked far harder the second "
                "time, so raw counts would measure the volunteers rather than the birds: "
                "instead we asked, for each species in each square, how likely a full day's "
                "card was to record it, and only in squares visited enough in both periods. "
                "Those probabilities are what we compared."
            ),
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
                # The map under this claim is the uncorrected surface, and the caveat above says
                # the two agree -- both true, at different scales, which the site has to say
                # rather than leave a reader to reconcile.
                "Per cell they agree less well, which is why the map beside this claim draws the "
                "uncorrected count: a disagreement of a fraction of one species, summed over five "
                "hundred of them, is a few whole species in a cell. That the map is the plainer "
                "measurement was fixed in advance, in docs/methods/phase1f-atlas-surface.md, as "
                "what to do if the two ever parted.",
            ],
        )
    )

    findings.append(_skill_finding())

    findings.extend(_idle_network_findings())

    findings.extend(
        _optional(
            _displacement_finding(),
            withheld="displacement-flat withheld: the escape correlation exceeded its bar",
        )
    )

    # --- Phase 1i: does any of this transfer? -----------------------------
    # The slowest entry in the build by a wide margin: it re-runs all three legs, and two of them
    # are whole analyses that already ran above. Kept whole rather than cached because the claim is
    # a comparison between them, and a comparison assembled from three separately-cached numbers is
    # exactly the figure that goes stale without anyone noticing.
    from migratlas.reports import phase1i  # noqa: PLC0415

    transfer = phase1i.summarise()
    by_realm = {leg.realm: leg for leg in transfer.legs}
    agreed = transfer.indistinguishable
    worst = transfer.worst

    # How many standard errors the marine median sits from zero. Named because the caveat used
    # to call both agreeing legs "indistinguishable from no tracking", and that is true of one
    # of them: a measured near-absence and an unmeasurable one are different things.
    marine_leg = by_realm[phase1i.MARINE]
    marine_sigma = abs(marine_leg.median) / marine_leg.median_se

    def coverage_of(realm: str) -> float:
        return next(held.coverage for held in transfer.held_out if held.realm == realm)

    findings.append(
        Finding(
            key="transfer-fails",
            plain_how=(
                "A test of whether one realm's answer travels. Three bodies of evidence, and "
                "three runs: each time, fit on two of them and try to describe the third, which "
                "the model has never seen. Two of the three could be recovered that way. The "
                "one measured from the air could not, by an order of magnitude — which is the "
                "finding rather than a hitch in it."
            ),
            realm="all",
            taxon_scope="all",
            evidence_type="all",
            bias=TRANSFER_BIAS,
            plain=(
                "Two records on opposite sides of the world agreed that these animals barely "
                "follow the warming. The third found a large response, so what crossed the "
                "equator was an absence."
            ),
            matters=(
                "Almost every published forecast of where wildlife will go assumes a response "
                "measured in one place holds in another. It is an assumption because testing it "
                "needs several responses measured the same way, which is rare. This is three of "
                "them under one audit — and the honest result is that the test could not be run "
                "as intended, because two of the three had almost no response to carry across."
            ),
            plain_caveat=(
                "Three records is three points. The one that disagreed is also the only one "
                "measuring dates instead of places, and the only one from radar, and nothing here "
                "can separate those."
            ),
            claim=(
                "Thermal tracking measured in the northern marine realm "
                f"({by_realm[phase1i.MARINE].median:+.3f}) and the southern terrestrial realm "
                f"({by_realm[phase1i.TERRESTRIAL].median:+.3f}) cannot be told apart, while the "
                f"aerial record ({by_realm[phase1i.AERIAL].median:+.3f}) differs from both. But "
                "the two that agree sit within a few percent of no tracking on a scale where one "
                "is full tracking, so what agreed across the equator is a near-absence of "
                "response — and two near-zeros matching cannot establish that a response "
                "transfers. The one leg carrying a substantial response is the one that broke the "
                "agreement, which is the result this design can support."
            ),
            value=(
                f"hold-one-out error {worst.error:.2f} for {worst.realm} against "
                + " and ".join(
                    f"{held.error:.2f}" for held in transfer.held_out if held.realm != worst.realm
                )
                + " for the other two"
            ),
            scope=(
                f"{by_realm[phase1i.AERIAL].n} radar stations between 37°N and 50°N, "
                f"{by_realm[phase1i.MARINE].n:,} species-and-survey pairs over northern-hemisphere "
                f"shelf seas, and {by_realm[phase1i.TERRESTRIAL].n} species over 496 "
                "quarter-degree cells in southern Africa. Each leg's own window."
            ),
            caveat=(
                "This tests whether three measured responses agree, not whether a model fitted in "
                "one would work in another — a weaker question, and the only one three cases can "
                "answer. And it could not be run as intended, because the two realms that agree do "
                "so at a median tracking of "
                f"{by_realm[phase1i.MARINE].median:+.3f} and "
                f"{by_realm[phase1i.TERRESTRIAL].median:+.3f} on a scale where one is full "
                "tracking. The southern figure is not separable from zero at all; the marine one "
                f"is, at about {marine_sigma:.1f} "
                "standard errors, which makes it a measured near-absence rather than an "
                "unmeasurable one — and neither is a response. So what transferred is an absence, "
                "which is a far cheaper thing to reproduce, and the held-out prediction that "
                "succeeded predicted approximately nothing from two values near nothing. The "
                "aerial leg is the only one carrying a substantial response and the only one that "
                "failed, and it is also the only "
                "phenological leg, the only radar leg and the only one needing a seasonal "
                "temperature slope to reach common units — the pre-registration listed realm, "
                "hemisphere, instrument and decade as inseparable here and did not list response "
                "type, which is the axis the result fell on. That omission is recorded as a "
                "correction in the method note rather than edited away. Every leg divides by a "
                "temperature and none carries wind, land use or fishing pressure, so a realm moved "
                "by something else reports it as a failure to follow the heat."
            ),
            method="docs/methods/phase1i-transfer.md",
            # A limit rather than a change: nothing here moved over time. It bounds what may be
            # extrapolated, which is the same shape as `coverage-bias` and is the promise this
            # discharges. The one positive result in it -- that two realms agreed -- is an
            # agreement about the *absence* of a response, and the caveat says so.
            direction="limit",
            supporting=[
                "The pair that agrees differs in hemisphere, realm, instrument, taxon and decade, "
                f"and its medians sit {agreed[0].gap:.3f} apart "
                f"(p={agreed[0].p_adjusted:.2f}, Holm-corrected) — while the aerial record sits "
                f"{max(pair.gap for pair in transfer.pairs):.2f} from both."
                if agreed
                else "Every pair of realms is distinguishable.",
                "Agreement is not only in the centre: predicting the southern atlas from the "
                f"other two puts {coverage_of(phase1i.TERRESTRIAL):.1%} of it inside the "
                "predicted interquartile range, against the 50% a correct prediction would give, "
                f"and the marine leg lands at {coverage_of(phase1i.MARINE):.1%}. The aerial leg "
                f"gets {worst.coverage:.1%}.",
                "The conversion the aerial leg needs was registered as a stop condition, and it "
                f"does not fire: its median moves {phase1i.aerial_window_spread():.3f} across "
                "three choices of autumn window, against the 0.2 that would have withdrawn the leg "
                "and reduced this to a two-realm comparison.",
                "Both quantities in that conversion are measured from the same reanalysis the "
                "denominator comes from, so no literature constant enters the only leg that needs "
                "one.",
                "Every summary here is a median. The aerial leg's mean moves between -1.09 and "
                "-6.67 across the same three windows whose medians agree to three decimal places, "
                "which is what a ratio of two noisy quantities does.",
                "Two of the four registered predictions failed, including the one naming which "
                "realm would be predicted worst, and both are graded as registered in the method "
                "note rather than restated to match the outcome.",
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


def _two_way_specimen(pooled: pl.DataFrame) -> tuple[int, str] | None:
    """The species that most decisively went both ways: the claim's argument on one animal.

    Scored by the smaller of its strongest northward and strongest southward shift, so the winner
    is the fish for which neither direction is a rounding artefact. Thresholded at the same
    FLAT_DEGREES the species cards use to say "no clear movement", because the specimen and the
    card it leads to must agree about what counts as moving.
    """
    from migratlas.reports.species import FLAT_DEGREES  # noqa: PLC0415 -- sibling, cycle-safe

    scored = (
        pooled.group_by("taxon_key", "taxon_label")
        .agg(
            north=pl.col("per_decade").max(),
            south=pl.col("per_decade").min(),
        )
        .filter((pl.col("north") > FLAT_DEGREES) & (pl.col("south") < -FLAT_DEGREES))
        .with_columns(score=pl.min_horizontal(pl.col("north"), -pl.col("south")))
        .sort("score", descending=True)
    )
    if scored.is_empty():
        return None
    best = scored.row(0, named=True)
    return int(best["taxon_key"]), str(best["taxon_label"])


def _displacement_finding() -> Finding | None:
    """The Phase 1h claim, or None while the escape correlation exceeds its registered bar.

    Published only while the escape holds in both herds: the claim is that displacement is
    independent of the sampling, and a correlation past the bar would make the sentence false.
    Same shape as composition-stable: the condition for publishing is the finding.
    """
    from migratlas.reports import phase1h  # noqa: PLC0415

    herds = {source_id: phase1h.grade(phase1h.seasons(source_id)) for source_id in phase1h.SOURCES}
    first_herd, second_herd = (herds[source_id] for source_id in phase1h.SOURCES)
    if not all(verdict.escape_holds for verdict in herds.values()):
        return None
    return Finding(
        key="displacement-flat",
        plain_how=(
            "Two collared herds, one in the Canadian Rockies and one on Svalbard. For each "
            "animal in each year we took where it was in a fixed winter window and where it was "
            "in a fixed summer window and measured the distance between the two — the same two "
            "windows every year, so the numbers can be compared — then asked whether that "
            "distance is growing or shrinking. Years with fewer than ten animals are left out."
        ),
        realm=Realm.TERRESTRIAL.value,
        taxon_scope=TaxonScope.EXACT.value,
        evidence_type=EvidenceType.TRACK.value,
        bias=DISPLACEMENT_BIAS,
        plain=(
            "Two collared herds travel about as far between winter and summer as they "
            "did when tracking began -- as far as their collars can honestly tell."
        ),
        matters=(
            "The obvious measure of animal movement -- distance walked along the track -- "
            "mostly measures how often the collar spoke, which changed 104-fold over "
            "this record. The distance between winter and summer does not care how "
            "often the collar spoke, and it has not changed. Six million fixes in this "
            "project's lake carry that lesson for every collar study ever pooled."
        ),
        plain_caveat=(
            "A change smaller than roughly a doubling per decade could not have been "
            "seen, so this is a wide kind of nothing."
        ),
        claim=(
            "Winter-summer displacement shows no detectable trend in either herd "
            f"({first_herd.slope_km_per_decade:+.2f} ± {first_herd.slope_ci95:.2f} and "
            f"{second_herd.slope_km_per_decade:+.2f} ± {second_herd.slope_ci95:.2f} km "
            "per decade), while path length tracks the fix interval at rho "
            f"{first_herd.path_vs_gap:+.3f} and displacement does not "
            f"({first_herd.displacement_vs_gap:+.3f})."
        ),
        value=(
            f"{first_herd.slope_km_per_decade:+.2f} ± {first_herd.slope_ci95:.2f} km per "
            f"decade over {first_herd.animal_years} elk animal-years; "
            f"{second_herd.slope_km_per_decade:+.2f} ± {second_herd.slope_ci95:.2f} over "
            f"{second_herd.animal_years} reindeer animal-years"
        ),
        scope=(
            f"Ya Ha Tinda elk 2001-2024 ({first_herd.animals} animals) and Svalbard "
            f"reindeer 2009-2022 ({second_herd.animals}), displacement between fixed "
            "winter and summer calendar windows, years with ten or more animals."
        ),
        caveat=(
            "The null is wide, and that must be said loudly: the elk interval spans "
            "roughly the median displacement itself, so anything short of a doubling or "
            "halving per decade was invisible. The distribution is a mixture of animals "
            "that stayed and animals that left, and whether the *share* that migrates "
            "has changed is a different question this design registered away -- it is "
            "the next pre-registration, not a post-hoc answer. And a herd that shifted "
            "when it moves rather than how far would not appear here at all."
        ),
        method="docs/methods/phase1h-elk.md",
        direction="null",
        supporting=[
            "The confound was demonstrated, not asserted: thin the elk track and the "
            "path length collapses while the displacement stands still, by construction.",
            "The trend is flat across animals and within them, so it is not collar "
            "turnover wearing a trend's clothes.",
            "The reindeer, whose fix interval varies only 8-fold, replicate the escape "
            "measure's independence -- a confound that is absent cannot be demonstrated, "
            "and its absence is the control.",
        ],
    )


def _autumn_advance(first_year: int, last_year: int) -> Finding:
    """The headline claim, recomputed from the station slopes on every build."""
    from migratlas.reports.phase1 import load_conus_nights, station_slopes  # noqa: PLC0415

    slopes = station_slopes(load_conus_nights(), max_year=last_year)
    autumn = slopes.filter(
        pl.col("season") == "autumn",
        pl.col("quantile") == "q50_doy",
        pl.col("latitude").is_between(37, 50, closed="left"),
    )
    values = autumn["days_per_decade"].to_numpy().astype(float)
    mean = float(values.mean())
    ci = 1.96 * float(values.std(ddof=1)) / np.sqrt(values.size)
    return Finding(
        key="autumn-advance",
        plain_how=(
            "Weather radar looks up, so it also sees whatever is flying. For every night at "
            "every station we measured how much was in the air and when the bulk of it went "
            "past, then asked whether that date has moved across thirty years — one straight "
            "line per station, and the published figure is what those lines agree on. Nothing "
            "in this identifies an animal. It counts what reflects."
        ),
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


class Scales(NamedTuple):
    """What the regional half of the predictability question adds to `skill-sparse`."""

    claim: str
    value: str
    supporting: str


def _scales() -> Scales:
    """The reconciliation, published at last.

    Two findings looked like a contradiction for as long as this number sat in a method note. One
    says knowing the weather barely predicts next year's passage; the other credits pre-season
    temperature with about half the thirty-year trend. Phase 3h's floor diagnostic is what makes
    both true at once: at a single station there is very little explainable variance for any driver
    to reach, and pooling stations into a region roughly doubles it. A trend and interannual
    predictability were always different properties, and this is the measurement that says why.
    """
    from migratlas.reports import phase3h, response_floor  # noqa: PLC0415 -- heavy, and only here

    floors = {floor.season: floor for floor in response_floor.collect()}
    floor = floors.get("autumn")
    regional = phase3h.regional_arm("autumn")
    if floor is None or regional is None:
        log.warning("skill-sparse: no regional half, so only the per-station scale is published")
        return Scales(
            claim="",
            value="",
            supporting=(
                "The regional scale could not be measured on this build, so this claim carries "
                "only the per-station answer and not the reason for it."
            ),
        )
    return Scales(
        claim=(
            f" The limit is the target rather than the drivers: a station's own passage date is "
            f"only {floor.station_ceiling:.0%} explainable against {floor.pooled_ceiling:.0%} for "
            f"a flyway-band region, and predicting the region instead lifts the autumn median to "
            f"{regional.median_skill:+.3f} with {regional.significant} of {regional.units} regions "
            f"beating their own null."
        ),
        value=(
            f"; regions {regional.significant}/{regional.units}, "
            f"median {regional.median_skill:+.3f}"
        ),
        supporting=(
            f"Two of this project's claims read as a contradiction until this was published: "
            f"temperature barely predicts a station's next year, and yet it is credited with about "
            f"half the thirty-year advance. Both hold, because a station's date is "
            f"{floor.station_ceiling:.0%} explainable and a region's {floor.pooled_ceiling:.0%} — "
            f"a trend and interannual predictability are different properties, and the second was "
            f"being measured against a target that is mostly noise."
        ),
    )


def _skill_finding() -> Finding:
    """Phase 3a's product: the predictability of timing, measured and mostly absent.

    Recomputed from the lake on every build like every other finding -- the fits are the
    registered era-split hindcasts, deterministic under their fixed seed, so this is slow on
    purpose rather than cached into staleness.
    """
    from migratlas.reports import phase3a  # noqa: PLC0415 -- sibling, heavy

    results = phase3a.aerial()
    seasons = {v.season: v for v in phase3a.verdicts(results)}
    spring, autumn = seasons["spring"], seasons["autumn"]
    scales = _scales()
    return Finding(
        key="skill-sparse",
        plain_how=(
            "Prediction was tested the only way that settles anything: fit on the early years, "
            "predict the later ones, and never look at them first. What the model was allowed "
            "to use was written down before it was run once. Then every station's score was set "
            "against the same model fed the same years shuffled, so a station counts as "
            "predictable only if it beats its own noise. Most did not."
        ),
        realm=Realm.AERIAL.value,
        taxon_scope=TaxonScope.UNATTRIBUTED.value,
        evidence_type=EvidenceType.FLUX.value,
        bias=SKILL_SPARSE_BIAS,
        plain=(
            "Knowing the weather and the big climate patterns barely helps predict when next "
            "year's migration will pass -- only a scattered few autumn stations beat guessing "
            "the average."
        ),
        matters=(
            "Migration timing has shifted over thirty years, and it is tempting to assume the "
            "shift makes each year predictable. It does not: a trend and year-to-year "
            "predictability are different properties, and every forecast this site will ever "
            "draw is licensed only where this map is not empty."
        ),
        plain_caveat=(
            "Tested with one deliberately simple model and seven registered inputs; a cleverer "
            "model might do better, but it would be answering a different, unregistered "
            "question."
        ),
        claim=(
            f"Interannual passage-timing skill is absent at most stations: spring significant "
            f"at {spring.significant} of {spring.stations} (chance bar {spring.binomial_bar}), "
            f"autumn at {autumn.significant} of {autumn.stations} (chance bar "
            f"{autumn.binomial_bar}), with median test-era skill "
            f"{spring.median_skill:+.3f} and {autumn.median_skill:+.3f}.{scales.claim}"
        ),
        value=(
            f"autumn {autumn.significant}/{autumn.stations} stations above chance; spring "
            f"{spring.significant}/{spring.stations} at the chance bar{scales.value}"
        ),
        scope=(
            f"{autumn.stations} US weather-radar stations, 1995-2025, era-split ridge against "
            "the training climatology with a per-station year-shuffle null; covariates fixed "
            "in docs/methods/phase3a-skill.md before any fit."
        ),
        caveat=(
            "One registered model class, one covariate list, one split: absence of skill here "
            "is absence under those registered choices, not a theorem about the atmosphere. "
            "Part of what skill exists is the shared climate modes wearing local clothes -- "
            "where the modes alone predict, the weather's marginal contribution halves -- and "
            "the marine and herd halves of the same design produced no skill map at all: the "
            "surveys mostly changed gear mid-record, and the herds' usable years fall below "
            "the design's own floor. The empty cells are statements about the data and the "
            "design, published at the same rank as the filled ones. One thing this number does "
            "not carry on its own: every aerial skill phase in this project has scored the same "
            "held-out era of the same panel, each blind within itself and none blind to the "
            "tables before it. ADR 0017 reserves the record's last three years for a single "
            "confirmatory run and requires each phase to state where in that sequence it sits."
        ),
        method="docs/methods/phase3a-skill.md",
        direction="limit",
        supporting=[
            scales.supporting,
            "Two of the design's own pre-registered predictions were graded false and stand "
            "recorded in the method note -- spring, the literature's temperature-forced "
            "season, is indistinguishable from the false-positive rate.",
            "Autumn's count clears its exact binomial chance bar, so the sparse map is not "
            "noise promoted to a story.",
            "The fits reproduced byte-for-byte across two runs under the registered seed, "
            "after a data gap forced the only rerun.",
        ],
    )
