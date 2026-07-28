"""OBIS speciesgrids adapter. The H3 grid and the WoRMS-to-GBIF hop are the risky parts."""

import polars as pl
import pytest

from migratlas.evidence import EvidenceType, Realm, TaxonScope, spec_for
from migratlas.ingest import obis

SURFACE = spec_for(EvidenceType.ABUNDANCE_SURFACE)

KEYS = {"Ursus maritimus": 2433451, "Erignathus barbatus": 2433397}


def _slice() -> pl.DataFrame:
    """Two Arctic species over three H3 cells, shaped as the DuckDB query returns them."""
    return pl.DataFrame(
        {
            "species": ["Ursus maritimus", "Erignathus barbatus", "Phoca vitulina"],
            "aphia_id": [137085, 137079, 137084],
            "taxon_class": ["Mammalia", "Mammalia", "Mammalia"],
            "records": [3, 2, 11],
            "min_year": [1958, 2005, 1990],
            "max_year": [1958, 2005, 2020],
            "cell": ["87031026bffffff", "870312935ffffff", "8703147aaffffff"],
            "cell_longitude": [-138.665, -153.037, -154.906],
            "cell_latitude": [85.062, 84.532, 85.508],
        }
    )


def test_to_evidence_conforms_to_the_spec() -> None:
    SURFACE.validate(obis.to_evidence(_slice(), KEYS))


def test_h3_cells_are_carried_natively_with_no_degree_size() -> None:
    """An H3 hexagon has no single degree size; inventing one would misstate the geometry."""
    frame = pl.from_arrow(obis.to_evidence(_slice(), KEYS))
    assert isinstance(frame, pl.DataFrame)
    assert set(frame["cell_system"]) == {"h3_7"}
    assert frame["cell_size_deg"].null_count() == frame.height
    assert frame["cell_id"].null_count() == 0
    assert set(frame["cell_id"]) <= set(_slice()["cell"])


def test_period_is_per_row_not_a_fixed_span() -> None:
    """Unlike a pooled surface, each cell carries its own observed year range."""
    frame = pl.from_arrow(obis.to_evidence(_slice(), KEYS))
    assert isinstance(frame, pl.DataFrame)
    assert sorted(frame["period_start"].dt.year().unique().to_list()) == [1958, 2005]
    assert sorted(frame["period_end"].dt.year().unique().to_list()) == [1958, 2005]


def test_unresolved_species_are_dropped_not_published_without_a_key() -> None:
    """The gate refuses an EXACT claim with no key, so the adapter must not emit one."""
    frame = pl.from_arrow(obis.to_evidence(_slice(), KEYS))
    assert isinstance(frame, pl.DataFrame)
    # Phoca vitulina is absent from KEYS.
    assert set(frame["taxon_label"]) == set(KEYS)
    assert frame["taxon_key"].null_count() == 0
    assert set(frame["taxon_scope"]) == {TaxonScope.EXACT.value}


def test_cells_with_no_year_range_are_dropped() -> None:
    """The schema requires a period; a cell with no years cannot be placed in time, and
    inventing a date would be worse than losing the row."""
    frame = _slice().with_columns(
        min_year=pl.Series([1958, None, 1990], dtype=pl.Int64),
    )
    out = pl.from_arrow(obis.to_evidence(frame, KEYS))
    assert isinstance(out, pl.DataFrame)
    assert out.height == 1
    assert set(out["taxon_label"]) == {"Ursus maritimus"}


def test_value_kind_says_records_not_individuals() -> None:
    """Occurrence records measure sampling effort as much as distribution, and must never be
    summed against a tracked-individual or relative-abundance surface."""
    frame = pl.from_arrow(obis.to_evidence(_slice(), KEYS))
    assert isinstance(frame, pl.DataFrame)
    assert set(frame["value_kind"]) == {"occurrence_records"}
    assert set(frame["realm"]) == {Realm.MARINE.value}


def test_scope_bound_is_vertebrates_and_cephalopods() -> None:
    """The bound is deliberate and documented; plankton and microbes are out of scope."""
    assert "Mammalia" in obis.MOVEMENT_CLASSES
    assert "Aves" in obis.MOVEMENT_CLASSES
    assert "Elasmobranchii" in obis.MOVEMENT_CLASSES
    assert "Cephalopoda" in obis.MOVEMENT_CLASSES
    # Explicitly excluded for now: 27k species, each needing a Backbone lookup.
    assert "Teleostei" not in obis.MOVEMENT_CLASSES
    # And definitively not these.
    for out_of_scope in ("Bacillariophyceae", "Copepoda", "Gastropoda", "Gammaproteobacteria"):
        assert out_of_scope not in obis.MOVEMENT_CLASSES


def test_parts_outside_the_expected_prefix_are_refused() -> None:
    """Part URLs come from parsing external XML, so they are checked before use."""
    with pytest.raises(ValueError, match="outside the expected prefix"):
        obis.read_slice(["https://example.org/evil.parquet"])


# --- Live source, opt-in -----------------------------------------------------
@pytest.mark.network
def test_bucket_still_lists_extensionless_parts() -> None:
    """The files carry no extension, so a *.parquet glob silently finds nothing."""
    urls = obis.part_urls()
    assert urls
    assert all(url.startswith(f"{obis.BUCKET}/{obis.PREFIX}") for url in urls)
    assert not any(url.endswith(".parquet") for url in urls)
