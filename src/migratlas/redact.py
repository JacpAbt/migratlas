"""The ethics gate: nothing is published without a clearance minted here.

Two structural choices. It fails closed — an unclassified taxon is not publishable.
And it is a capability, not a convention: tile builders require a
:class:`PublicationClearance` that only this module can mint, so forgetting the gate
is a type error rather than a silent leak.

Policy follows GBIF's *Current Best Practices for Generalizing Sensitive Species
Occurrence Data* and the TDWG Sensitive Species Extension, reported via
``dwc:dataGeneralizations``.
"""

import math
from dataclasses import InitVar, dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Final

from migratlas.evidence.types import EvidenceType, Granularity, Realm, TaxonScope


class Sensitivity(StrEnum):
    """Risk that publishing increases targeted exploitation. Least to most restrictive.

    Deliberately coarse: a finer scale invites false precision in what the literature
    treats as a context-dependent expert judgement.
    """

    NOT_SENSITIVE = "not_sensitive"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EMBARGOED = "embargoed"
    """Not publishable at any resolution, by owner instruction or law."""


class RedactionError(Exception):
    """Base class for gate refusals."""


class IngestRefusedError(RedactionError):
    """A source may not enter the lake."""


class PublicationRefusedError(RedactionError):
    """Data may not be published in any form."""


@dataclass(frozen=True, slots=True)
class Generalization:
    """What to do to the data before publication."""

    grid_deg: float | None
    """Snap coordinates to this grid. ``None`` means no spatial generalisation."""

    delay_days: int
    drop_individual_id: bool
    withhold: bool = False

    def statement(self) -> str:
        """``dwc:dataGeneralizations`` value, so users can tell degraded from precise."""
        if self.withhold:
            return "Withheld entirely: sensitive taxon or evidence type."
        parts: list[str] = []
        if self.grid_deg is not None:
            parts.append(f"coordinates generalised to a {self.grid_deg}-degree grid")
        if self.delay_days:
            parts.append(f"records within {self.delay_days} days of present withheld")
        if self.drop_individual_id:
            parts.append("individual identifiers removed")
        if not parts:
            return "Published at source resolution."
        return (
            "Generalised for animal safety: "
            + "; ".join(parts)
            + ". Fuller data may be available from the data owner on request."
        )


_GATE_KEY: Final = object()


@dataclass(frozen=True, slots=True)
class PublicationClearance:
    """Proof the gate approved a specific publication. Only the gate can mint one."""

    source_id: str
    evidence_type: EvidenceType | None
    """``None`` for a driver layer: an ice edge or a wind field is not evidence about an animal,
    and the gate still prices its licence."""

    realm: Realm
    sensitivity: Sensitivity
    generalization: Generalization
    issued_at: datetime
    permission_reference: str | None = field(default=None)

    gate_key: InitVar[object] = None

    def __post_init__(self, gate_key: object) -> None:
        if gate_key is not _GATE_KEY:
            msg = (
                "PublicationClearance cannot be constructed directly. "
                "Obtain one from migratlas.redact.clear_for_publication()."
            )
            raise RedactionError(msg)


@dataclass(frozen=True, slots=True)
class OwnerPermission:
    """Recorded owner permission to publish more finely than the default.

    Every field required: a permission with no contact and no date is a recollection,
    and recollections do not survive audit.
    """

    reference: str
    granted_by: str
    contact: str
    granted_on: str
    max_grid_deg: float | None
    allow_individual_id: bool
    min_delay_days: int


_PUBLISH_AS_IS = Generalization(grid_deg=None, delay_days=0, drop_individual_id=False)
_WITHHOLD = Generalization(grid_deg=None, delay_days=0, drop_individual_id=True, withhold=True)

# Explicit so a reviewer can read the whole policy and object to a specific cell.
_AGGREGATE_POLICY: Final[dict[Sensitivity, Generalization]] = {
    Sensitivity.NOT_SENSITIVE: _PUBLISH_AS_IS,
    Sensitivity.LOW: _PUBLISH_AS_IS,
    Sensitivity.MODERATE: Generalization(grid_deg=0.5, delay_days=0, drop_individual_id=True),
    Sensitivity.HIGH: Generalization(grid_deg=1.0, delay_days=30, drop_individual_id=True),
    Sensitivity.EMBARGOED: _WITHHOLD,
}

