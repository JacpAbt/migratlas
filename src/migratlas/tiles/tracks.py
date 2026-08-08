"""Identified journeys from a low-sensitivity track source, per ADR 0011.

Lines exist because ``low`` keeps identifiers. The policy floor is 0.001°, and this builder snaps
a decimal coarser -- 0.01°, about a kilometre -- because the animals' den sites are fixed points
that years of summer fixes converge on, and a season of positions at 100 m is a den map. That is
the deliberate coarser-than-policy choice ADR 0010 requires a product to record; it is stated
here, in the layer's own prose, and in the ETHICS ledger.

A line is drawn only through days the transmitter spoke: daily median positions, split wherever
the record goes quiet for longer than a week, because a straight line across a month of silence
is a specific claim about where the animal went that nobody measured.
"""

import json
import logging
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Final

import polars as pl

from migratlas.catalog import loader as catalog
from migratlas.evidence import EvidenceType, Realm, TaxonScope
from migratlas.lake.reader import scan
from migratlas.redact import clear_for_publication, delay_cutoff
from migratlas.tiles.export import snap_expr

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)

SNAP_DEG: Final = 0.01
"""Coarser than the 0.001 policy floor, for the den reason in the module docstring."""

GAP_DAYS: Final = 7
"""Silence longer than this splits the line rather than being drawn across."""

MIN_POINTS: Final = 2


@dataclass(frozen=True, slots=True)
class TrackSpec:
    """One journeys layer, and the prose that must travel with it."""

    name: str
    source_id: str
    realm: Realm
    title: str
    description: str
    popup_caveat: str


