"""The evidence-type core.

Import the vocabulary from here rather than from the submodules::

    from migratlas.evidence import EvidenceType, Realm, spec_for
"""

from migratlas.evidence.schema import (
    ABUNDANCE_SURFACE,
    DETECTION,
    FLUX,
    MARK_RECAPTURE,
    OCCURRENCE,
    SPECS,
    SURVEY_INDEX,
    TRACK,
    EvidenceSpec,
    spec_for,
)
from migratlas.evidence.types import EvidenceType, Granularity, Realm, TaxonScope

__all__ = [
    "ABUNDANCE_SURFACE",
    "DETECTION",
    "FLUX",
    "MARK_RECAPTURE",
    "OCCURRENCE",
    "SPECS",
    "SURVEY_INDEX",
    "TRACK",
    "EvidenceSpec",
    "EvidenceType",
    "Granularity",
    "Realm",
    "TaxonScope",
    "spec_for",
]
