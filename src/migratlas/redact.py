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
    evidence_type: EvidenceType
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
# Note that even NOT_SENSITIVE individual data is gridded and de-identified: the safe
# path has to be the default path, not the one taken when someone remembers to ask.
_AGGREGATE_POLICY: Final[dict[Sensitivity, Generalization]] = {
    Sensitivity.NOT_SENSITIVE: _PUBLISH_AS_IS,
    Sensitivity.LOW: _PUBLISH_AS_IS,
    Sensitivity.MODERATE: Generalization(grid_deg=0.5, delay_days=0, drop_individual_id=True),
    Sensitivity.HIGH: Generalization(grid_deg=1.0, delay_days=30, drop_individual_id=True),
    Sensitivity.EMBARGOED: _WITHHOLD,
}

_INDIVIDUAL_POLICY: Final[dict[Sensitivity, Generalization]] = {
    Sensitivity.NOT_SENSITIVE: Generalization(grid_deg=0.1, delay_days=7, drop_individual_id=True),
    Sensitivity.LOW: Generalization(grid_deg=0.25, delay_days=30, drop_individual_id=True),
    Sensitivity.MODERATE: Generalization(grid_deg=1.0, delay_days=90, drop_individual_id=True),
    Sensitivity.HIGH: _WITHHOLD,
    Sensitivity.EMBARGOED: _WITHHOLD,
}


def policy_for(sensitivity: Sensitivity, granularity: Granularity) -> Generalization:
    """Return the default generalisation for a sensitivity and granularity."""
    table = _AGGREGATE_POLICY if granularity is Granularity.AGGREGATE else _INDIVIDUAL_POLICY
    return table[sensitivity]


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
    evidence_type: EvidenceType,
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

    generalization = policy_for(sensitivity, evidence_type.granularity)
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
