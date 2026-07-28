"""MegaMove adapter. The crosswalk is the risky part: a wrong match puts counts under
the wrong animal, silently."""

import polars as pl
import pytest

from migratlas.evidence import EvidenceType, Realm, TaxonScope, spec_for
from migratlas.ingest import megamove
from migratlas.ingest.http import require_local

SURFACE = spec_for(EvidenceType.ABUNDANCE_SURFACE)


# --- Name folding ------------------------------------------------------------
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Adelie penguin", "adelie penguin"),
        # Accents are stripped, so the grid's mangled header folds to the same key.
        ("Adélie penguin", "adelie penguin"),
        # Apostrophes are deleted, not spaced: "Audouins_gull" has no apostrophe left.
        ("Audouin's gull", "audouins gull"),
        ("Audouin’s gull", "audouins gull"),
        ("Long-nosed fur seal", "long nosed fur seal"),
        ("  Sooty   Shearwater ", "sooty shearwater"),
    ],
)
def test_normalise(raw: str, expected: str) -> None:
    assert megamove.normalise(raw) == expected


def test_normalise_folds_grid_headers_and_common_names_together() -> None:
    assert megamove.normalise("Baraus_petrel") == megamove.normalise("Barau’s petrel")


# --- Crosswalk resolution ----------------------------------------------------
def test_resolve_uses_the_crosswalk() -> None:
    crosswalk = {"sooty shearwater": "Ardenna grisea"}
    assert megamove.resolve_species_columns(["Sooty_shearwater_nind"], crosswalk) == {
        "Sooty_shearwater_nind": "Ardenna grisea"
    }


def test_resolve_applies_curated_aliases() -> None:
    """The 11 known wording differences must resolve, not fall through."""
    crosswalk = {"harbor seal": "Phoca vitulina"}
    assert megamove.resolve_species_columns(["Harbour_seal_nind"], crosswalk) == {
        "Harbour_seal_nind": "Phoca vitulina"
    }


def test_unresolved_columns_are_refused_not_dropped() -> None:
    """Silently dropping a species would be very hard to notice later."""
    with pytest.raises(megamove.CrosswalkError, match="could not be resolved"):
        megamove.resolve_species_columns(["Nonexistent_beast_nind"], {"other": "Genus species"})


def test_every_alias_target_is_distinct() -> None:
    """Two grid columns mapping to one crosswalk entry would double-count a species."""
    targets = list(megamove.ALIASES.values())
    assert len(targets) == len(set(targets))


# --- Reshaping ---------------------------------------------------------------
def _grids() -> tuple[pl.DataFrame, pl.DataFrame]:
    species = pl.DataFrame(
        {
            "Latitude": [-10.5, 20.5],
            "Longitude": [30.5, -40.5],
            "Sooty_shearwater_nind": [3, 0],
            "Blue_shark_nind": [1, 7],
        }
    )
    taxa = pl.DataFrame(
        {
            "Latitude": [-10.5, 20.5],
            "Longitude": [30.5, -40.5],
            "Birds_nind": [3, 0],
            "Fishes_nind": [1, 7],
        }
    )
    return species, taxa


RESOLVED = {"Sooty_shearwater_nind": "Ardenna grisea", "Blue_shark_nind": "Prionace glauca"}
KEYS = {"Ardenna grisea": 2481660, "Prionace glauca": 2417940}


def test_to_evidence_conforms_to_the_spec() -> None:
    species, taxa = _grids()
    SURFACE.validate(megamove.to_evidence(species, taxa, RESOLVED, KEYS))


def test_species_rows_are_exact_with_a_key_and_taxa_rows_are_aggregate_without() -> None:
    """The gate refuses an EXACT claim with no key, so the adapter must not emit one."""
    species, taxa = _grids()
    frame = pl.from_arrow(megamove.to_evidence(species, taxa, RESOLVED, KEYS))
    assert isinstance(frame, pl.DataFrame)

    exact = frame.filter(pl.col("taxon_scope") == TaxonScope.EXACT.value)
    aggregate = frame.filter(pl.col("taxon_scope") == TaxonScope.AGGREGATE.value)

    assert exact.height == 4
    assert exact["taxon_key"].null_count() == 0
    assert aggregate.height == 4
    assert aggregate["taxon_key"].null_count() == aggregate.height
    assert set(aggregate["taxon_label"]) == {"Birds", "Fishes"}


def test_species_with_no_gbif_key_are_dropped_rather_than_published() -> None:
    species, taxa = _grids()
    frame = pl.from_arrow(
        megamove.to_evidence(species, taxa, RESOLVED, {"Ardenna grisea": 2481660})
    )
    assert isinstance(frame, pl.DataFrame)
    exact = frame.filter(pl.col("taxon_scope") == TaxonScope.EXACT.value)
    assert set(exact["taxon_label"]) == {"Ardenna grisea"}


def test_grid_geometry_is_recorded() -> None:
    species, taxa = _grids()
    frame = pl.from_arrow(megamove.to_evidence(species, taxa, RESOLVED, KEYS))
    assert isinstance(frame, pl.DataFrame)
    assert set(frame["cell_size_deg"]) == {1.0}
    assert set(frame["cell_system"]) == {"degree_1"}
    # A plain degree grid has no native cell identifier.
    assert frame["cell_id"].null_count() == frame.height
    assert set(frame["realm"]) == {Realm.MARINE.value}
    # Counts of tracked individuals, never to be summed against relative abundance.
    assert set(frame["value_kind"]) == {"tracked_individuals"}


def test_the_static_period_is_the_studys_full_span() -> None:
    """One surface pooled over 1985-2018, not a time series."""
    species, taxa = _grids()
    frame = pl.from_arrow(megamove.to_evidence(species, taxa, RESOLVED, KEYS))
    assert isinstance(frame, pl.DataFrame)
    assert frame["period_start"].dt.year().unique().to_list() == [1985]
    assert frame["period_end"].dt.year().unique().to_list() == [2018]


def test_zero_counts_are_kept() -> None:
    """A zero in a surveyed cell is an absence given effort, which models need."""
    species, taxa = _grids()
    frame = pl.from_arrow(megamove.to_evidence(species, taxa, RESOLVED, KEYS))
    assert isinstance(frame, pl.DataFrame)
    assert (frame["value"] == 0).sum() > 0


# --- Against the real archives, if the operator has placed them --------------
@pytest.mark.localdata
def test_real_grid_and_crosswalk_are_a_bijection() -> None:
    """Every grid column resolves, and every crosswalk entry is consumed exactly once.

    This is what justifies the curated aliases: the residual paired 1:1, so no species is
    left over and none is claimed twice. If upstream revises the tables, this fails.
    """
    grid = require_local(megamove.SOURCE_ID, megamove.GRID_ARCHIVE)
    tables = require_local(megamove.SOURCE_ID, megamove.TABLES_ARCHIVE)

    crosswalk = megamove.load_crosswalk(tables)
    columns = [
        c
        for c in pl.read_csv(megamove._member(grid, megamove.SPECIES_GRID), n_rows=1).columns
        if c.endswith("_nind")
    ]
    resolved = megamove.resolve_species_columns(columns, crosswalk)

    assert len(resolved) == len(columns) == 111
    assert len(set(resolved.values())) == len(resolved), "a species was claimed twice"
    assert set(resolved.values()) == set(crosswalk.values()), "crosswalk entry unused"
