"""The sea ice's median edge, monthly, on the globe's own clock.

The first driver drawn rather than regressed (`docs/ideas/satellite-drivers-on-the-globe.md`):
twelve monthly median ice-edge polylines per hemisphere from the Sea Ice Index, 1981-2010, a few
kilobytes each. The clock's week picks the month, so the ice breathes with the same slider that
moves the passage and the herds -- one wheel, three hands.

Two honesty notes carried into the prose rather than discovered by a reader. This is a
climatology's ice: the recent edge sits poleward of these lines in most months, and the
difference is the warming. And monthly is the finest wheel the product turns on, so the weekly
clock steps it twelve times a year rather than pretending to interpolate ice.

The gate half: a driver layer is not evidence about an animal, so the clearance is minted with
no evidence type -- and the licence check applies in full, which is the reason the gate exists
to price a layer with no animal in it at all.
"""

import json
import logging
import zipfile
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

from migratlas.catalog import loader as catalog
from migratlas.config import get_settings
from migratlas.evidence import Realm, TaxonScope
from migratlas.ingest.http import RemoteFile, fetch
from migratlas.redact import clear_for_publication

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)

SOURCE_ID: Final = "nsidc_sea_ice_index"
MONTHS: Final = tuple(range(1, 13))
HEMISPHERES: Final = (("north", "N"), ("south", "S"))

# The product is ~25 km passive microwave; two decimals (~1 km) already flatters it.
ROUND: Final = 2

LAYER_NAME: Final = "sea-ice-edge"
TITLE: Final = "The sea ice's median edge"
DESCRIPTION: Final = (
    "Where the ice edge stood in the median year of 1981-2010, month by month, both poles. "
    "A climatology's ice, not this year's: the recent edge sits poleward of these lines in "
    "most months, and the difference is the warming rather than an error. The clock steps it "
    "monthly, the finest wheel the product turns on."
)
POPUP_CAVEAT: Final = (
    "the median edge of 1981-2010 for this month — a climatology's ice, poleward of which "
    "today's edge usually sits."
)


@dataclass(frozen=True, slots=True)
class ContourExport:
    path: str
    months: int
    segments: int
    generalization: str

    @property
    def features(self) -> int:
        return self.segments


def build_ice(destination_root: Path) -> ContourExport:
    """Fetch, unproject and publish the twenty-four monthly median edges."""
    import pyproj  # noqa: PLC0415 -- geo extra, only this builder

    source = catalog.get(SOURCE_ID)
    clearance = clear_for_publication(
        source_id=source.id,
        evidence_type=None,
        realm=Realm.MARINE,
        sensitivity=source.default_sensitivity,
        taxon_scope=TaxonScope.UNATTRIBUTED,
        taxon_key=None,
        redistribution_allowed=source.redistribution.allowed,
    )

    scratch = get_settings().cache_dir / SOURCE_ID
    scratch.mkdir(parents=True, exist_ok=True)

    features: list[dict[str, object]] = []
    segments = 0
    for hemisphere, letter in HEMISPHERES:
        # EPSG:3411 north, 3412 south -- the product's own stated projections.
        unproject = pyproj.Transformer.from_crs(
            f"EPSG:{3411 if letter == 'N' else 3412}", "EPSG:4326", always_xy=True
        )
        for month in MONTHS:
            name = f"median_extent_{letter}_{month:02d}_1981-2010_polyline_v4.0.zip"
            archive = fetch(
                RemoteFile(
                    url=(
                        f"{source.download_uri}/{hemisphere}/monthly/shapefiles/shp_median/{name}"
                    ),
                    name=name,
                ),
                SOURCE_ID,
            )
            with zipfile.ZipFile(archive) as bundle:
                bundle.extractall(scratch)
            shp = scratch / name.replace(".zip", ".shp")

            lines: list[list[tuple[float, float]]] = []
            for geometry in _read_lines(shp):
                xx, yy = geometry.xy
                lon, lat = unproject.transform(list(xx), list(yy))
                run = [
                    (round(float(x), ROUND), round(float(y), ROUND))
                    for x, y in zip(lon, lat, strict=True)
                ]
                lines.extend(_split_antimeridian(run))
            segments += len(lines)
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "MultiLineString",
                        "coordinates": [[[x, y] for x, y in line] for line in lines],
                    },
                    "properties": {"month": month, "hemisphere": hemisphere},
                }
            )
    destination = destination_root / f"{LAYER_NAME}.geojson"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")),
        encoding="utf-8",
    )
    statement = (
        f"{clearance.generalization.statement()}; unprojected from the product's polar "
        f"stereographic and split at the antimeridian"
    )
    destination.with_suffix(".meta.json").write_text(
        json.dumps(
            {
                "source_id": clearance.source_id,
                "evidence_type": "driver",
                "realm": str(clearance.realm),
                "sensitivity": str(clearance.sensitivity),
                "dwc:dataGeneralizations": statement,
                "cleared_at": clearance.issued_at.isoformat(),
                "months": len(MONTHS),
                "segments": segments,
                "reduction": (
                    "Monthly median ice edge over 1981-2010, as published; nothing here is a "
                    "measurement of any particular year."
                ),
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    log.info("exported %d monthly edges (%d segments) to %s", len(features), segments, destination)
    return ContourExport(
        path=str(destination),
        months=len(MONTHS),
        segments=segments,
        generalization=statement,
    )


def _read_lines(shp: Path) -> list[Any]:
    """Every LineString in the shapefile, MultiLineStrings flattened."""
    import shapely  # noqa: PLC0415 -- geo extra, only this builder
    from pyogrio.raw import read as read_raw  # noqa: PLC0415

    _, _, wkbs, _ = read_raw(str(shp))
    out: list[Any] = []
    for wkb in wkbs:
        geometry = shapely.from_wkb(wkb)
        if geometry.geom_type == "MultiLineString":
            out.extend(geometry.geoms)
        else:
            out.append(geometry)
    return out


def _split_antimeridian(run: list[tuple[float, float]]) -> list[list[tuple[float, float]]]:
    """Break a run wherever it crosses ±180°, or the globe draws the crossing as a streak.

    A polar line unprojects into longitudes that jump from one side of the antimeridian to the
    other between neighbouring vertices; drawn naively, each jump is a horizontal line across
    the entire map. Split, both halves keep their own side.
    """
    jump = 180.0
    least = 2  # a line needs two vertices; a stranded one is dropped, not drawn
    out: list[list[tuple[float, float]]] = []
    run_start = 0
    for index in range(1, len(run)):
        if abs(run[index][0] - run[index - 1][0]) > jump:
            if index - run_start >= least:
                out.append(run[run_start:index])
            run_start = index
    if len(run) - run_start >= least:
        out.append(run[run_start:])
    return out
