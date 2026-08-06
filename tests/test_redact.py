"""Tests for the ethics gate.

Each case covers a way the gate could fail *permissively* — the only direction that
matters. A gate that wrongly refuses is an annoyance; one that wrongly permits is a
dead animal.
"""

from datetime import UTC, datetime, timedelta

import pytest

from migratlas.evidence import EvidenceType, Granularity, Realm, TaxonScope
from migratlas.redact import (
    Generalization,
    IngestRefusedError,
    OwnerPermission,
    PublicationClearance,
    PublicationRefusedError,
    RedactionError,
    Sensitivity,
    admit_for_ingest,
    admit_taxon_for_ingest,
    clear_for_publication,
    is_within_delay,
    policy_for,
    snap_to_grid,
)

NOW = datetime(2026, 7, 28, 12, 0, tzinfo=UTC)


def _clear(**overrides: object) -> PublicationClearance:
    """Mint a clearance with sane defaults, overriding one thing at a time."""
    kwargs: dict[str, object] = {
        "source_id": "test_source",
        "evidence_type": EvidenceType.ABUNDANCE_SURFACE,
        "realm": Realm.MARINE,
        "sensitivity": Sensitivity.NOT_SENSITIVE,
        "taxon_scope": TaxonScope.EXACT,
        "taxon_key": 12_345,
        "redistribution_allowed": True,
        "now": NOW,
    }
    kwargs.update(overrides)
    return clear_for_publication(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# The capability cannot be forged
# ---------------------------------------------------------------------------
def test_clearance_cannot_be_constructed_directly() -> None:
    """The whole enforcement model rests on this being impossible."""
    with pytest.raises(RedactionError, match="cannot be constructed directly"):
        PublicationClearance(
            source_id="sneaky",
            evidence_type=EvidenceType.TRACK,
            realm=Realm.TERRESTRIAL,
            sensitivity=Sensitivity.NOT_SENSITIVE,
            generalization=Generalization(grid_deg=None, delay_days=0, drop_individual_id=False),
            issued_at=NOW,
        )


def test_gate_mints_a_usable_clearance() -> None:
    clearance = _clear()
    assert clearance.source_id == "test_source"
    assert clearance.issued_at == NOW


# ---------------------------------------------------------------------------
# Fail closed
# ---------------------------------------------------------------------------
def test_unclassified_sensitivity_is_refused() -> None:
    """Absence of a classification must never be read as absence of risk."""
    with pytest.raises(PublicationRefusedError, match="no sensitivity"):
        _clear(sensitivity=None)


def test_embargoed_is_refused_at_every_granularity() -> None:
    for evidence_type in EvidenceType:
        with pytest.raises(PublicationRefusedError, match="withholds"):
            _clear(sensitivity=Sensitivity.EMBARGOED, evidence_type=evidence_type)


def test_high_sensitivity_individual_data_is_refused() -> None:
    """A poached-species track is exactly the thing this project must not publish."""
    with pytest.raises(PublicationRefusedError, match="withholds"):
        _clear(sensitivity=Sensitivity.HIGH, evidence_type=EvidenceType.TRACK)


def test_high_sensitivity_aggregate_data_is_allowed_but_coarsened() -> None:
    """Aggregates are the safe path, so they survive -- at 1 degree and delayed."""
    clearance = _clear(sensitivity=Sensitivity.HIGH, evidence_type=EvidenceType.ABUNDANCE_SURFACE)
    assert clearance.generalization.grid_deg == 1.0
    assert clearance.generalization.delay_days == 30


def test_exact_taxon_scope_without_a_key_is_refused() -> None:
    """A broken crosswalk would attach the wrong species' policy to the data."""
    with pytest.raises(PublicationRefusedError, match="no taxon_key"):
        _clear(taxon_scope=TaxonScope.EXACT, taxon_key=None)


def test_unattributed_scope_needs_no_key() -> None:
    """Radar biomass genuinely has no taxon; the gate must not demand a fake one."""
    clearance = _clear(
        evidence_type=EvidenceType.FLUX,
        taxon_scope=TaxonScope.UNATTRIBUTED,
        taxon_key=None,
    )
    assert clearance.evidence_type is EvidenceType.FLUX


# ---------------------------------------------------------------------------
# Aggregate-by-default for individual data
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "evidence_type",
    [t for t in EvidenceType if t.granularity is Granularity.INDIVIDUAL],
)
def test_individual_data_is_never_published_at_source_resolution_by_default(
    evidence_type: EvidenceType,
) -> None:
    """Even a species nobody would hunt is gridded and de-identified by default.

    "Aggregate by default" has to mean the safe path is the *default* path, not
    the path taken when someone remembers to ask for it.
    """
    clearance = _clear(evidence_type=evidence_type, sensitivity=Sensitivity.NOT_SENSITIVE)
    assert clearance.generalization.grid_deg is not None
    assert clearance.generalization.drop_individual_id is True


