import json

import polars as pl
import pytest

from migratlas.catalog import loader as catalog
from migratlas.evidence import EvidenceType, Realm, TaxonScope, spec_for
from migratlas.ingest import ebird_st
from migratlas.redact import PublicationRefusedError, clear_for_publication


# --- The list is a licence obligation, not a preference ---------------------
def test_the_species_list_stays_inside_the_terms() -> None:
    """Non-peer-reviewed use is capped at 50 species. A cap you can drift past is not a cap."""
    assert len(ebird_st.SPECIES) <= ebird_st.MAX_SPECIES


def test_species_codes_and_names_are_unique() -> None:
    """A duplicate would silently spend two of the fifty on one bird."""
    codes = [s.code for s in ebird_st.SPECIES]
    names = [s.scientific_name for s in ebird_st.SPECIES]
    assert len(set(codes)) == len(codes)
    assert len(set(names)) == len(names)


def test_ingest_refuses_a_list_over_the_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    over = ebird_st.SPECIES + (ebird_st.Species("xxxxxx", "Genus species", "Test Bird"),) * (
        ebird_st.MAX_SPECIES + 1 - len(ebird_st.SPECIES)
    )
    monkeypatch.setattr(ebird_st, "SPECIES", over)
    with pytest.raises(ebird_st.SpeciesRejectedError, match="do not raise the cap"):
        ebird_st.ingest()


# --- The source is registered as unpublishable, and that is load-bearing ----
def test_the_registry_forbids_redistributing_this_source() -> None:
    source = catalog.get(ebird_st.SOURCE_ID)
    assert source.redistribution.allowed is False


def test_the_gate_refuses_to_publish_it() -> None:
    """The terms permit analysis and forbid serving it. Enforced, not merely documented."""
    source = catalog.get(ebird_st.SOURCE_ID)
    with pytest.raises(PublicationRefusedError, match="does not permit redistribution"):
        clear_for_publication(
            source_id=source.id,
            evidence_type=EvidenceType.ABUNDANCE_SURFACE,
            realm=Realm.AERIAL,
            sensitivity=source.default_sensitivity,
            taxon_scope=TaxonScope.EXACT,
            taxon_key=9515886,
            redistribution_allowed=source.redistribution.allowed,
        )


def test_ingest_refuses_if_the_registry_ever_says_publishable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Belt and braces: if the registry entry is edited, the ingest stops rather than the gate.

    Landing rows under a registry entry that would let them be published is the failure this
    guards, and it is cheaper to refuse at ingest than to notice at export.
    """
    source = catalog.get(ebird_st.SOURCE_ID)
    relaxed = source.model_copy(
        update={"redistribution": source.redistribution.model_copy(update={"allowed": True})}
    )
    # Patched where the module looked it up, which is the only binding that matters.
    monkeypatch.setattr(catalog, "admit", lambda _source_id: relaxed)
    monkeypatch.setattr(ebird_st, "taxon_keys", dict)
    with pytest.raises(ebird_st.SpeciesRejectedError, match="registered as redistributable"):
        ebird_st.ingest()


# --- Verification against the source's own metadata -------------------------
def _config(code: str, *, resident: bool) -> dict[str, object]:
    return {"SPECIES_CODE": [code], "IS_RESIDENT": [resident], "SRD_PRED_YEAR": [2023]}


def test_a_resident_species_is_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
) -> None:
    """eBird's own flag decides, so a mistake in the curated list cannot become quiet rows."""
    path = tmp_path / "config.json"  # type: ignore[operator]
    path.write_text(json.dumps(_config("abetow", resident=True)), encoding="utf-8")
    monkeypatch.setattr(ebird_st, "_download", lambda *_args: path)

    with pytest.raises(ebird_st.SpeciesRejectedError, match="resident per eBird"):
        ebird_st.verify(ebird_st.Species("abetow", "Melozone aberti", "Abert's Towhee"))


def test_a_code_that_disagrees_with_its_config_is_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory
) -> None:
    path = tmp_path / "config.json"  # type: ignore[operator]
    path.write_text(json.dumps(_config("swathr", resident=False)), encoding="utf-8")
    monkeypatch.setattr(ebird_st, "_download", lambda *_args: path)

    with pytest.raises(ebird_st.SpeciesRejectedError, match="not the code in its own config"):
        ebird_st.verify(ebird_st.Species("veery", "Catharus fuscescens", "Veery"))


# --- Shape of what lands ----------------------------------------------------
def test_evidence_rows_match_the_canonical_schema() -> None:
    weeks = pl.DataFrame(
        {
            "week_date": ["2023-05-03", "2023-05-10"],
            "cell_longitude": [-95.5, -95.5],
            "cell_latitude": [39.5, 39.5],
            "value": [0.25, 1.75],
        }
    )
    species = ebird_st.Species("swathr", "Catharus ustulatus", "Swainson's Thrush")
    table = ebird_st.to_evidence(species, weeks, taxon_key=2490705)

    assert table.schema.equals(spec_for(EvidenceType.ABUNDANCE_SURFACE).schema)
    frame = pl.from_arrow(table)
    assert isinstance(frame, pl.DataFrame)
    assert frame["realm"].unique().to_list() == [Realm.AERIAL.value]
    assert frame["value_kind"].unique().to_list() == ["relative_abundance"]
    # A weekly period, which is the whole reason this source is worth the licence constraints.
    assert (frame["period_end"] - frame["period_start"]).dt.total_days().unique().to_list() == [6]


def test_the_week_is_a_real_period_not_a_year() -> None:
    """Every other surface in the lake carries a year or a multi-decade span."""
    weeks = pl.DataFrame(
        {
            "week_date": ["2023-01-04"],
            "cell_longitude": [-95.5],
            "cell_latitude": [39.5],
            "value": [1.0],
        }
    )
    frame = pl.from_arrow(ebird_st.to_evidence(ebird_st.SPECIES[0], weeks, taxon_key=1))
    assert isinstance(frame, pl.DataFrame)
    assert frame["period_start"].dt.strftime("%Y-%m-%d").to_list() == ["2023-01-04"]
    assert frame["period_end"].dt.strftime("%Y-%m-%d").to_list() == ["2023-01-10"]


def test_relative_abundance_is_averaged_across_subcells_never_summed() -> None:
    """It is an expected count on a standard checklist, so it does not add over area.

    Two 27 km points inside one degree cell must average, not sum. Summing is the intuitive
    thing to write and would scale the value with how many sub-cells a degree happens to hold.
    """
    points = pl.DataFrame(
        {
            "week_date": ["2023-05-03"] * 3,
            "lon": [-95.9, -95.1, -94.9],
            "lat": [39.1, 39.9, 39.5],
            "value": [1.0, 3.0, 10.0],
        }
    )
    cells = ebird_st.to_degree_cells(points)

    assert cells.height == 2
    by_cell = dict(zip(cells["cell_longitude"], cells["value"], strict=True))
    assert by_cell[-95.5] == pytest.approx(2.0)
    assert by_cell[-94.5] == pytest.approx(10.0)