# The grids are GBIF's published category resolutions (adr/0011): not sensitive is released as
# published, LOW is Category 4 (~100 m), MODERATE is Category 3 (~1 km). Two house additions
# survive the alignment because each closes a hole the standard's occurrence-shaped scope never
# considers: the delay defends a live tagged animal against real-time interception, and dropping
# identifiers at MODERATE stops one hunted animal's habitual sites being read off its track.
# HIGH stays withheld outright -- ETHICS.md defines it as active persecution pressure, and a
# persecuted animal's whereabouts have no safe resolution.
_INDIVIDUAL_POLICY: Final[dict[Sensitivity, Generalization]] = {
    Sensitivity.NOT_SENSITIVE: _PUBLISH_AS_IS,
    Sensitivity.LOW: Generalization(grid_deg=0.001, delay_days=30, drop_individual_id=False),
    Sensitivity.MODERATE: Generalization(grid_deg=0.01, delay_days=90, drop_individual_id=True),
    Sensitivity.HIGH: _WITHHOLD,
    Sensitivity.EMBARGOED: _WITHHOLD,
}


def policy_for(sensitivity: Sensitivity, granularity: Granularity) -> Generalization:
    """Return the default generalisation for a sensitivity and granularity."""
    table = _AGGREGATE_POLICY if granularity is Granularity.AGGREGATE else _INDIVIDUAL_POLICY
    return table[sensitivity]


NEVER_INGESTED_KEYS: Final[frozenset[int]] = frozenset({2436436, 2436435})
"""GBIF usage keys for *Homo sapiens* and the genus *Homo*, verified against the species-match API.

Both, because a source may resolve only to genus, and a refusal that a coarser identification slips
past is not a refusal.
"""

NEVER_INGESTED_NAMES: Final[frozenset[str]] = frozenset({"homo sapiens", "homo"})
"""The same refusal by name, for a source that ships names and no keys.

Two routes to one answer rather than a preference between them: Movebank supplies names, the lake
stores keys, and a check that only understood one of those would be satisfiable by accident.
"""


def admit_taxon_for_ingest(
    source_id: str,
    *,
    taxon_key: int | None = None,
    scientific_name: str | None = None,
) -> None:
    """Refuse a taxon that must never enter the lake, whatever its source's registry entry says.

    **Not a sensitivity classification.** Those are per source, in the registry, and the failure
    this closes is precisely that nobody wrote one: an unclassified taxon falls through to
    ``default_sensitivity``, and a source-wide default cannot speak for a species nobody considered.
    That is the same argument :meth:`Source._individual_granularity_needs_taxon_rules` makes,
    applied to the one taxon where the answer is never "publish it more coarsely".

    Found rather than anticipated. Movebank hosts human tracking studies beside animal ones -- an
    open-licence study of twelve people sits in the same taxon list as the caribou -- so an ingest
    that trusted the archive's taxon field would land human location data here. See
    ``docs/methods/tracks-and-sensitivity.md`` §7.

    Deliberately a floor, not a policy row: a registry entry cannot lower it, and the refusal is at
    *ingest* rather than publication because the publication gate can only refuse what it was told
    to look at.

    **A row with no taxon at all is refused too**, and that is not a technicality. The floor answers
    "is this species allowed here"; asked about nothing, it cannot answer, and a gate that returns
    "fine" when it has not been told what it is looking at is not a gate. It was silently reachable:
    the Movebank adapter dropped nulls before calling this, so 13,966 fixes of eight animals whose
    species the archive never recorded went into the lake unscreened -- and per-taxon sensitivity
    cannot be applied to a taxon nobody named either.

    Raises:
        IngestRefusedError: if the taxon is refused outright, or if there is no taxon to check.
    """
    normalised = " ".join(scientific_name.lower().split()) if scientific_name else None
    if taxon_key is None and not normalised:
        msg = (
            f"Source {source_id!r} asked the floor to admit a row carrying neither a taxon key nor "
            f"a scientific name. The floor cannot clear a species it was not told, and neither can "
            f"the per-taxon sensitivity rules. Identify the rows or drop them at the ingest."
        )
        raise IngestRefusedError(msg)
    if taxon_key in NEVER_INGESTED_KEYS or (normalised in NEVER_INGESTED_NAMES):
        subject = scientific_name or f"taxon key {taxon_key}"
        msg = (
            f"Source {source_id!r} carries rows for {subject}, which never enters this lake. "
            f"This is an animal-movement atlas and the gate has no resolution at which human "
            f"location data may be stored. Filter the taxon out at the ingest, not downstream."
        )
        raise IngestRefusedError(msg)