TRACK_LAYERS: Final[tuple[TrackSpec, ...]] = (
    TrackSpec(
        name="bylot-journeys",
        source_id="movebank_bylot_fox_argos",
        realm=Realm.TERRESTRIAL,
        title="Arctic fox journeys",
        description=(
            "The paths of the Argos-collared Arctic foxes on and around Bylot Island, "
            "2007-2021, drawn from daily median positions a kilometre coarse -- deliberately "
            "coarser than policy requires, so that no den is a point on this map. Winter lines "
            "run out onto the sea ice and back, which is the journey this layer exists to show. "
            "Where the collars went, not where the species lives: a line breaks wherever a "
            "transmitter fell silent for more than a week, and the animals are the studied "
            "ones, not a sample of anything."
        ),
        popup_caveat=(
            "one animal's journeys, daily medians a kilometre coarse — where this collar went, "
            "not where the species lives, and no trend."
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class TrackExport:
    path: str
    animals: int
    segments: int
    generalization: str

    @property
    def features(self) -> int:
        return self.segments


def build_tracks(spec: TrackSpec, destination_root: Path) -> TrackExport:
    """Build one journeys layer, or refuse if the clearance cannot identify an animal."""
    source = catalog.get(spec.source_id)
    keys = {rule.taxon_key for rule in source.taxon_sensitivity}
    if len(keys) != 1:
        msg = f"{spec.source_id} names {len(keys)} taxa; a journeys layer is about one"
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
    generalization = clearance.generalization
    if generalization.drop_individual_id:
        msg = (
            f"{spec.name}: the clearance de-identifies this source, and a journeys layer is an "
            f"identified product. Publish a presence surface instead, or record a permission."
        )
        raise ValueError(msg)
    if generalization.grid_deg is not None and generalization.grid_deg > SNAP_DEG:
        msg = f"{spec.name}: {SNAP_DEG} deg is finer than the clearance's {generalization.grid_deg}"
        raise ValueError(msg)

    fixes = (
        scan(EvidenceType.TRACK, source_id=spec.source_id)
        .select("individual_id", "timestamp", "latitude", "longitude")
        .collect()
    )
    cutoff = delay_cutoff(generalization, datetime.now(UTC))
    if cutoff is not None:
        fixes = fixes.filter(pl.col("timestamp") <= cutoff)

    daily = (
        fixes.with_columns(day=pl.col("timestamp").dt.date())
        .group_by(["individual_id", "day"])
        .agg(latitude=pl.col("latitude").median(), longitude=pl.col("longitude").median())
        .with_columns(lat=snap_expr("latitude", SNAP_DEG), lon=snap_expr("longitude", SNAP_DEG))
        .sort(["individual_id", "day"])
    )

    features: list[dict[str, object]] = []
    animals = 0
    for (individual,), path in daily.group_by(["individual_id"], maintain_order=True):
        animals += 1
        for segment in _segments(path):
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[round(lon, 3), round(lat, 3)] for lon, lat in segment],
                    },
                    "properties": {
                        "individual": individual,
                        "days": len(segment),
                    },
                }
            )

    destination = destination_root / f"{spec.name}.geojson"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")),
        encoding="utf-8",
    )
    statement = (
        f"{generalization.statement()}; drawn from daily median positions snapped to "
        f"{SNAP_DEG} degrees, coarser than policy, so no den resolves to a point"
    )
    destination.with_suffix(".meta.json").write_text(
        json.dumps(
            {
                "source_id": clearance.source_id,
                "evidence_type": str(clearance.evidence_type),
                "realm": str(clearance.realm),
                "sensitivity": str(clearance.sensitivity),
                "dwc:dataGeneralizations": statement,
                "cleared_at": clearance.issued_at.isoformat(),
                "animals": animals,
                "segments": len(features),
                "reduction": (
                    "Daily median positions per animal, split across silences longer than "
                    f"{GAP_DAYS} days. Not the fixes, and not a route between them."
                ),
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    log.info("exported %d journeys from %d animals to %s", len(features), animals, destination)
    return TrackExport(
        path=str(destination),
        animals=animals,
        segments=len(features),
        generalization=statement,
    )


def _segments(path: pl.DataFrame) -> list[list[tuple[float, float]]]:
    """Split one animal's days into drawable runs, dropping consecutive same-cell days."""
    out: list[list[tuple[float, float]]] = []
    run: list[tuple[float, float]] = []
    previous_day = None
    previous_cell = None
    for row in path.iter_rows(named=True):
        day, cell = row["day"], (row["lon"], row["lat"])
        gone_quiet = previous_day is not None and (day - previous_day).days > GAP_DAYS
        if gone_quiet:
            if len(run) >= MIN_POINTS:
                out.append(_simplify(run, SNAP_DEG))
            run = []
            previous_cell = None
        if cell != previous_cell:
            run.append(cell)
        previous_day, previous_cell = day, cell
    if len(run) >= MIN_POINTS:
        out.append(_simplify(run, SNAP_DEG))
    return out


def _simplify(run: list[tuple[float, float]], epsilon: float) -> list[tuple[float, float]]:
    """Ramer-Douglas-Peucker at one cell of tolerance.

    The vertices are already snapped to cells, so a run of days walking a straight line is a
    staircase of cell centres carrying no information the endpoints do not -- and at daily
    resolution over years, most of the payload was exactly that. One cell of tolerance cannot
    displace the drawn line by more than the generalisation the coordinates already carry.
    """
    if len(run) <= MIN_POINTS:
        return run
    (x1, y1), (x2, y2) = run[0], run[-1]
    length = math.hypot(x2 - x1, y2 - y1)
    farthest, at = 0.0, 0
    for index, (x, y) in enumerate(run[1:-1], start=1):
        distance = (
            math.hypot(x - x1, y - y1)
            if length == 0
            else abs((x2 - x1) * (y1 - y) - (x1 - x) * (y2 - y1)) / length
        )
        if distance > farthest:
            farthest, at = distance, index
    if farthest <= epsilon:
        return [run[0], run[-1]]
    return _simplify(run[: at + 1], epsilon)[:-1] + _simplify(run[at:], epsilon)
