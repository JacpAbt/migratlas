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
from migratlas.evidence import EvidenceType, Realm, TaxonScope, spec_for
from migratlas.lake.reader import scan
from migratlas.metrics.phenology import NORTHERN_AUTUMN, passage_quantiles, passage_trends
from migratlas.redact import clear_for_publication
from migratlas.tiles.export import ExportResult, export_surface
from migratlas.tiles.station_series import SeriesExport, export_station_series

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)

# A globe layer is a single fetch, so it has to stay small. MegaMove's one-degree grid is
# ~29k cells and fits comfortably; anything at H3 resolution needs aggregating first.
MAX_FEATURES: Final = 60_000

# A night the radar only watched part of is not comparable to a full one, and a weekly median
# built from a mix of both is biased toward whenever coverage happened to be good.
MIN_COVERAGE: Final = 0.9

# The published thresholds from docs/methods/phase1-phenology.md. A layer must not quietly
# apply looser ones than the report it derives from.
MIN_NIGHTS_PER_SEASON: Final = 40
MIN_YEARS_FOR_TREND: Final = 15


@dataclass(frozen=True, slots=True)
class LayerSpec:
    """One publishable layer."""

    name: str
    source_id: str
    evidence_type: EvidenceType
    realm: Realm
    title: str
    description: str


SERIES_LAYERS: Final[tuple[LayerSpec, ...]] = (
    LayerSpec(
        name="aerial-passage",
        source_id="darkecology_daily",
        evidence_type=EvidenceType.FLUX,
        realm=Realm.AERIAL,
        title="Nightly aerial passage",
        description=(
            "Weekly median of nightly reflectivity traffic past US weather radars, pooled "
            "across 1995-2025, with each station's shift in autumn passage date. Aerial "
            "biomass, not birds: the radar does not separate birds from bats from insects. "
            "The autumn window is a northern-hemisphere one, so the shift means little at "
            "the tropical stations."
        ),
    ),
)

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


def build_series(layer: LayerSpec, destination_root: Path | None = None) -> SeriesExport:
    """Export one station time-series layer, gated."""
    source = catalog.get(layer.source_id)
    nights = (
        scan(EvidenceType.FLUX, source_id=layer.source_id)
        .filter(
            pl.col("window_kind") == "night",
            pl.col("quantity") == "reflectivity_traffic",
            pl.col("coverage_fraction").is_null() | (pl.col("coverage_fraction") >= MIN_COVERAGE),
        )
        .select("station_id", "timestamp", "magnitude", "station_longitude", "station_latitude")
        .collect()
    )
    if nights.is_empty():
        msg = f"No rows in the lake for {layer.source_id!r}. Ingest it first."
        raise ValueError(msg)

    clearance = clear_for_publication(
        source_id=source.id,
        evidence_type=layer.evidence_type,
        realm=layer.realm,
        sensitivity=source.default_sensitivity,
        # The radar measures aerial biomass, so there is no taxon to attribute.
        taxon_scope=TaxonScope.UNATTRIBUTED,
        taxon_key=None,
    )
    root = destination_root or (get_settings().tiles_dir / "layers")
    return export_station_series(
        nights,
        clearance,
        root / f"{layer.name}.geojson",
        annotations=_passage_shift(nights),
    )


def _passage_shift(nights: pl.DataFrame) -> pl.DataFrame:
    """Per-station autumn passage-date shift, in days per decade.

    Autumn and not spring, and passage date and not magnitude, because those are the only
    numbers Phase 1 could defend. The spring trend sits inside its own permutation null and
    flips sign across break specifications; a magnitude trend runs straight across the
    NEXRAD dual-polarisation upgrade with nothing to separate the instrument from the
    animals. Publishing either on a globe would be publishing noise attractively.
    """
    quantiles = passage_quantiles(
        nights,
        spec_for(EvidenceType.FLUX),
        seasons=[NORTHERN_AUTUMN],
        quantiles=(0.5,),
        min_coverage=MIN_COVERAGE,
        min_observations=MIN_NIGHTS_PER_SEASON,
    )
    trends = passage_trends(quantiles, columns=("q50_doy",), min_years=MIN_YEARS_FOR_TREND)
    if trends.is_empty():
        log.warning("no station cleared the trend thresholds; publishing the cycle alone")
        return pl.DataFrame({"station_id": [], "autumn_shift_days_per_decade": []})
    return trends.select(
        "station_id",
        pl.col("days_per_decade").round(2).alias("autumn_shift_days_per_decade"),
        pl.col("years").alias("trend_years"),
    )


def build_all(destination_root: Path | None = None) -> list[ExportResult | SeriesExport]:
    """Export every registered layer."""
    results: list[ExportResult | SeriesExport] = [
        build(layer, destination_root) for layer in LAYERS
    ]
    results += [build_series(layer, destination_root) for layer in SERIES_LAYERS]
    return results


def manifest() -> list[dict[str, object]]:
    """Layer metadata for the frontend, including the citation it must display."""
    entries: list[dict[str, object]] = []
    for layer in (*LAYERS, *SERIES_LAYERS):
        source = catalog.get(layer.source_id)
        entries.append(
            {
                "name": layer.name,
                "title": layer.title,
                "description": layer.description,
                "realm": str(layer.realm),
                "evidence_type": str(layer.evidence_type),
                "kind": "series" if layer in SERIES_LAYERS else "surface",
                "value_kind": _value_kind(layer.source_id)
                if layer in LAYERS
                else "reflectivity_traffic",
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


__all__ = [
    "LAYERS",
    "SERIES_LAYERS",
    "LayerSpec",
    "build",
    "build_all",
    "build_series",
    "manifest",
]
