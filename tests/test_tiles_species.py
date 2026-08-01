import json
from pathlib import Path

import polars as pl
import pytest

from migratlas.catalog import loader as catalog
from migratlas.catalog.models import TaxonSensitivity
from migratlas.evidence import EvidenceType, Realm
from migratlas.redact import Sensitivity
from migratlas.tiles import species as tile_species
from migratlas.tiles.layers import LayerSpec


def _cells(taxon_key: int, count: int, *, label: str = "Testus specius") -> pl.DataFrame:
    """One taxon on `count` one-degree cells, all cell centres."""
    return pl.DataFrame(
        {
            "taxon_key": [taxon_key] * count,
            "taxon_label": [label] * count,
            "cell_longitude": [(-40.5 + index) for index in range(count)],
            "cell_latitude": [20.5] * count,
            "value": [float(index + 1) for index in range(count)],
        }
    )


def _layer(source_id: str = "megamove") -> LayerSpec:
    return LayerSpec(
        name="marine-space-use",
        source_id=source_id,
        evidence_type=EvidenceType.ABUNDANCE_SURFACE,
        realm=Realm.MARINE,
        title="Test layer",
        description="",
        cell_size_deg=1.0,
    )


def _build(
    monkeypatch: pytest.MonkeyPatch, frame: pl.DataFrame, tmp_path: Path, **layer_kwargs: object
) -> tile_species.SpeciesExport:
    monkeypatch.setattr(tile_species, "per_taxon_cells", lambda _source: frame)
    return tile_species.build((_layer(**layer_kwargs),), tmp_path)  # type: ignore[arg-type]


