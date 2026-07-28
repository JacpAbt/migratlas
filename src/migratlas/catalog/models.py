"""What must be known about a source before its data may be used."""

from datetime import date
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from migratlas.evidence import EvidenceType, Granularity, Realm, TaxonScope
from migratlas.redact import Sensitivity

NonEmpty = Annotated[str, Field(min_length=1)]


class Redistribution(BaseModel):
    """Whether we may republish derived products, and under what obligation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    allowed: bool
    attribution_required: bool = True
    commercial_use: bool | None = None
    """``None`` where the licence is silent -- which is not the same as permitted."""

    notes: str = ""


class TaxonSensitivity(BaseModel):
    """A sensitivity classification narrower than the source default.

    Keyed by GBIF usage key so it survives renames and synonymy. ``evidence_type`` and
    ``realm`` may narrow it further, because the same animal is not equally sensitive
    in every kind of record.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    taxon_key: int
    sensitivity: Sensitivity
    evidence_type: EvidenceType | None = None
    realm: Realm | None = None
    rationale: NonEmpty
    """Why. An unexplained classification cannot be reviewed."""

    @property
    def specificity(self) -> int:
        """How narrowly this rule applies; higher wins during resolution."""
        return (self.evidence_type is not None) + (self.realm is not None)


class Source(BaseModel):
    """One registered data source."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: NonEmpty
    title: NonEmpty
    evidence_type: EvidenceType
    realm: Realm
    taxon_scope: TaxonScope

    landing_page: HttpUrl
    doi: str = ""
    download_uri: str = ""

    licence: NonEmpty
    """Exact terms as published. "unknown" is an acceptable value; blank is not."""

    licence_url: HttpUrl | None = None
    citation: NonEmpty
    redistribution: Redistribution

    default_sensitivity: Sensitivity
    taxon_sensitivity: tuple[TaxonSensitivity, ...] = ()

    credential: str = ""
    """Name passed to Settings.credential(), if the source needs one."""

    caveats: str = ""
    """Known limitations that would mislead someone who did not read the paper."""

    added: date

    @model_validator(mode="after")
    def _individual_granularity_needs_taxon_rules(self) -> Self:
        """Individual-level sources must classify sensitivity per taxon.

        A single source-wide default is fine for an aggregate surface, where the data is
        already summarised over animals. It is not fine for tracks or occurrences: those
        pin an individual to a place, and "the average species in this dataset is not
        sensitive" is not a statement about the one that is.
        """
        if self.evidence_type.granularity is Granularity.INDIVIDUAL and not self.taxon_sensitivity:
            msg = (
                f"Source {self.id!r} is {self.evidence_type} (individual granularity) "
                f"but has no taxon_sensitivity entries. A source-wide default cannot "
                f"speak for the most sensitive species in the set."
            )
            raise ValueError(msg)
        return self

    def sensitivity_for(
        self,
        taxon_key: int | None,
        *,
        evidence_type: EvidenceType | None = None,
        realm: Realm | None = None,
    ) -> Sensitivity:
        """Resolve sensitivity for a taxon, most specific rule winning.

        Falls back to the source default only when no taxon rule matches, and takes the
        most restrictive of equally specific matches so that a conflict resolves safely
        rather than arbitrarily.
        """
        matches = [
            rule
            for rule in self.taxon_sensitivity
            if rule.taxon_key == taxon_key
            if rule.evidence_type in (None, evidence_type)
            if rule.realm in (None, realm)
        ]
        if not matches:
            return self.default_sensitivity

        best = max(rule.specificity for rule in matches)
        finalists = [rule.sensitivity for rule in matches if rule.specificity == best]
        return max(finalists, key=_RESTRICTIVENESS.__getitem__)


_RESTRICTIVENESS = {
    Sensitivity.NOT_SENSITIVE: 0,
    Sensitivity.LOW: 1,
    Sensitivity.MODERATE: 2,
    Sensitivity.HIGH: 3,
    Sensitivity.EMBARGOED: 4,
}
