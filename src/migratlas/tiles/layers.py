"""Build the globe's published layers from the lake.

Each layer resolves its source in the registry, asks the gate for a clearance, and hands
that clearance to the exporter. There is no path from lake to web that skips the gate.
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import polars as pl

from migratlas.catalog import loader as catalog
from migratlas.config import get_settings
from migratlas.evidence import EvidenceType, Realm, TaxonScope
from migratlas.lake.reader import scan
from migratlas.redact import clear_for_publication
from migratlas.tiles.export import ExportResult, export_surface

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)

# A globe layer is a single fetch, so it has to stay small. MegaMove's one-degree grid is
# ~29k cells and fits comfortably; anything at H3 resolution needs aggregating first.
MAX_FEATURES: Final = 60_000


@dataclass(frozen=True, slots=True)
class LayerSpec:
    """One publishable layer."""

    name: str
    source_id: str
    evidence_type: EvidenceType
    realm: Realm
    title: str
    description: str


LAYERS: Final[tuple[LayerSpec, ...]] = (
    LayerSpec(
        name="marine-space-use",
        source_id="megamove",
        evidence_type=EvidenceType.ABUNDANCE_SURFACE,
        realm=Realm.MARINE,
        title="Marine megafauna space use",
        description=(
            "Tracked individuals per one-degree cell, 1985-2018, pooled across 121 species. "
            "Reflects research effort as much as animal distribution."
        ),
    ),
)


def _surface_for(source_id: str, *, taxon_key: int | None = None) -> pl.DataFrame:
    """Read one source's abundance surface from the lake."""
    frame = scan(EvidenceType.ABUNDANCE_SURFACE, source_id=source_id)
    if taxon_key is not None:
        frame = frame.filter(pl.col("taxon_key") == taxon_key)
    else:
        # Pooling across taxa: only the aggregate rows, or every species would be counted
        # once per taxon *and* once in its group total.
        frame = frame.filter(pl.col("taxon_scope") == TaxonScope.AGGREGATE.value)
    return frame.collect()


def build(layer: LayerSpec, destination_root: Path | None = None) -> ExportResult:
    """Export one layer, gated.

    The clearance is minted here from the registry's classification, so a source whose
    sensitivity changes cannot keep publishing at the old resolution.
    """
    source = catalog.get(layer.source_id)
    frame = _surface_for(layer.source_id)
    if frame.is_empty():
        msg = f"No rows in the lake for {layer.source_id!r}. Ingest it first."
        raise ValueError(msg)

    clearance = clear_for_publication(
        source_id=source.id,
        evidence_type=layer.evidence_type,
        realm=layer.realm,
        # Pooled across taxa, so the source default governs rather than any one species.
        sensitivity=source.default_sensitivity,
        taxon_scope=TaxonScope.AGGREGATE,
        taxon_key=None,
    )

    root = destination_root or (get_settings().tiles_dir / "layers")
    result = export_surface(frame, clearance, root / f"{layer.name}.geojson")

    if result.rows_out > MAX_FEATURES:
        log.warning(
            "%s has %d features, above the %d single-fetch budget -- needs tiling",
            layer.name,
            result.rows_out,
            MAX_FEATURES,
        )
    return result


def build_all(destination_root: Path | None = None) -> list[ExportResult]:
    """Export every registered layer."""
    return [build(layer, destination_root) for layer in LAYERS]


def manifest() -> list[dict[str, object]]:
    """Layer metadata for the frontend, including the citation it must display."""
    entries: list[dict[str, object]] = []
    for layer in LAYERS:
        source = catalog.get(layer.source_id)
        entries.append(
            {
                "name": layer.name,
                "title": layer.title,
                "description": layer.description,
                "realm": str(layer.realm),
                "evidence_type": str(layer.evidence_type),
                "value_kind": _value_kind(layer.source_id),
                "attribution": source.citation.strip(),
                "licence": source.licence,
                "landing_page": str(source.landing_page),
                "caveats": source.caveats.strip(),
            }
        )
    return entries


def _value_kind(source_id: str) -> str:
    """What the layer's numbers actually are, read from the data rather than assumed."""
    kinds = (
        scan(EvidenceType.ABUNDANCE_SURFACE, source_id=source_id)
        .select("value_kind")
        .unique()
        .collect()["value_kind"]
        .to_list()
    )
    return kinds[0] if len(kinds) == 1 else "mixed"


__all__ = ["LAYERS", "LayerSpec", "build", "build_all", "manifest"]