def test_policy_table_is_total() -> None:
    """Every sensitivity and granularity pair must have an explicit policy row."""
    for sensitivity in Sensitivity:
        for granularity in Granularity:
            assert isinstance(policy_for(sensitivity, granularity), Generalization)


def test_sensitivity_is_monotonic_in_restrictiveness() -> None:
    """Coarser or withheld as risk rises -- a regression here would be silent."""
    order = [
        Sensitivity.NOT_SENSITIVE,
        Sensitivity.LOW,
        Sensitivity.MODERATE,
        Sensitivity.HIGH,
        Sensitivity.EMBARGOED,
    ]
    previous = -1.0
    for sensitivity in order:
        policy = policy_for(sensitivity, Granularity.INDIVIDUAL)
        # Withholding is maximally restrictive; treat it as infinite coarseness.
        current = float("inf") if policy.withhold else (policy.grid_deg or 0.0)
        assert current >= previous, f"{sensitivity} is less restrictive than its predecessor"
        previous = current


# ---------------------------------------------------------------------------
# Owner permission
# ---------------------------------------------------------------------------
def test_permission_can_relax_but_must_be_fully_recorded() -> None:
    permission = OwnerPermission(
        reference="perm-0001",
        granted_by="Example Stork Project",
        contact="pi@example.org",
        granted_on="2026-07-01",
        max_grid_deg=None,
        allow_individual_id=True,
        min_delay_days=0,
    )
    clearance = _clear(evidence_type=EvidenceType.TRACK, permission=permission)
    assert clearance.generalization.grid_deg is None
    assert clearance.generalization.drop_individual_id is False
    assert clearance.permission_reference == "perm-0001"


def test_permission_cannot_unlock_an_embargo() -> None:
    """If an owner changes their mind the classification changes, not the override."""
    permission = OwnerPermission(
        reference="perm-0002",
        granted_by="Someone",
        contact="x@example.org",
        granted_on="2026-07-01",
        max_grid_deg=None,
        allow_individual_id=True,
        min_delay_days=0,
    )
    with pytest.raises(PublicationRefusedError):
        _clear(sensitivity=Sensitivity.EMBARGOED, permission=permission)


def test_permission_coarser_than_policy_is_honoured() -> None:
    """A permission may tighten as well as relax."""
    permission = OwnerPermission(
        reference="perm-0003",
        granted_by="Cautious Project",
        contact="x@example.org",
        granted_on="2026-07-01",
        max_grid_deg=2.0,
        allow_individual_id=False,
        min_delay_days=180,
    )
    clearance = _clear(evidence_type=EvidenceType.TRACK, permission=permission)
    assert clearance.generalization.grid_deg == 2.0
    assert clearance.generalization.delay_days == 180


# ---------------------------------------------------------------------------
# Ingest admission
# ---------------------------------------------------------------------------
def test_ingest_refuses_unclassified_source() -> None:
    with pytest.raises(IngestRefusedError, match="no sensitivity classification"):
        admit_for_ingest("mystery", sensitivity=None, licence="CC0")


