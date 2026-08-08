"""Weekly presence surfaces from the tracked herds, per ADR 0010 as amended by ADR 0011.

One feature per cell centre carrying the same property contract as the radar stations --
``w0``..``w51``, ``peak``, ``years`` -- so the frontend that animates passage animates a herd
unchanged. The value is the number of distinct collared animals in the cell that week of year,
median across years like every other climatology on the site.

Three rules from ADR 0010, enforced here rather than hoped for:

- **k >= 3 distinct animals** must stand behind a cell-week across the whole record, or it is
  not published: a cell-week holding one animal is an individual location wearing an aggregate
  hat, whatever the arithmetic says.
- **the cell must be at least as coarse as the clearance's grid.** The policy is a floor, and a
  builder choosing a finer cell would be routing around the gate with arithmetic.
- **the visibility bar**: the surviving surface's weekly centres must move by more than two
  cells across the year, or the export refuses. A static blob captioned as movement is an
  overclaim drawn instead of written -- and the bar can fail, which for the bison it would.
"""

import logging
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import polars as pl

from migratlas.catalog import loader as catalog
from migratlas.evidence import EvidenceType, Realm, TaxonScope
from migratlas.lake.reader import scan
from migratlas.redact import clear_for_publication
from migratlas.tiles.export import snap_expr
from migratlas.tiles.station_series import WEEKS, SeriesExport, export_station_series

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)

K_FLOOR: Final = 3
"""Distinct animals a cell-week needs across the record before it may publish."""

VISIBILITY_CELLS: Final = 2.0
"""Seasonal throw the surface must exceed, in cells, before it earns a place on a globe."""

KM_PER_DEGREE: Final = 111.32


@dataclass(frozen=True, slots=True)
class PresenceSpec:
    """One herd surface, and the prose that must travel with it."""

    name: str
    source_id: str
    realm: Realm
    title: str
    description: str
    popup_caveat: str
    cell_deg: float


PRESENCE_LAYERS: Final[tuple[PresenceSpec, ...]] = (
    PresenceSpec(
        name="yahatinda-herd",
        source_id="movebank_yahatinda_elk",
        realm=Realm.TERRESTRIAL,
        title="The Ya Ha Tinda herd's year",
        description=(
            "Distinct collared elk per one-hundredth-degree cell in a typical week, pooled "
            "across 2001-2024. The herd's year, not any animal's journey: every cell-week "
            "stands on at least three animals, identifiers are dropped, and who wears a collar "
            "is a research decision -- so this maps study coverage at least as much as elk. "
            "A seasonal cycle, not a trend; the trend question is answered, in the negative, "
            "in the methods notes."
        ),
        popup_caveat=(
            "collared animals in a typical week — research coverage, not abundance. The herd's "
            "year pooled across two decades, no animal's own path, and no trend."
        ),
        cell_deg=0.01,
    ),
    PresenceSpec(
        name="svalbard-herd",
        source_id="movebank_svalbard_reindeer",
        realm=Realm.TERRESTRIAL,
        title="The Svalbard herd's year",
        description=(
            "Distinct collared reindeer per one-hundredth-degree cell in a typical week, "
            "pooled across 2009-2022. The herd's year, not any animal's journey: every "
            "cell-week stands on at least three animals, identifiers are dropped, and who "
            "wears a collar is a research decision -- so this maps study coverage at least "
            "as much as reindeer. The same species as the withheld mountain caribou, and "
            "classified per source rather than per species: this population is not in that "
            "position."
        ),
        popup_caveat=(
            "collared animals in a typical week — research coverage, not abundance. The herd's "
            "year pooled across thirteen years, no animal's own path, and no trend."
        ),
        cell_deg=0.01,
    ),
)


