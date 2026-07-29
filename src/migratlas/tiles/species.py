"""Per-species surfaces, so selecting an animal in the search box shows where it goes.

The published layers are pooled -- one surface across 121 marine species, one count of taxa per
cell -- which makes them unfilterable by species. That is the right shape for an overview and the
wrong shape for "where does the leatherback turtle go", so this module publishes one grid per
taxon alongside them.

It is also the first place the ethics gate does the job it was designed for. Every other export
mints one clearance for a pooled surface and uses the source default. Here a clearance is minted
**per taxon**, so a species classified sensitive in the registry is coarsened or withheld
individually, while the rest publish at full resolution. Nothing about that is special-cased: it
falls out of passing the taxon's own key to ``clear_for_publication``.

Sharded rather than one file per species. 3,523 OBIS taxa at one degree is 9.1 MiB, which is too
much to fetch eagerly and too many files to commit individually; a shard keyed on the taxon brings
a selection down to one bounded request.
"""

import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import polars as pl

from migratlas.catalog import loader as catalog
from migratlas.config import get_settings
from migratlas.evidence import EvidenceType, TaxonScope
from migratlas.lake.reader import scan
from migratlas.redact import PublicationRefusedError, clear_for_publication
from migratlas.tiles.export import snap_expr

if TYPE_CHECKING:
    from pathlib import Path

    from migratlas.tiles.layers import LayerSpec

log = logging.getLogger(__name__)

# One degree, matching every published surface. OBIS is native H3 level 7 and is snapped here.
CELL_DEG: Final = 1.0

# Sixty-four shards puts OBIS's 9.1 MiB into ~145 KiB pieces, which is the same order as a
# published layer. The count is in the manifest so the frontend does not hard-code it.
SHARDS: Final = 64

# A taxon on one or two cells is a dot: not wrong, but it tells a viewer nothing and it costs a
# search-index entry. Reported rather than silently dropped.
MIN_CELLS: Final = 3


@dataclass(frozen=True, slots=True)
class SpeciesEntry:
    """One searchable taxon and where its surface lives."""

    taxon_key: int
    scientific_name: str
    layer: str
    layer_title: str
    """Carried into the index so a taxon present in two layers gives two distinguishable rows."""
    cells: int
    shard: int
    generalization: str


@dataclass(frozen=True, slots=True)
class SpeciesExport:
    entries: list[SpeciesEntry]
    shards: int
    withheld: list[str]
    too_small: int


def per_taxon_cells(source_id: str) -> pl.DataFrame:
    """Non-zero cells per taxon at one degree.

    ``value > 0`` matters more than it looks: MegaMove stores a dense grid per species, so 187,624
    of its 234,432 pooled rows are zeros, and a species surface built without the filter would be
    a rectangle covering every ocean.
    """
    return (
        scan(EvidenceType.ABUNDANCE_SURFACE, source_id=source_id)
        .filter(
            pl.col("taxon_scope") == TaxonScope.EXACT.value,
            pl.col("value") > 0,
            pl.col("taxon_key").is_not_null(),
        )
        .select(
            taxon_key=pl.col("taxon_key"),
            taxon_label=pl.col("taxon_label"),
            cell_longitude=snap_expr("cell_longitude", CELL_DEG),
            cell_latitude=snap_expr("cell_latitude", CELL_DEG),
            value=pl.col("value"),
        )
        # Snapping H3 cells into a degree merges many into one, so the values recombine. Summed
        # rather than averaged: OBIS values are occurrence counts, which do add.
        .group_by("taxon_key", "taxon_label", "cell_longitude", "cell_latitude")
        .agg(pl.col("value").sum().alias("value"))
        .collect()
    )


def _grid(frame: pl.DataFrame, grid_deg: float) -> dict[str, object]:
    """One taxon's cells as index arrays, in the same encoding as a published layer."""
    half = grid_deg / 2
    indexed = frame.select(
        x=((pl.col("cell_longitude") - half + 180.0) / grid_deg).round().cast(pl.Int32),
        y=((pl.col("cell_latitude") - half + 90.0) / grid_deg).round().cast(pl.Int32),
        v=pl.col("value").round(3),
    ).sort("y", "x")
    return {
        "x": indexed["x"].to_list(),
        "y": indexed["y"].to_list(),
        "v": indexed["v"].to_list(),
    }