def test_ingest_refuses_source_without_licence() -> None:
    with pytest.raises(IngestRefusedError, match="no recorded licence"):
        admit_for_ingest("mystery", sensitivity=Sensitivity.LOW, licence=None)


def test_ingest_admits_a_fully_described_source() -> None:
    admit_for_ingest("darkecology", sensitivity=Sensitivity.NOT_SENSITIVE, licence="CC BY 4.0")


# ---------------------------------------------------------------------------
# The never-ingested floor
#
# Movebank hosts human tracking studies beside animal ones: an open-licence study of twelve people
# sits in the same taxon list as the caribou (docs/methods/tracks-and-sensitivity.md, section 7). An
# ingest that trusted the archive's taxon field would land human location data in this lake, and the
# reason the sensitivity tables would not have caught it is that nobody wrote an entry -- so the row
# falls through to `default_sensitivity`, which was chosen for animals.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("key", "name"),
    [
        (2436436, None),
        (2436435, None),
        (None, "Homo sapiens"),
        (None, "homo sapiens"),
        (None, "  Homo   sapiens  "),
        (None, "Homo"),
        (2436436, "Homo sapiens"),
    ],
)
def test_humans_never_enter_the_lake(key: int | None, name: str | None) -> None:
    """By key, by name, at species and at genus, however the source spells it."""
    with pytest.raises(IngestRefusedError, match="never enters this lake"):
        admit_taxon_for_ingest("movebank", taxon_key=key, scientific_name=name)


@pytest.mark.parametrize(
    ("key", "name"),
    [
        (2440944, "Rangifer tarandus"),
        (5219243, "Canis lupus"),
        (None, "Homo sapiens tracking study"),
    ],
)
def test_the_floor_refuses_only_what_it_names(key: int | None, name: str | None) -> None:
    """Including a study *title* containing the name: the check is on the taxon, not on prose.

    A substring match here would refuse a caribou study called "Homo sapiens impacts on Rangifer",
    and a gate that refuses the wrong things gets switched off.

    `(None, None)` used to be a case here, asserting the floor said nothing when told nothing. That
    was the bug rather than the contract -- see the test below.
    """
    admit_taxon_for_ingest("movebank", taxon_key=key, scientific_name=name)


def test_the_floor_refuses_a_row_it_was_told_nothing_about() -> None:
    """A gate asked about nothing cannot answer, and one that returns "fine" is not a gate.

    Silently reachable until now: the Movebank adapter dropped null taxa before calling this, so
    13,966 fixes of eight animals whose species the archive never recorded entered the lake
    unscreened -- and no per-taxon sensitivity rule can reach a taxon nobody named.
    """
    for key, name in ((None, None), (None, ""), (None, "   ")):
        with pytest.raises(IngestRefusedError, match="neither a taxon key nor"):
            admit_taxon_for_ingest("movebank", taxon_key=key, scientific_name=name)


def test_the_floor_holds_where_the_source_level_gate_is_satisfied() -> None:
    """The point of a floor, and the reason it is a second function.

    `NOT_SENSITIVE` with a real licence is the most permissive thing a registry can say, and the
    source-level gate is content with it -- as it should be, since Movebank's animal studies are
    exactly that. The taxon check is what refuses, and nothing at the source level can lower it.
    """
    admit_for_ingest("movebank", sensitivity=Sensitivity.NOT_SENSITIVE, licence="CC0")
    with pytest.raises(IngestRefusedError, match="never enters this lake"):
        admit_taxon_for_ingest("movebank", taxon_key=2436436)


