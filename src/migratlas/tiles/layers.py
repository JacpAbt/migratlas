"""Build the globe's published layers from the lake.

Each layer resolves its source in the registry, asks the gate for a clearance, and hands
that clearance to the exporter. There is no path from lake to web that skips the gate.
"""

import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Final

import polars as pl

from migratlas.catalog import loader as catalog
from migratlas.config import get_settings
from migratlas.evidence import EvidenceType, Realm, TaxonScope, spec_for
from migratlas.lake.reader import scan
from migratlas.metrics.phenology import NORTHERN_AUTUMN, passage_quantiles, passage_trends
from migratlas.redact import clear_for_publication
from migratlas.tiles.export import ExportResult, export_surface, snap_expr
from migratlas.tiles.species import SpeciesExport
from migratlas.tiles.species import build as build_species
from migratlas.tiles.station_series import SeriesExport, export_station_series

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)

# A soft ceiling, logged not enforced. The real budget is measured in the browser
# ("the published layers stay inside the performance budget"): 45 MB heap and 172 KiB
# compressed for three layers totalling 76k cells. This number only catches an order-of-
# magnitude mistake before anyone opens a browser.
MAX_FEATURES: Final = 100_000

# A night the radar only watched part of is not comparable to a full one, and a weekly median
# built from a mix of both is biased toward whenever coverage happened to be good.
MIN_COVERAGE: Final = 0.9

# The published thresholds from docs/methods/phase1-phenology.md. A layer must not quietly
# apply looser ones than the report it derives from.
MIN_NIGHTS_PER_SEASON: Final = 40
MIN_YEARS_FOR_TREND: Final = 15


class Pooling(StrEnum):
    """How a source's rows become one pooled surface."""

    AGGREGATE_ROWS = "aggregate_rows"
    """The source publishes its own pooled total; use those rows and ignore the per-taxon ones."""

    COUNT_TAXA = "count_taxa"
    """No pooled rows exist, so pool by counting the distinct taxa recorded in each cell."""


@dataclass(frozen=True, slots=True)
class LayerSpec:
    """One publishable layer."""

    name: str
    source_id: str
    evidence_type: EvidenceType
    realm: Realm
    title: str
    description: str
    cell_size_deg: float | None = None
    """Set for a regular grid, which is then published as a grid rather than as points."""
    pool: Pooling = Pooling.AGGREGATE_ROWS
    """How to reduce a per-taxon source to one surface."""
    value_kind: str | None = None
    """What the numbers are, when pooling produces a quantity the source itself does not hold."""


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
        cell_size_deg=1.0,
    ),
    LayerSpec(
        name="marine-taxa-recorded",
        source_id="obis_speciesgrids",
        evidence_type=EvidenceType.ABUNDANCE_SURFACE,
        realm=Realm.MARINE,
        title="Marine taxa recorded",
        description=(
            "Distinct moving marine taxa with at least one record in each one-degree cell, "
            "from OBIS. Not species richness: it counts what has been observed and reported, "
            "so it maps survey effort and coastal accessibility at least as much as biology."
        ),
        # OBIS is H3 level 7, roughly 5 km, which is far finer than anything a globe shows and
        # far finer than the effort behind it justifies. Pooled onto a one-degree grid, stated.
        cell_size_deg=1.0,
        pool=Pooling.COUNT_TAXA,
        value_kind="taxa_recorded",
    ),
)


def _surface_for(layer: LayerSpec) -> pl.DataFrame:
    """Read one layer's pooled surface from the lake."""
    frame = scan(EvidenceType.ABUNDANCE_SURFACE, source_id=layer.source_id)

    if layer.pool is Pooling.AGGREGATE_ROWS:
        # Only the source's own aggregate rows, or every species would be counted once per
        # taxon *and* once in its group total.
        return frame.filter(pl.col("taxon_scope") == TaxonScope.AGGREGATE.value).collect()

    # No aggregate rows to use, so the pooled quantity is a count of taxa per cell. Summing
    # per-taxon values instead would add occurrence counts across species, which is a number
    # with no meaning -- one whale record plus a thousand plankton records is not "1001".
    #
    # Snapped to the layer's grid first: H3 cells have no lat/lon alignment, so counting
    # distinct taxa has to happen after the cells are pooled or the same taxon is counted once
    # per H3 cell it occupies.
    grid = layer.cell_size_deg or 1.0
    return (
        frame.filter(pl.col("taxon_key").is_not_null(), pl.col("value") > 0)
        .select(
            cell_longitude=snap_expr("cell_longitude", grid),
            cell_latitude=snap_expr("cell_latitude", grid),
            taxon_key=pl.col("taxon_key"),
        )
        .unique()
        .group_by("cell_longitude", "cell_latitude")
        .agg(value=pl.len())
        .with_columns(period_start=pl.lit(None, dtype=pl.Datetime("us", "UTC")))
        .collect()
    )


def build(layer: LayerSpec, destination_root: Path | None = None) -> ExportResult:
    """Export one layer, gated.

    The clearance is minted here from the registry's classification, so a source whose
    sensitivity changes cannot keep publishing at the old resolution.
    """
    source = catalog.get(layer.source_id)
    frame = _surface_for(layer)
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
        redistribution_allowed=source.redistribution.allowed,
    )

    root = destination_root or (get_settings().tiles_dir / "layers")
    result = export_surface(frame, clearance, root, layer.name, cell_size_deg=layer.cell_size_deg)

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
        redistribution_allowed=source.redistribution.allowed,
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


def build_all_species(destination_root: Path | None = None) -> SpeciesExport:
    """Per-taxon surfaces for the searchable layers, each gated on its own species."""
    return build_species(LAYERS, destination_root)


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
                "format": "grid" if layer.cell_size_deg else "geojson",
                "value_kind": layer.value_kind
                or (_value_kind(layer.source_id) if layer in LAYERS else "reflectivity_traffic"),
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