def admit_for_ingest(
    source_id: str,
    *,
    sensitivity: Sensitivity | None,
    licence: str | None,
) -> None:
    """Decide whether a source may enter the local lake.

    Weaker than the publication gate by design: holding raw data on one machine is not
    the dangerous act. What this prevents is data arriving with nobody having thought
    about its sensitivity, because by tiling time that person has moved on.

    Source-level only. A source's *rows* are screened per taxon by
    :func:`admit_taxon_for_ingest`, which this cannot do because a source declares no taxon list.

    Raises:
        IngestRefusedError: if the source is unclassified or has no recorded licence.
    """
    if sensitivity is None:
        msg = (
            f"Source {source_id!r} has no sensitivity classification. Add one to "
            f"catalog/registry.yaml. Unclassified is not a synonym for safe."
        )
        raise IngestRefusedError(msg)
    if not licence:
        msg = (
            f"Source {source_id!r} has no recorded licence. Record the exact terms, "
            f"including 'unknown -- do not redistribute' if that is the truth."
        )
        raise IngestRefusedError(msg)


def clear_for_publication(  # noqa: PLR0913 -- each argument is a distinct policy input
    *,
    source_id: str,
    evidence_type: EvidenceType | None,
    realm: Realm,
    sensitivity: Sensitivity | None,
    taxon_scope: TaxonScope,
    taxon_key: int | None,
    redistribution_allowed: bool,
    permission: OwnerPermission | None = None,
    now: datetime | None = None,
) -> PublicationClearance:
    """Mint a clearance, or refuse. The only way to obtain one.

    ``redistribution_allowed`` has no default on purpose. It comes from the source's licence in
    the registry, and a caller that has not looked it up cannot compile -- which is the same
    trick the clearance itself plays on the exporter. Animal safety and licence terms are
    independent reasons to refuse: eBird Status and Trends is not sensitive in the least and
    still may not be republished from a website.

    Raises:
        PublicationRefusedError: if the licence forbids redistribution, sensitivity is
            unresolved, the taxon claim is inconsistent, or policy withholds the data outright.
    """
    now = now or datetime.now(UTC)

    # First, and before the licence: a taxon on the never-ingested floor is also never published.
    # Redundant if the ingest held -- and that is the point. Rows landed before the floor existed
    # would otherwise reach a reader through a gate that had only ever been taught to check
    # sensitivity, and sensitivity is the thing nobody wrote down for them.
    if taxon_key in NEVER_INGESTED_KEYS:
        msg = (
            f"Refusing to publish {source_id!r}: taxon_key={taxon_key} is on the never-ingested "
            f"floor, so its presence means the lake holds rows an ingest should have refused. "
            f"Delete them rather than coarsening them."
        )
        raise PublicationRefusedError(msg)

    if not redistribution_allowed:
        msg = (
            f"Refusing to publish {source_id!r}: its licence does not permit redistribution. "
            f"The data may be used for analysis, and results may be reported, but no derived "
            f"product may be served. See the source's `redistribution` block in the registry."
        )
        raise PublicationRefusedError(msg)

    if sensitivity is None:
        msg = (
            f"Refusing to publish {source_id!r} ({evidence_type}): no sensitivity "
            f"resolved for taxon_key={taxon_key}. The gate fails closed by design."
        )
        raise PublicationRefusedError(msg)

    # An EXACT claim with no key means a broken crosswalk, which would attach some
    # other taxon's policy to this data.
    if taxon_scope is TaxonScope.EXACT and taxon_key is None:
        msg = (
            f"Refusing to publish {source_id!r}: taxon_scope is EXACT but no "
            f"taxon_key was resolved. Fix the taxonomy crosswalk first."
        )
        raise PublicationRefusedError(msg)

    # A driver layer has no animal in it and no granularity to speak of; the aggregate table is
    # the one whose questions still apply, and the licence refusal above applies in full.
    granularity = evidence_type.granularity if evidence_type else Granularity.AGGREGATE
    generalization = policy_for(sensitivity, granularity)
    if permission is not None:
        generalization = _apply_permission(generalization, permission, sensitivity)

    if generalization.withhold:
        msg = (
            f"Refusing to publish {source_id!r} ({evidence_type}, {sensitivity}): "
            f"policy withholds this combination entirely."
        )
        raise PublicationRefusedError(msg)

    return PublicationClearance(
        source_id=source_id,
        evidence_type=evidence_type,
        realm=realm,
        sensitivity=sensitivity,
        generalization=generalization,
        issued_at=now,
        permission_reference=permission.reference if permission else None,
        gate_key=_GATE_KEY,
    )