def test_a_human_row_already_in_the_lake_is_refused_at_publication_too() -> None:
    """Belt and braces, for rows that landed before the floor existed.

    Refused ahead of the licence check, unlike everything else, because the answer does not depend
    on the licence: no permission makes this publishable.
    """
    with pytest.raises(PublicationRefusedError, match="never-ingested floor"):
        clear_for_publication(
            source_id="movebank",
            evidence_type=EvidenceType.TRACK,
            realm=Realm.TERRESTRIAL,
            sensitivity=Sensitivity.NOT_SENSITIVE,
            taxon_scope=TaxonScope.EXACT,
            taxon_key=2436436,
            redistribution_allowed=True,
        )


# ---------------------------------------------------------------------------
# Mechanics
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("value", "grid", "expected"),
    [
        (0.0, 1.0, 0.5),
        (0.4, 1.0, 0.5),
        (12.7, 0.5, 12.75),
        # Negative coordinates are the classic off-by-one-cell bug: floor division
        # must be used consistently or the southern and western hemispheres shift.
        (-0.1, 1.0, -0.5),
        (-45.6, 1.0, -45.5),
        (7.3, None, 7.3),
    ],
)
def test_snap_to_grid(value: float, grid: float | None, expected: float) -> None:
    assert snap_to_grid(value, grid) == pytest.approx(expected)


def test_snapped_points_stay_inside_their_cell() -> None:
    """Property that matters: the published centroid must represent the true cell."""
    grid = 0.25
    for raw in (-179.9, -37.4, -0.01, 0.0, 0.01, 58.6, 179.9):
        snapped = snap_to_grid(raw, grid)
        assert abs(snapped - raw) <= grid


def test_is_within_delay() -> None:
    generalization = Generalization(grid_deg=1.0, delay_days=30, drop_individual_id=True)
    assert is_within_delay(NOW - timedelta(days=1), generalization, NOW) is True
    assert is_within_delay(NOW - timedelta(days=60), generalization, NOW) is False


def test_no_delay_means_nothing_is_withheld() -> None:
    generalization = Generalization(grid_deg=None, delay_days=0, drop_individual_id=False)
    assert is_within_delay(NOW, generalization, NOW) is False


# ---------------------------------------------------------------------------
# The public statement
# ---------------------------------------------------------------------------
def test_generalization_statement_describes_what_was_done() -> None:
    """dwc:dataGeneralizations must let a user tell degraded data from precise data."""
    statement = Generalization(grid_deg=1.0, delay_days=90, drop_individual_id=True).statement()
    assert "1.0-degree grid" in statement
    assert "90 days" in statement
    assert "individual identifiers removed" in statement
    assert "data owner" in statement


def test_source_resolution_statement_is_explicit() -> None:
    statement = Generalization(grid_deg=None, delay_days=0, drop_individual_id=False).statement()
    assert statement == "Published at source resolution."


# --- Licence, which is a separate reason to refuse from animal safety -------
def test_a_licence_forbidding_redistribution_refuses_publication() -> None:
    """eBird Status and Trends is not sensitive at all and still may not be republished."""
    with pytest.raises(PublicationRefusedError, match="does not permit redistribution"):
        clear_for_publication(
            source_id="ebird_status_trends",
            evidence_type=EvidenceType.ABUNDANCE_SURFACE,
            realm=Realm.AERIAL,
            sensitivity=Sensitivity.NOT_SENSITIVE,
            taxon_scope=TaxonScope.EXACT,
            taxon_key=9515886,
            redistribution_allowed=False,
        )


def test_the_licence_check_runs_before_anything_else() -> None:
    """A forbidden licence is refused even where sensitivity would also have refused it.

    Order matters for the message: told "no sensitivity resolved", an operator goes looking for
    a missing classification instead of reading the licence.
    """
    with pytest.raises(PublicationRefusedError, match="does not permit redistribution"):
        clear_for_publication(
            source_id="ebird_status_trends",
            evidence_type=EvidenceType.TRACK,
            realm=Realm.AERIAL,
            sensitivity=None,
            taxon_scope=TaxonScope.UNATTRIBUTED,
            taxon_key=None,
            redistribution_allowed=False,
        )
