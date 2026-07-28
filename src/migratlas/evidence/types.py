"""Core vocabulary. Downstream code dispatches on these and never on taxon."""

from enum import StrEnum


class Granularity(StrEnum):
    """Whether a record concerns one animal or many."""

    INDIVIDUAL = "individual"
    AGGREGATE = "aggregate"


class EvidenceType(StrEnum):
    """How we came to know an animal was somewhere.

    Seven shapes cover every source surveyed; they differ in dimensionality, not in
    taxon. A fish acoustic detection and a bat radio detection are the same shape and
    go through the same code. A source that fits none of these is a design
    conversation, not a special case.
    """

    TRACK = "track"
    """Ordered positions of one identified animal."""

    OCCURRENCE = "occurrence"
    """Unordered presence points, one observation each."""

    ABUNDANCE_SURFACE = "abundance_surface"
    """Gridded population estimate per time step."""

    FLUX = "flux"
    """Passage intensity past a fixed instrument."""

    DETECTION = "detection"
    """An identified animal seen by a fixed station at a time."""

    MARK_RECAPTURE = "mark_recapture"
    """Paired marking and re-encounter events."""

    SURVEY_INDEX = "survey_index"
    """Standardised repeated counts with effort."""

    @property
    def granularity(self) -> Granularity:
        """Whether records of this type trace back to an individual animal.

        The redaction gate keys its policy off this. ``OCCURRENCE`` counts as
        individual: one observation pins one animal to one place, which is what makes
        rare-species records sensitive.
        """
        return Granularity.AGGREGATE if self in _AGGREGATE_TYPES else Granularity.INDIVIDUAL


class Realm(StrEnum):
    """Physical medium of an observation or driver.

    The axis that keeps the driver layer from becoming terrestrial-only: a marine
    metric pulls sea surface temperature and chlorophyll where an aerial one pulls
    reanalysis winds, and neither knows about the other.
    """

    AERIAL = "aerial"
    TERRESTRIAL = "terrestrial"
    MARINE = "marine"
    FRESHWATER = "freshwater"


class TaxonScope(StrEnum):
    """How precisely a record is attributed to a taxon.

    Exists because weather radar measures aerial biomass without separating birds
    from bats from insects. A taxon-agnostic core has to be able to say that, rather
    than quietly labelling the signal with whichever group is most studied.
    """

    EXACT = "exact"
    """Resolved to a single GBIF Backbone key."""

    AGGREGATE = "aggregate"
    """A named group rather than one taxon."""

    UNATTRIBUTED = "unattributed"
    """Biological signal with no taxonomic attribution at all."""


_AGGREGATE_TYPES = frozenset(
    {EvidenceType.ABUNDANCE_SURFACE, EvidenceType.FLUX, EvidenceType.SURVEY_INDEX}
)