def _apply_permission(
    default: Generalization,
    permission: OwnerPermission,
    sensitivity: Sensitivity,
) -> Generalization:
    """Relax the default as far as the owner permitted, and no further.

    An embargo cannot be relaxed by permission: if the owner has changed their mind,
    the classification changes, not the override.
    """
    if sensitivity is Sensitivity.EMBARGOED:
        return default
    return Generalization(
        grid_deg=_coarser_grid(default.grid_deg, permission.max_grid_deg),
        delay_days=max(permission.min_delay_days, 0),
        drop_individual_id=not permission.allow_individual_id,
    )


def _coarser_grid(default_grid: float | None, permitted_grid: float | None) -> float | None:
    """Finest grid both policy and permission tolerate. ``None`` means no gridding."""
    if permitted_grid is None:
        return None
    if default_grid is None:
        return permitted_grid
    return max(default_grid, permitted_grid)


def delay_cutoff(generalization: Generalization, now: datetime) -> datetime | None:
    """Newest timestamp that may be published, or ``None`` when nothing is withheld.

    The single definition of the delay rule. A vectorised filter wants the boundary and a
    scalar check wants a predicate; both come from here so they cannot drift apart.
    """
    if not generalization.delay_days:
        return None
    return now - timedelta(days=generalization.delay_days)


def is_within_delay(timestamp: datetime, generalization: Generalization, now: datetime) -> bool:
    """Whether ``timestamp`` falls in the withheld recent window and must be dropped."""
    cutoff = delay_cutoff(generalization, now)
    return cutoff is not None and timestamp > cutoff


GRID_QUOTIENT_PRECISION: Final = 9
"""Decimal places the cell index is rounded to before flooring.

Grid sizes like 0.1 are not exactly representable, so ``value / 0.1`` can land a hair below
an integer and floor to the cell beneath -- putting a point in the wrong cell, at the finest
and most-used grid. Real coordinates carry nowhere near nine decimal digits of meaningful
precision, so rounding the quotient first removes the representation noise without moving
any genuine boundary.
"""


def snap_to_grid(value: float, grid_deg: float | None) -> float:
    """Snap a coordinate to its grid cell centre.

    Aggregation, not jitter: random offsetting only hides a solvable puzzle, and for
    camera traps naive 1 km obfuscation was narrowed to ~13% of the candidate area
    using public imagery. Centres rather than corners, so a published point is the
    honest centroid of the area it represents.
    """
    if grid_deg is None:
        return value
    index = math.floor(round(value / grid_deg, GRID_QUOTIENT_PRECISION))
    return index * grid_deg + grid_deg / 2