def build_presence(spec: PresenceSpec, destination_root: Path) -> SeriesExport:
    """Build one herd surface, or refuse for one of the three stated reasons."""
    source = catalog.get(spec.source_id)
    keys = {rule.taxon_key for rule in source.taxon_sensitivity}
    if len(keys) != 1:
        msg = f"{spec.source_id} names {len(keys)} taxa; a herd surface is about one"
        raise ValueError(msg)
    taxon_key = keys.pop()

    clearance = clear_for_publication(
        source_id=source.id,
        evidence_type=EvidenceType.TRACK,
        realm=spec.realm,
        sensitivity=source.sensitivity_for(
            taxon_key, evidence_type=EvidenceType.TRACK, realm=spec.realm
        ),
        taxon_scope=TaxonScope.EXACT,
        taxon_key=taxon_key,
        redistribution_allowed=source.redistribution.allowed,
    )
    floor = clearance.generalization.grid_deg
    if floor is not None and spec.cell_deg < floor:
        msg = f"{spec.name}: cell {spec.cell_deg} is finer than the clearance's {floor} floor"
        raise ValueError(msg)

    fixes = (
        scan(EvidenceType.TRACK, source_id=spec.source_id)
        .select("individual_id", "timestamp", "latitude", "longitude")
        .collect()
    )
    weekly = fixes.with_columns(
        week=((pl.col("timestamp").dt.ordinal_day() - 1) // 7).clip(0, WEEKS - 1),
        year=pl.col("timestamp").dt.year(),
        cell_lat=snap_expr("latitude", spec.cell_deg),
        cell_lon=snap_expr("longitude", spec.cell_deg),
    )

    # The k-floor is judged on the whole record: the question is how many animals' data stands
    # behind a published cell-week, not how many happened to be there in one year.
    backing = weekly.group_by(["cell_lat", "cell_lon", "week"]).agg(
        animals=pl.col("individual_id").n_unique()
    )
    kept = weekly.join(
        backing.filter(pl.col("animals") >= K_FLOOR).drop("animals"),
        on=["cell_lat", "cell_lon", "week"],
        how="inner",
    )
    if kept.is_empty():
        msg = f"{spec.name}: nothing clears the k >= {K_FLOOR} floor"
        raise ValueError(msg)

    _require_visible(spec, kept)

    # One synthetic row per cell, year and week, valued at that year-week's distinct animals.
    # The exporter's climatology then takes the median across years, exactly as it does for the
    # radar's nightly values -- one exporter, one meta contract, one delay rule.
    yearly = kept.group_by(["cell_lat", "cell_lon", "year", "week"]).agg(
        animals=pl.col("individual_id").n_unique()
    )
    label = _cell_label(pl.col("cell_lat"), pl.col("cell_lon"))
    rows = yearly.select(
        site_id=label,
        timestamp=(
            pl.datetime(pl.col("year"), 1, 1, time_zone="UTC")
            + pl.duration(days=pl.col("week") * 7)
        ),
        animals=pl.col("animals").cast(pl.Float64),
        cell_lon="cell_lon",
        cell_lat="cell_lat",
    )
    return export_station_series(
        rows,
        clearance,
        destination_root / f"{spec.name}.geojson",
        site="site_id",
        longitude="cell_lon",
        latitude="cell_lat",
        value_column="animals",
    )


def _require_visible(spec: PresenceSpec, kept: pl.DataFrame) -> None:
    """ADR 0010's bar: the weekly centres must move by more than two cells across the year."""
    centres = (
        kept.group_by("week")
        .agg(lat=pl.col("cell_lat").mean(), lon=pl.col("cell_lon").mean())
        .to_dicts()
    )
    throw = max(
        (_km(a["lat"], a["lon"], b["lat"], b["lon"]) for a in centres for b in centres),
        default=0.0,
    )
    bar = VISIBILITY_CELLS * spec.cell_deg * KM_PER_DEGREE
    if throw <= bar:
        msg = (
            f"{spec.name}: seasonal throw {throw:.1f} km does not clear {bar:.1f} km "
            f"({VISIBILITY_CELLS} cells at {spec.cell_deg} deg) -- a static blob captioned as "
            f"movement is an overclaim, so nothing is exported"
        )
        raise ValueError(msg)
    log.info("%s: seasonal throw %.1f km against a %.1f km bar", spec.name, throw, bar)


def _km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    mean_lat = math.radians((lat1 + lat2) / 2)
    dy = (lat2 - lat1) * KM_PER_DEGREE
    dx = (lon2 - lon1) * KM_PER_DEGREE * math.cos(mean_lat)
    return math.hypot(dx, dy)


def _cell_label(lat: pl.Expr, lon: pl.Expr) -> pl.Expr:
    """A cell's name is its position, which is all an id-less surface may say about it."""
    return pl.format(
        "{}°{} {}°{}",
        lat.abs().round(2),
        pl.when(lat >= 0).then(pl.lit("N")).otherwise(pl.lit("S")),
        lon.abs().round(2),
        pl.when(lon >= 0).then(pl.lit("E")).otherwise(pl.lit("W")),
    )
