"""Registry invariants and the sensitivity resolution cascade."""

from datetime import date

import pytest
from pydantic import ValidationError

from migratlas.catalog import provenance
from migratlas.catalog.loader import UnregisteredSourceError, admit, get, load
from migratlas.catalog.models import Redistribution, Source, TaxonSensitivity
from migratlas.evidence import EvidenceType, Granularity, Realm, TaxonScope
from migratlas.redact import Sensitivity

PERMISSIVE = Redistribution(allowed=True)


def _source(**overrides: object) -> Source:
    fields: dict[str, object] = {
        "id": "test",
        "title": "Test source",
        "evidence_type": EvidenceType.ABUNDANCE_SURFACE,
        "realm": Realm.MARINE,
        "taxon_scope": TaxonScope.EXACT,
        "landing_page": "https://example.org",
        "licence": "CC0 1.0",
        "citation": "Someone (2026)",
        "redistribution": PERMISSIVE,
        "default_sensitivity": Sensitivity.LOW,
        "added": date(2026, 7, 28),
    }
    fields.update(overrides)
    return Source.model_validate(fields)


# --- The shipped registry ----------------------------------------------------
def test_registry_loads() -> None:
    assert load(), "registry is empty"


def test_registry_ids_match_their_keys() -> None:
    for key, source in load().items():
        assert key == source.id


@pytest.mark.parametrize("source_id", sorted(load()))
def test_every_source_is_fully_described(source_id: str) -> None:
    """Licence and citation are not optional. "unknown" is allowed; blank is not."""
    source = get(source_id)
    assert source.licence.strip()
    assert source.citation.strip()
    assert source.caveats.strip(), f"{source_id} records no caveats -- every source has some"


def test_registry_spans_more_than_one_realm() -> None:
    """Phase 1 requires two realms; a single-realm registry means the core is untested."""
    assert len({s.realm for s in load().values()}) >= 2


def test_registry_spans_more_than_one_evidence_type() -> None:
    assert len({s.evidence_type for s in load().values()}) >= 2


def test_unregistered_source_is_refused() -> None:
    with pytest.raises(UnregisteredSourceError, match="not in the registry"):
        get("does-not-exist")


def test_admit_returns_the_source_for_a_good_entry() -> None:
    assert admit("darkecology").id == "darkecology"


def test_radar_source_is_unattributed() -> None:
    """It measures aerial biomass. Claiming a taxon would be claiming an attribution
    the instrument cannot make."""
    assert get("darkecology").taxon_scope is TaxonScope.UNATTRIBUTED


# --- Individual-granularity sources need per-taxon rules ---------------------
def test_individual_granularity_source_requires_taxon_rules() -> None:
    with pytest.raises(ValidationError, match="no taxon_sensitivity"):
        _source(evidence_type=EvidenceType.TRACK)


def test_individual_granularity_source_accepts_taxon_rules() -> None:
    source = _source(
        evidence_type=EvidenceType.TRACK,
        taxon_sensitivity=(
            TaxonSensitivity(
                taxon_key=2420694,
                sensitivity=Sensitivity.HIGH,
                rationale="Targeted by trophy and fin fisheries.",
            ),
        ),
    )
    assert source.evidence_type.granularity is Granularity.INDIVIDUAL


def test_aggregate_source_needs_no_taxon_rules() -> None:
    assert _source(evidence_type=EvidenceType.FLUX).taxon_sensitivity == ()


# --- Resolution cascade ------------------------------------------------------
def test_unknown_taxon_falls_back_to_the_source_default() -> None:
    assert _source().sensitivity_for(999) is Sensitivity.LOW


def test_taxon_rule_beats_the_default() -> None:
    source = _source(
        taxon_sensitivity=(
            TaxonSensitivity(taxon_key=42, sensitivity=Sensitivity.HIGH, rationale="Poached."),
        )
    )
    assert source.sensitivity_for(42) is Sensitivity.HIGH
    assert source.sensitivity_for(43) is Sensitivity.LOW


def test_more_specific_rule_wins() -> None:
    """A track of this animal is dangerous; an occurrence record is not."""
    source = _source(
        taxon_sensitivity=(
            TaxonSensitivity(taxon_key=42, sensitivity=Sensitivity.LOW, rationale="Common."),
            TaxonSensitivity(
                taxon_key=42,
                sensitivity=Sensitivity.HIGH,
                evidence_type=EvidenceType.TRACK,
                rationale="A live track would lead someone straight to it.",
            ),
        )
    )
    assert source.sensitivity_for(42, evidence_type=EvidenceType.TRACK) is Sensitivity.HIGH
    assert source.sensitivity_for(42, evidence_type=EvidenceType.OCCURRENCE) is Sensitivity.LOW


def test_equally_specific_conflict_resolves_to_the_more_restrictive() -> None:
    """A registry conflict must fail safe rather than pick whichever came first."""
    source = _source(
        taxon_sensitivity=(
            TaxonSensitivity(taxon_key=42, sensitivity=Sensitivity.LOW, rationale="One view."),
            TaxonSensitivity(
                taxon_key=42, sensitivity=Sensitivity.EMBARGOED, rationale="Another view."
            ),
        )
    )
    assert source.sensitivity_for(42) is Sensitivity.EMBARGOED


def test_rationale_is_required() -> None:
    with pytest.raises(ValidationError):
        TaxonSensitivity(taxon_key=42, sensitivity=Sensitivity.HIGH, rationale="")


# --- Provenance --------------------------------------------------------------
def test_provenance_names_every_source_and_its_licence() -> None:
    text = provenance.render()
    for source in load().values():
        assert source.title in text
        assert source.licence in text
        assert source.citation.strip().split("\n")[0][:40] in text


def test_provenance_marks_itself_generated() -> None:
    assert "Do not edit by hand" in provenance.render()
