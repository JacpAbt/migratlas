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
