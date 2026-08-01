"""Registry invariants and the sensitivity resolution cascade."""

from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from migratlas.catalog import provenance
from migratlas.catalog.loader import UnregisteredSourceError, admit, get, load
from migratlas.catalog.models import Redistribution, Source, TaxonSensitivity
from migratlas.evidence import EvidenceType, Granularity, Realm, TaxonScope
from migratlas.redact import (
    PublicationRefusedError,
    Sensitivity,
    clear_for_publication,
)

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


def test_every_module_that_writes_to_the_lake_admits_its_source() -> None:
    """The registry rule was a convention, and a convention got skipped.

    `drivers/narr.py` landed 8,700 rows from an unregistered source, because nothing checked
    that an adapter calls `catalog.admit` -- the writer does not consult the registry, and every
    other adapter happened to call it by hand. This turns "nothing may be ingested that is not
    described here" from a comment at the top of registry.yaml into something that fails.
    """
    source_root = Path(__file__).resolve().parents[1] / "src" / "migratlas"
    writers = ("write_table(", "write_evidence(")
    offenders = []
    for path in sorted(source_root.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        # The writer module defines them; it does not call them about a source of its own.
        if path.parent.name == "lake":
            continue
        # The import is required as well as the call, because `write_table(` is not a name this
        # project owns: pyarrow's ParquetWriter has a method of exactly that name, and
        # `ingest/sabap2.py` uses it to cache a projection of a 33 GB archive without going near
        # the lake. A module that never imports the writer cannot be writing to the lake.
        if "migratlas.lake.writer" not in text:
            continue
        if any(call in text for call in writers) and "catalog.admit(" not in text:
            offenders.append(path.relative_to(source_root).as_posix())
    assert not offenders, f"these write to the lake without admitting a source: {offenders}"


def test_the_lake_write_guard_still_catches_a_module_that_forgets_to_admit() -> None:
    """The guard above was loosened to ignore pyarrow's identically-named method.

    So it needs its own test: a module that really does import the lake writer and call it without
    admitting a source must still be caught, or the loosening quietly disabled the invariant.
    """
    offender = "from migratlas.lake.writer import write_evidence\nwrite_evidence(table, spec)\n"
    innocent = "import pyarrow.parquet as pq\nwriter.write_table(batch)\n"

    def caught(text: str) -> bool:
        if "migratlas.lake.writer" not in text:
            return False
        return any(call in text for call in ("write_table(", "write_evidence(")) and (
            "catalog.admit(" not in text
        )

    assert caught(offender)
    assert not caught(innocent)
    assert not caught(
        offender.replace("write_evidence(table", "catalog.admit(x)\nwrite_evidence(t")
    )


def test_a_driver_only_source_needs_no_evidence_type() -> None:
    """A wind field is not evidence about an animal, and has no taxon to scope.

    It is still registered, because the registry is where a licence lives and PROVENANCE.md is
    generated from it -- a driver kept out would be a source whose terms nothing states.
    """
    source = _source(evidence_type=None, taxon_scope=None)
    assert not source.provides_evidence
    assert source.realm is Realm.MARINE


def test_a_half_specified_source_is_refused() -> None:
    """Either both or neither. An evidence type with no scope leaves it unsaid whether a row
    names a species or a genus; a scope with no evidence type claims taxonomic precision for
    something that is not about animals."""
    with pytest.raises(ValidationError, match="either both evidence_type and taxon_scope"):
        _source(taxon_scope=None)
    with pytest.raises(ValidationError, match="either both evidence_type and taxon_scope"):
        _source(evidence_type=None)


def test_provenance_renders_a_driver_only_source_without_printing_none() -> None:
    """Both display paths formatted `evidence_type` unconditionally, so the first driver-only
    source crashed `catalog list` and would have written "None" into PROVENANCE.md -- while the
    test suite stayed green, because nothing exercised the rendering.
    """
    text = provenance.render()
    # Backticked, so this catches a formatted `None` rather than the document's own prose,
    # which opens "None of this data is ours".
    assert "`None`" not in text
    assert "drivers only" in text


def test_registry_spans_more_than_one_realm() -> None:
    """Phase 1 requires two realms; a single-realm registry means the core is untested."""
    assert len({s.realm for s in load().values()}) >= 2


def test_registry_spans_more_than_one_evidence_type() -> None:
    assert len({s.evidence_type for s in load().values()}) >= 2


def test_unregistered_source_is_refused() -> None:
    with pytest.raises(UnregisteredSourceError, match="not in the registry"):
        get("does-not-exist")


def test_admit_returns_the_source_for_a_good_entry() -> None:
    assert admit("darkecology_daily").id == "darkecology_daily"


def test_radar_source_is_unattributed() -> None:
    """It measures aerial biomass. Claiming a taxon would be claiming an attribution
    the instrument cannot make."""
    assert get("darkecology_daily").taxon_scope is TaxonScope.UNATTRIBUTED


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
    assert source.evidence_type is not None
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


def test_the_committed_provenance_document_is_current() -> None:
    """The credit ledger is generated, committed, and therefore able to go stale.

    It exists because every licence here demands attribution, so a version that no longer matches
    the registry is a broken promise rather than an untidy file. It was invisible to git until
    2026-07-30 -- `.gitignore` carried an unanchored `data/` that matched `docs/data/` too -- which
    is exactly the kind of thing only a test notices.
    """
    committed = Path(__file__).resolve().parents[1] / "docs" / "data" / "PROVENANCE.md"
    assert committed.is_file(), "run `make provenance`"
    assert committed.read_text(encoding="utf-8") == provenance.render(), "run `make provenance`"


# --- The registered track sources --------------------------------------------
#
# The first `track` sources in the lake, so the first to exercise the per-taxon rule. Registered in
# docs/methods/phase1d-tracks.md, which commits to what each one may publish. These assert the
# registry still says what that note says, because the note is the argued version and the registry
# is the enforced one.
TRACK_SOURCES = {
    "movebank_yahatinda_elk": (2440958, Sensitivity.MODERATE),
    "movebank_mountain_caribou_bc": (5220114, Sensitivity.HIGH),
    "movebank_missouri_bison": (2441176, Sensitivity.LOW),
    "movebank_bylot_fox_gps": (5219303, Sensitivity.LOW),
    "movebank_bylot_fox_argos": (5219303, Sensitivity.LOW),
    "movebank_svalbard_reindeer": (5220114, Sensitivity.MODERATE),
    "movebank_hebblewhite_wolves": (5219173, Sensitivity.HIGH),
}


@pytest.mark.parametrize(("source_id", "expected"), TRACK_SOURCES.items())
def test_track_source_classifies_its_own_taxon(
    source_id: str, expected: tuple[int, Sensitivity]
) -> None:
    taxon_key, sensitivity = expected
    assert get(source_id).sensitivity_for(taxon_key) is sensitivity


def test_the_same_species_is_classified_differently_in_two_populations() -> None:
    """Rangifer tarandus is `high` in British Columbia and `moderate` on Svalbard.

    The reason `TaxonSensitivity` is per source rather than global. Southern mountain caribou live
    in herds of tens and several went extinct inside the study window; Svalbard's are ~20,000,
    protected, and hunted under quota. One flag per binomial would be wrong for one of them, and
    which one depends on which way it was set.
    """
    caribou = 5220114
    assert get("movebank_mountain_caribou_bc").sensitivity_for(caribou) is Sensitivity.HIGH
    assert get("movebank_svalbard_reindeer").sensitivity_for(caribou) is Sensitivity.MODERATE


@pytest.mark.parametrize("source_id", TRACK_SOURCES)
def test_a_track_sources_licence_field_describes_its_licence_and_nothing_else(
    source_id: str,
) -> None:
    """Written after getting this wrong: the ethics refusal must not be encoded as a licence fact.

    Both `high` sources were first registered with `redistribution.allowed: false`, to record that
    nothing would be served. It worked -- and made the gate refuse with "its licence does not permit
    redistribution", about two CC BY datasets whose licences permit exactly that. Two costs, and the
    second is worse than the first: an operator reading that message goes to renegotiate a licence
    that was never the obstacle, and `PROVENANCE.md` is generated from this field, so the site would
    have published a false claim about someone else's terms.

    Licence and animal safety are independent reasons to refuse, and `clear_for_publication` says so
    in its own docstring. They stay in separate fields.
    """
    source = get(source_id)
    assert source.licence.startswith("CC")
    assert source.redistribution.allowed, (
        f"{source_id} is {source.licence}, which permits redistribution. If the ethics gate should "
        "refuse it, that belongs in default_sensitivity, not here."
    )


def test_the_gate_refuses_the_two_high_sources_for_the_reason_it_should() -> None:
    """And the message names sensitivity, not the licence."""
    for source_id in ("movebank_mountain_caribou_bc", "movebank_hebblewhite_wolves"):
        source = get(source_id)
        taxon_key = TRACK_SOURCES[source_id][0]
        with pytest.raises(PublicationRefusedError, match="policy withholds"):
            clear_for_publication(
                source_id=source.id,
                evidence_type=EvidenceType.TRACK,
                realm=Realm.TERRESTRIAL,
                sensitivity=source.sensitivity_for(taxon_key),
                taxon_scope=TaxonScope.EXACT,
                taxon_key=taxon_key,
                redistribution_allowed=source.redistribution.allowed,
            )


def test_the_other_five_publish_only_coarsened_and_delayed() -> None:
    """No track is ever published as recorded, whatever its classification.

    Even `low` gets a 0.25-degree grid, a 30-day delay and its individual identifiers removed. The
    safe path has to be the default path rather than the one taken when someone remembers to ask.
    """
    withheld = {"movebank_mountain_caribou_bc", "movebank_hebblewhite_wolves"}
    publishable = set(TRACK_SOURCES) - withheld
    for source_id in publishable:
        source = get(source_id)
        taxon_key = TRACK_SOURCES[source_id][0]
        clearance = clear_for_publication(
            source_id=source.id,
            evidence_type=EvidenceType.TRACK,
            realm=Realm.TERRESTRIAL,
            sensitivity=source.sensitivity_for(taxon_key),
            taxon_scope=TaxonScope.EXACT,
            taxon_key=taxon_key,
            redistribution_allowed=source.redistribution.allowed,
        )
        generalization = clearance.generalization
        assert generalization.grid_deg is not None
        assert generalization.grid_deg >= 0.25
        assert generalization.delay_days >= 30
        assert generalization.drop_individual_id


def test_the_terrestrial_realm_is_no_longer_only_birds() -> None:
    """The structural gap these sources were added to close.

    Asserted on the registry rather than on a comment, because the last three sources added before
    these were all birds and nothing objected.
    """
    terrestrial = [
        source
        for source in load().values()
        if source.realm is Realm.TERRESTRIAL and source.provides_evidence
    ]
    assert any(source.evidence_type is EvidenceType.TRACK for source in terrestrial)
    assert len({source.evidence_type for source in terrestrial}) > 1