def build(layers: tuple[LayerSpec, ...], destination_root: Path | None = None) -> SpeciesExport:
    """Write per-taxon grids for every layer whose source carries per-species rows.

    Each taxon gets its own clearance. A species the registry classifies as sensitive is
    coarsened or refused on its own terms while its neighbours publish untouched, which is the
    behaviour the per-taxon sensitivity table was built for and which no pooled export can show.
    """
    root = destination_root or (get_settings().tiles_dir / "layers")
    root.mkdir(parents=True, exist_ok=True)

    shards: dict[int, dict[str, object]] = defaultdict(dict)
    entries: list[SpeciesEntry] = []
    withheld: list[str] = []
    too_small = 0

    for layer in layers:
        source = catalog.get(layer.source_id)
        if not source.redistribution.allowed:
            log.info("%s: licence forbids redistribution, no species surfaces", layer.source_id)
            continue

        cells = per_taxon_cells(layer.source_id)
        if cells.is_empty():
            log.info("%s: no per-species rows", layer.source_id)
            continue

        for (taxon_key, taxon_label), group in cells.group_by(
            ["taxon_key", "taxon_label"], maintain_order=True
        ):
            key = int(taxon_key)
            try:
                clearance = clear_for_publication(
                    source_id=source.id,
                    evidence_type=layer.evidence_type,
                    realm=layer.realm,
                    # The taxon's own classification if the registry has one, else the source
                    # default. This is the line that makes the gate per-species.
                    sensitivity=source.sensitivity_for(
                        taxon_key=key, evidence_type=layer.evidence_type, realm=layer.realm
                    ),
                    taxon_scope=TaxonScope.EXACT,
                    taxon_key=key,
                    redistribution_allowed=source.redistribution.allowed,
                )
            except PublicationRefusedError as refusal:
                withheld.append(f"{taxon_label} ({refusal})")
                continue

            # A clearance that coarsens overrides the layer's own resolution, exactly as it does
            # for a pooled surface.
            grid_deg = clearance.generalization.grid_deg or CELL_DEG
            snapped = (
                group.with_columns(
                    cell_longitude=snap_expr("cell_longitude", grid_deg),
                    cell_latitude=snap_expr("cell_latitude", grid_deg),
                )
                .group_by("cell_longitude", "cell_latitude")
                .agg(pl.col("value").sum().alias("value"))
                if grid_deg != CELL_DEG
                else group
            )
            if snapped.height < MIN_CELLS:
                too_small += 1
                continue

            shard = key % SHARDS
            payload = _grid(snapped, grid_deg)
            payload["cell_size_deg"] = grid_deg
            payload["layer"] = layer.name
            shards[shard][str(key)] = payload
            entries.append(
                SpeciesEntry(
                    taxon_key=key,
                    scientific_name=str(taxon_label),
                    layer=layer.name,
                    layer_title=layer.title,
                    cells=snapped.height,
                    shard=shard,
                    generalization=clearance.generalization.statement(),
                )
            )

    for shard in range(SHARDS):
        path = root / f"species-{shard:02d}.json"
        path.write_text(json.dumps(shards.get(shard, {}), separators=(",", ":")), encoding="utf-8")

    if withheld:
        log.warning("%d taxa withheld by the gate: %s", len(withheld), "; ".join(withheld[:5]))
    if too_small:
        log.info("%d taxa below the %d-cell floor, not published", too_small, MIN_CELLS)
    log.info("%d taxon surfaces across %d shards", len(entries), SHARDS)
    return SpeciesExport(entries=entries, shards=SHARDS, withheld=withheld, too_small=too_small)


def _vernacular_cache() -> Path:
    return get_settings().cache_dir / "vernaculars.json"


def vernaculars() -> dict[int, str]:
    """Cached common names. Reads only -- never fetches during a build.

    A search box matching scientific names alone is close to useless, since nobody types
    ``Physeter macrocephalus``, so the names are worth two GBIF calls per taxon. But 3,600 taxa is
    ~7,200 requests and twenty minutes, which has no business inside ``build-layers``: the build
    should be offline and deterministic. ``warm_vernaculars`` does the fetching as its own step and
    this reads whatever it has produced so far.
    """
    cache = _vernacular_cache()
    if not cache.exists():
        return {}
    known = json.loads(cache.read_text(encoding="utf-8"))
    return {int(key): str(name) for key, name in known.items() if name}


def warm_vernaculars(keys: list[int], *, flush_every: int = 100) -> int:
    """Fetch missing common names into the cache. Resumable, returns how many were added.

    Flushed periodically rather than once at the end: this is twenty minutes of network for a few
    thousand taxa, and an earlier version that wrote only on completion would have thrown away
    every lookup if the last request failed.
    """
    from migratlas.taxonomy import gbif  # noqa: PLC0415 -- keeps the tiles layer import-light

    cache = _vernacular_cache()
    known: dict[str, str] = {}
    if cache.exists():
        known = {str(k): str(v) for k, v in json.loads(cache.read_text(encoding="utf-8")).items()}

    missing = [key for key in keys if str(key) not in known]
    if not missing:
        log.info("all %d taxa already have a cached name decision", len(keys))
        return 0

    cache.parent.mkdir(parents=True, exist_ok=True)

    def flush() -> None:
        cache.write_text(json.dumps(known, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    log.info("resolving %d common names against GBIF", len(missing))
    with gbif.client() as http:
        for index, key in enumerate(missing, start=1):
            try:
                # An empty string is a real answer -- GBIF has no English name for this taxon --
                # and caching it stops the next run asking again.
                known[str(key)] = gbif.vernacular_name(http, key) or ""
            except (gbif.TaxonomyError, OSError) as error:
                log.debug("no common name for %d: %s", key, error)
                known[str(key)] = ""
            if index % flush_every == 0:
                flush()
                log.info("  %d/%d", index, len(missing))
    flush()
    return len(missing)


def write_index(export: SpeciesExport, destination: Path) -> int:
    """Write the search index the frontend loads, built from what was actually published.

    Replaces a hand-written seed list of thirty animals. Every entry here has a surface behind it,
    so a search hit can never be a dead end -- which the previous index could not promise.
    """
    names = vernaculars()
    payload = [
        {
            "key": entry.taxon_key,
            "scientific": entry.scientific_name,
            "vernacular": names.get(entry.taxon_key, ""),
            "layer": entry.layer,
            "layer_title": entry.layer_title,
            "cells": entry.cells,
            "shard": entry.shard,
        }
        # Widest-ranging first: with 3,600 taxa the order of equally-good matches decides what a
        # viewer sees, and a species on 9,000 cells is a better first answer than one on three.
        for entry in sorted(export.entries, key=lambda e: -e.cells)
    ]
    named = sum(1 for taxon in payload if taxon["vernacular"])
    if named < len(payload):
        log.info(
            "%d of %d taxa have a common name; run `make taxon-names` to resolve the rest",
            named,
            len(payload),
        )

    body = json.dumps(
        {"shards": export.shards, "taxa": payload}, ensure_ascii=False, separators=(",", ":")
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(body + "\n", encoding="utf-8")
    return len(body)