# --- The grid round-trips exactly ------------------------------------------
def test_a_taxon_grid_decodes_to_the_cells_it_was_given(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    frame = _cells(1234, 5)
    export = _build(monkeypatch, frame, tmp_path)
    assert len(export.entries) == 1

    entry = export.entries[0]
    shard = json.loads((tmp_path / f"species-{entry.shard:02d}.json").read_text(encoding="utf-8"))
    grid = shard[str(entry.taxon_key)]

    size = grid["cell_size_deg"]
    decoded = {
        (round((x + 0.5) * size - 180, 6), round((y + 0.5) * size - 90, 6))
        for x, y in zip(grid["x"], grid["y"], strict=True)
    }
    expected = set(
        zip(
            [round(v, 6) for v in frame["cell_longitude"]],
            [round(v, 6) for v in frame["cell_latitude"]],
            strict=True,
        )
    )
    assert decoded == expected


def test_every_shard_file_exists_even_when_empty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A missing shard is a 404 in the browser, so all of them are written."""
    _build(monkeypatch, _cells(7, 4), tmp_path)
    for shard in range(tile_species.SHARDS):
        assert (tmp_path / f"species-{shard:02d}.json").is_file()


def test_a_shard_is_written_in_a_stable_order(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Numerically, so two builds of the same data produce the same bytes.

    They did not. A `group_by` promises no order, so each build wrote the taxa into a shard
    wherever they came out -- 64 files marked modified, identical in length and content, differing
    only in arrangement. The cost is not the churn: it is that a real change cannot be seen in a
    diff like that, and one was hiding in one.
    """
    frame = pl.concat([_cells(key, 4, label=f"Taxon {key}") for key in (192, 64, 128)])
    _build(monkeypatch, frame, tmp_path)
    shard = json.loads((tmp_path / "species-00.json").read_text(encoding="utf-8"))
    assert list(shard) == ["64", "128", "192"]


def test_a_taxon_lands_in_the_shard_the_index_claims(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The index and the shards must agree or a search hit fetches the wrong file."""
    frame = pl.concat([_cells(key, 4, label=f"Taxon {key}") for key in (100, 101, 164, 228)])
    export = _build(monkeypatch, frame, tmp_path)

    for entry in export.entries:
        assert entry.shard == entry.taxon_key % tile_species.SHARDS
        shard = json.loads(
            (tmp_path / f"species-{entry.shard:02d}.json").read_text(encoding="utf-8")
        )
        assert str(entry.taxon_key) in shard


def test_taxa_below_the_cell_floor_are_counted_not_hidden(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    frame = pl.concat([_cells(1, tile_species.MIN_CELLS - 1), _cells(2, tile_species.MIN_CELLS)])
    export = _build(monkeypatch, frame, tmp_path)

    assert export.too_small == 1
    assert [entry.taxon_key for entry in export.entries] == [2]


# --- The gate runs per taxon, which is the point of this module -------------
def test_a_sensitive_taxon_is_coarsened_while_its_neighbours_are_not(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The behaviour no pooled export can show, and why the sensitivity table is per taxon.

    Driven through a real registry rule rather than a patched method, so the resolution logic and
    the export are both under test.
    """
    sensitive = 4242
    classified = catalog.get("megamove").model_copy(
        update={
            "taxon_sensitivity": [
                TaxonSensitivity(
                    taxon_key=sensitive,
                    sensitivity=Sensitivity.MODERATE,
                    rationale="Test rule: a species whose cells must be coarsened.",
                )
            ]
        }
    )
    monkeypatch.setattr(catalog, "get", lambda _id: classified)

    frame = pl.concat([_cells(sensitive, 6, label="Sensitive one"), _cells(11, 6, label="Open")])
    export = _build(monkeypatch, frame, tmp_path)

    by_key = {entry.taxon_key: entry for entry in export.entries}
    # MODERATE for an aggregate surface is a half-degree grid; the source default coarsens nothing.
    assert "0.5" in by_key[sensitive].generalization
    assert by_key[11].generalization != by_key[sensitive].generalization

    shard = json.loads(
        (tmp_path / f"species-{by_key[sensitive].shard:02d}.json").read_text(encoding="utf-8")
    )
    assert shard[str(sensitive)]["cell_size_deg"] == 0.5


def test_a_source_that_forbids_redistribution_publishes_no_species(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """eBird is ingested and must never appear here, per its licence."""
    monkeypatch.setattr(tile_species, "per_taxon_cells", lambda _source: _cells(1, 9))
    export = tile_species.build((_layer(source_id="ebird_status_trends"),), tmp_path)
    assert export.entries == []


# --- The search index ------------------------------------------------------
def test_the_index_only_lists_taxa_that_have_a_surface(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The old index was a seed list and most hits led nowhere. This one cannot."""
    frame = pl.concat([_cells(5, 8, label="Alpha one"), _cells(6, 2, label="Beta two")])
    export = _build(monkeypatch, frame, tmp_path)
    monkeypatch.setattr(tile_species, "vernaculars", lambda: {5: "Alpha"})

    destination = tmp_path / "taxon-index.json"
    tile_species.write_index(export, destination)
    payload = json.loads(destination.read_text(encoding="utf-8"))

    assert payload["shards"] == tile_species.SHARDS
    assert [taxon["key"] for taxon in payload["taxa"]] == [5]
    assert payload["taxa"][0]["vernacular"] == "Alpha"
    assert payload["taxa"][0]["cells"] == 8
    # Present so two rows for one taxon in two layers can be told apart.
    assert payload["taxa"][0]["layer_title"] == "Test layer"


def test_the_index_is_ordered_widest_ranging_first(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """With thousands of taxa the order of equally-good matches is what a viewer sees."""
    frame = pl.concat(
        [_cells(1, 4, label="Small"), _cells(2, 40, label="Large"), _cells(3, 12, label="Medium")]
    )
    export = _build(monkeypatch, frame, tmp_path)
    monkeypatch.setattr(tile_species, "vernaculars", dict)

    destination = tmp_path / "taxon-index.json"
    tile_species.write_index(export, destination)
    taxa = json.loads(destination.read_text(encoding="utf-8"))["taxa"]
    assert [taxon["cells"] for taxon in taxa] == [40, 12, 4]


# --- One taxon, one name ----------------------------------------------------
def _entry(key: int, label: str, cells: int, layer: str = "a") -> tile_species.SpeciesEntry:
    return tile_species.SpeciesEntry(
        taxon_key=key,
        scientific_name=label,
        layer=layer,
        layer_title=layer,
        cells=cells,
        shard=key % tile_species.SHARDS,
        generalization="",
    )


def test_two_sources_naming_one_animal_differently_give_it_one_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The crabeater seal shipped as both *Lobodon carcinophaga* and *carcinophagus*.

    Ninety-five keys in the lake carry two or more verbatim labels, mostly genuine taxonomic
    revisions -- *Grus* and *Antigone canadensis* are one bird. Whichever the build happened to
    read first became a second search result for an animal there is only one of.
    """
    monkeypatch.setattr(tile_species, "canonical_names", dict)
    entries = [
        _entry(2434762, "Lobodon carcinophagus", 40, layer="megamove"),
        _entry(2434762, "Lobodon carcinophaga", 9, layer="obis"),
    ]
    resolved = tile_species._display_names(entries)
    assert set(resolved) == {2434762}


def test_the_backbone_name_beats_the_widest_label(monkeypatch: pytest.MonkeyPatch) -> None:
    """A cached name is the same taxon's name whoever is speaking, so it wins outright.

    The fallback is only deterministic, not correct -- it takes the label carried by the most
    cells, which is a fact about how much data a source published rather than about the animal.
    """
    monkeypatch.setattr(tile_species, "canonical_names", lambda: {7: "Antigone canadensis"})
    entries = [_entry(7, "Grus canadensis", 900), _entry(7, "Antigone canadensis", 3)]
    assert tile_species._display_names(entries)[7] == "Antigone canadensis"


def test_an_uncached_key_falls_back_to_the_widest_label(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tile_species, "canonical_names", dict)
    entries = [_entry(7, "Grus canadensis", 900), _entry(7, "Antigone canadensis", 3)]
    assert tile_species._display_names(entries)[7] == "Grus canadensis"


def test_the_old_flat_names_cache_is_read_rather_than_discarded(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Filling it is twenty minutes of GBIF requests; a format change may not cost that twice."""
    cache = tmp_path / "vernaculars.json"
    cache.write_text(json.dumps({"11": "Sperm Whale", "12": ""}), encoding="utf-8")
    monkeypatch.setattr(tile_species, "_names_cache", lambda: cache)

    assert tile_species.vernaculars() == {11: "Sperm Whale"}
    # No scientific names in the old shape, so those keys still need warming rather than looking
    # complete -- which is what would happen if the reader defaulted them to the empty string.
    assert tile_species.canonical_names() == {}


# --- The shipped index ------------------------------------------------------
SHIPPED = Path(__file__).resolve().parents[1] / "web" / "public" / "taxon-index.json"


@pytest.mark.skipif(not SHIPPED.is_file(), reason="taxon-index.json not built")
def test_the_shipped_index_has_the_shape_the_frontend_parses() -> None:
    """One command writes this file, and a second one used to overwrite it with another shape.

    `taxonomy build-index` built a thirty-animal seed list as a bare JSON array, and `make
    taxon-index` invoked it. Running that target replaced a 3,073-taxon index with something
    `web/src/search/taxon.ts` cannot read -- silently, since nothing type-checks a JSON file
    across two languages. The command is gone; this is what stops it coming back.
    """
    document = json.loads(SHIPPED.read_text(encoding="utf-8"))
    assert isinstance(document, dict), "the index is a bare array, so a seed builder wrote it"
    assert document["shards"] == tile_species.SHARDS
    assert document["taxa"], "the index is empty"
    for taxon in document["taxa"]:
        assert set(taxon) == {
            "key",
            "scientific",
            "vernacular",
            "layer",
            "layer_title",
            "cells",
            "shard",
        }
        assert taxon["shard"] == taxon["key"] % tile_species.SHARDS


@pytest.mark.skipif(not SHIPPED.is_file(), reason="taxon-index.json not built")
def test_no_animal_appears_in_the_shipped_index_under_two_names() -> None:
    """A taxon may be listed once per layer that drew it, but never under two spellings."""
    spellings: dict[int, set[str]] = {}
    for taxon in json.loads(SHIPPED.read_text(encoding="utf-8"))["taxa"]:
        spellings.setdefault(taxon["key"], set()).add(taxon["scientific"])
    doubled = {key: sorted(names) for key, names in spellings.items() if len(names) > 1}
    assert not doubled, f"one animal, two names: {doubled}"
