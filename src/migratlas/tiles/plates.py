"""The atlas's plates: each one's own coast, rivers and lakes, cut to what its camera can see.

ADR 0021 replaces the globe with a drawn atlas whose plates come down to twenty kilometres across,
where the bundled 1:110m outline is a few straight lines (ADR 0005's 2026-10-12 amendment). Each
plate here names a place, the box its camera frames, and where its map comes from: Natural Earth
1:10m for the continent and for Bylot, the Norwegian Polar Institute's surveyed coast for Svalbard,
and Canada's National Hydro Network for the Ya Ha Tinda, whose rivers Natural Earth either lacks or
names by their system.

What is written is cut to what the camera can see on the spread -- the frame fitted into its widest
and a squarer sheet, unprojected -- and thinned to about a pixel at that size; a phone's tall sheet
shows more, and the atlas draws the world's outline there. The land is thinned before it is cut, so
the cut lays exact vertices on the box's edges and corners: the box is written beside the features,
and the atlas inks every segment of a ring except those lying along the box, which were straight
false shores when the first prototype inked them. One outline does for fill and coast, which halved
the files against writing the coast again as lines.

A map's outline is still published, so it still passes the gate: each source's clearance is minted
before anything is written, and the licence check applies in full -- two of the three ask for
attribution, which `ATTRIBUTION.md` beside the files carries, generated from the registry.
"""

import json
import logging
import warnings
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final, NamedTuple

from migratlas.catalog import loader as catalog
from migratlas.evidence import Realm, TaxonScope
from migratlas.ingest.http import Checksum, RemoteFile, fetch
from migratlas.redact import PublicationClearance, clear_for_publication

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)

NATURAL_EARTH: Final = "natural_earth"
SVALBARD_COAST: Final = "npi_svalbard_coastlines"
HYDRO_NETWORK: Final = "nrcan_national_hydro_network"

# Four decimals is eleven metres, finer than a pixel on the smallest plate.
ROUND: Final = 4
# A plate's file over this is the ADR's kill condition: thin harder or split it by zoom.
MAX_BYTES: Final = 600_000
# The spread's map box is about 1.95 wide; 1.2 covers a squarer window. A phone's tall leaf would
# have the continent's plate reach from the tropics to the pole -- 3.7 MB of coast nobody reads at
# that size -- so the atlas draws the world's outline beyond the box instead.
ASPECTS: Final = (2.3, 1.2)
EARTH_RADIUS_M: Final = 6_371_000.0
LEAST_VERTICES: Final = 2  # a line needs two

# The files are pinned: Natural Earth's GitHub master has no release for them, and neither the
# Polar Institute nor NRCan states a digest, so a changed upstream fails here rather than drifting.
NATURAL_EARTH_LAND: Final = RemoteFile(
    url=f"{catalog.get(NATURAL_EARTH).download_uri}/ne_10m_land.geojson",
    name="ne_10m_land.geojson",
    checksum=Checksum("sha256", "1ac90796408bc6ad6911d69448485d3c4dbf2190370080368a09976e1c9f7416"),
)
NATURAL_EARTH_RIVERS: Final = RemoteFile(
    url=f"{catalog.get(NATURAL_EARTH).download_uri}/ne_10m_rivers_lake_centerlines.geojson",
    name="ne_10m_rivers_lake_centerlines.geojson",
    checksum=Checksum("sha256", "bb854a900ecbd3b408df46d5e16e3e0f974ba55993f9d8b5c26e855273c0905a"),
)
# The 2022 coast, the year the herd's record ends; each year from 2008 is its own attachment.
SVALBARD_FILE: Final = RemoteFile(
    url=f"{catalog.get(SVALBARD_COAST).download_uri}/6f539ba634e5796f287ac46048f12549",
    name="Coast2022.zip",
    checksum=Checksum("sha256", "ec456ca71acf21a87f2b2e15f5490a8fcd3cda2e38e31e5edbf252d536f3d016"),
)
HYDRO_UNITS: Final = {
    "05ba000": "538412c09025224a18561224a28bd91f3b6da06c1f4bbc2890cc48a9eb8b65f3",
    "05bb000": "8102baf344164c161d038d9e2004b8845478a1e15f6c405ff2a26f593c9879ef",
    "05ca000": "ef4d2f5a75ae324d555a01fe21b5b68f228a968373c6dff0ee0c81eeae1c3ba8",
    "05da000": "cfd0254dd2b76fe1603db1c2f208560708e30250252b075154ca1a83126c286d",
    "05db000": "764b31d2b41aebcc5708cae4ba16ca05795414f53d28258e251d289421e6136b",
}


class Box(NamedTuple):
    """A longitude-latitude box, in degrees."""

    west: float
    east: float
    south: float
    north: float


@dataclass(frozen=True, slots=True)
class Plate:
    """One plate of the atlas: a place, what its camera frames, and where its map comes from."""

    name: str
    frame: Box
    centre: tuple[float, float]
    land: str
    rivers: str | None = None
    # Natural Earth ranks a river 1 (greatest) to 10; under the radar's strokes only the great ones.
    river_rank: int | None = None


PLATES: Final[tuple[Plate, ...]] = (
    Plate(
        name="north-america",
        frame=Box(-126.0, -65.0, 23.5, 50.5),
        centre=(-96.0, 38.0),
        land=NATURAL_EARTH,
        rivers=NATURAL_EARTH,
        river_rank=5,
    ),
    Plate(
        name="bylot",
        frame=Box(-87.0, -66.0, 64.5, 75.5),
        centre=(-77.0, 70.0),
        land=NATURAL_EARTH,
        rivers=NATURAL_EARTH,
    ),
    Plate(
        name="svalbard",
        frame=Box(13.4, 17.4, 77.6, 78.36),
        centre=(15.4, 77.97),
        land=SVALBARD_COAST,
    ),
    Plate(
        name="ya-ha-tinda",
        frame=Box(-116.75, -114.75, 51.22, 52.06),
        centre=(-115.75, 51.64),
        land=NATURAL_EARTH,
        rivers=HYDRO_NETWORK,
    ),
)


@dataclass(frozen=True, slots=True)
class PlateExport:
    path: str
    features: int
    bytes: int


# --- What a camera can see -----------------------------------------------------------------------
def visible_box(plate: Plate, aspects: tuple[float, ...] = ASPECTS, pad: float = 0.08) -> Box:
    """The longitudes and latitudes a camera framing ``plate`` shows on any of ``aspects``.

    The atlas fits the frame into its map box in the plate's Lambert azimuthal projection, so a
    sheet wider or taller than the frame shows more than the frame: on Bylot at 70 N the spread's
    sheet shows three times the frame's longitudes, and a map cut to the frame ended in a straight
    edge there.
    """
    import pyproj  # noqa: PLC0415 -- geo extra, only this builder

    lon0, lat0 = plate.centre
    laea = pyproj.Proj(proj="laea", lat_0=lat0, lon_0=lon0, R=EARTH_RADIUS_M)
    edge = [
        (lon, lat)
        for i in range(49)
        for lon, lat in (
            (plate.frame.west + (plate.frame.east - plate.frame.west) * i / 48, plate.frame.south),
            (plate.frame.west + (plate.frame.east - plate.frame.west) * i / 48, plate.frame.north),
            (
                plate.frame.west,
                plate.frame.south + (plate.frame.north - plate.frame.south) * i / 48,
            ),
            (
                plate.frame.east,
                plate.frame.south + (plate.frame.north - plate.frame.south) * i / 48,
            ),
        )
    ]
    xs, ys = laea([p[0] for p in edge], [p[1] for p in edge])
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    cx, cy, w, h = (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0

    lons: list[float] = []
    lats: list[float] = []
    for aspect in aspects:
        half_w = max(w, h * aspect) / 2 * (1 + pad)
        half_h = max(h, w / aspect) / 2 * (1 + pad)
        ring = [
            (cx + half_w * (2 * i / 48 - 1), cy + half_h * side)
            for i in range(49)
            for side in (-1, 1)
        ] + [
            (cx + half_w * side, cy + half_h * (2 * i / 48 - 1))
            for i in range(49)
            for side in (-1, 1)
        ]
        lon, lat = laea([p[0] for p in ring], [p[1] for p in ring], inverse=True)
        lons += list(lon)
        lats += list(lat)
    return Box(min(lons), max(lons), max(-89.9, min(lats)), min(89.9, max(lats)))


def tolerance(plate: Plate) -> float:
    """About a pixel at the plate's size, in degrees: its frame's latitudes over the ~750 pixels of
    height the spread gives them."""
    return (plate.frame.north - plate.frame.south) / 750


# --- Cutting and thinning ------------------------------------------------------------------------
def cut_land(polygons: list[Any], box: Box, tol: float, smallest: float = 0.0) -> list[Any]:
    """The land inside ``box``, thinned and then cut, as polygons whose rings also ink its coast.

    Thinned first, so the cut puts exact vertices on the box's edges and corners and the atlas can
    tell a shore from an edge; cut first, the thinning could take a corner and leave a diagonal
    that would ink as a coast. ``smallest`` drops what would be a few pixels across -- in the hydro
    network, thousands of ponds.
    """
    import shapely  # noqa: PLC0415 -- geo extra, only this builder

    frame = shapely.box(*_bounds(box))
    out: list[Any] = []
    for polygon in polygons:
        if not polygon.intersects(frame):
            continue
        if smallest and _diagonal(polygon) < smallest:
            continue
        thinned = polygon.simplify(tol, preserve_topology=True)
        cut = shapely.clip_by_rect(thinned, *_bounds(box))
        out += [part for part in _parts(cut) if part.geom_type == "Polygon" and not part.is_empty]
    return out


def cut_lines(lines: list[Any], box: Box, tol: float, shortest: float = 0.0) -> list[Any]:
    """Lines inside ``box``, thinned; a line leaving and coming back is two lines."""
    import shapely  # noqa: PLC0415 -- geo extra, only this builder

    out: list[Any] = []
    for line in lines:
        cut = shapely.clip_by_rect(line.simplify(tol, preserve_topology=False), *_bounds(box))
        out += [
            part
            for part in _parts(cut)
            if part.geom_type == "LineString"
            and len(part.coords) >= LEAST_VERTICES
            and part.length >= shortest
        ]
    return out


def merged(named: list[tuple[Any, str]]) -> list[tuple[Any, str]]:
    """Each name's segments joined end to end: 12,046 reaches of 2,676 names, one line a name."""
    import shapely  # noqa: PLC0415 -- geo extra, only this builder

    by_name: dict[str, list[Any]] = {}
    for line, name in named:
        by_name.setdefault(name, []).append(line)
    out: list[tuple[Any, str]] = []
    for name, lines in by_name.items():
        joined = shapely.line_merge(shapely.MultiLineString(lines))
        out += [(part, name) for part in _parts(joined) if part.geom_type == "LineString"]
    return out


def _diagonal(geometry: Any) -> float:
    west, south, east, north = geometry.bounds
    return float(((east - west) ** 2 + (north - south) ** 2) ** 0.5)


def _bounds(box: Box) -> tuple[float, float, float, float]:
    return box.west, box.south, box.east, box.north


def rounded(box: Box) -> Box:
    """The box at the files' precision, so a vertex the cut lays on an edge equals the edge."""
    return Box(*(round(v, ROUND) for v in box))


def _parts(geometry: Any) -> list[Any]:
    if geometry.is_empty:
        return []
    if hasattr(geometry, "geoms"):
        return [part for member in geometry.geoms for part in _parts(member)]
    return [geometry]


# --- The sources ---------------------------------------------------------------------------------
def _read(
    path: str, layer: str | None = None, columns: list[str] | None = None
) -> tuple[list[Any], dict[str, list[Any]]]:
    """Geometries and the named columns of one layer, flattened to two dimensions."""
    import shapely  # noqa: PLC0415 -- geo extra, only this builder
    from pyogrio.raw import read as read_raw  # noqa: PLC0415

    with warnings.catch_warnings():
        # The hydro network's lines carry measures, which GDAL reads as 3D and says so.
        warnings.simplefilter("ignore", UserWarning)
        meta, _, wkbs, fields = read_raw(path, layer=layer, columns=columns)
    geometries = [shapely.force_2d(shapely.from_wkb(wkb)) for wkb in wkbs]
    names = list(meta["fields"])
    return geometries, {name: list(fields[names.index(name)]) for name in columns or []}


def _layer(archive: Path, suffix: str) -> str:
    """The one layer in a hydro work unit whose name ends suffix.

    Matched by suffix because a work unit's layers carry its edition -- `NHN_05CA000_1_0_...` but
    `NHN_05DA000_1_1_...` -- and naming the edition broke on the first unit that had moved on.
    """
    import pyogrio  # noqa: PLC0415 -- geo extra, only this builder

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        listed = pyogrio.list_layers(f"/vsizip/{archive}")
    found = [name for name, _ in listed if name.endswith(suffix)]
    if len(found) != 1:
        msg = f"{archive.name} has {len(found)} layers ending {suffix!r}, expected one"
        raise ValueError(msg)
    return str(found[0])


def _transformed(geometries: list[Any], crs: str) -> list[Any]:
    """Geometries carried from ``crs`` into longitude and latitude."""
    import pyproj  # noqa: PLC0415 -- geo extra, only this builder
    import shapely.ops  # noqa: PLC0415

    to_lonlat = pyproj.Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    return [shapely.ops.transform(to_lonlat.transform, geometry) for geometry in geometries]


def _polygons(geometries: list[Any]) -> list[Any]:
    return [
        part for geometry in geometries for part in _parts(geometry) if part.geom_type == "Polygon"
    ]


def _lines(geometries: list[Any]) -> list[Any]:
    return [
        part
        for geometry in geometries
        for part in _parts(geometry)
        if part.geom_type == "LineString"
    ]


class _Sources:
    """Each source fetched and read once, however many plates draw on it."""

    def __init__(self) -> None:
        self._land: dict[str, list[Any]] = {}
        self._ranked: list[tuple[Any, float]] | None = None
        self._hydro: tuple[list[tuple[Any, str]], list[Any]] | None = None

    def land(self, source_id: str) -> list[Any]:
        if source_id not in self._land:
            if source_id == NATURAL_EARTH:
                self._land[source_id] = _polygons(
                    _read(str(fetch(NATURAL_EARTH_LAND, NATURAL_EARTH)))[0]
                )
            elif source_id == SVALBARD_COAST:
                path = fetch(SVALBARD_FILE, SVALBARD_COAST)
                shapes = _read(f"/vsizip/{path}", layer="Coast2022")[0]
                self._land[source_id] = _polygons(_transformed(shapes, "EPSG:32633"))
            else:
                msg = f"{source_id} is not a source of land"
                raise ValueError(msg)
        return self._land[source_id]

    def rivers(self, source_id: str, rank: int | None) -> list[tuple[Any, str]]:
        """Rivers as (line, name): a name only where a label may print it, and Natural Earth's are
        its systems' -- the Bow labelled South Saskatchewan -- so none of its are kept."""
        if source_id == NATURAL_EARTH:
            if self._ranked is None:
                path = str(fetch(NATURAL_EARTH_RIVERS, NATURAL_EARTH))
                geometries, fields = _read(path, columns=["scalerank"])
                self._ranked = [
                    (line, float(r))
                    for g, r in zip(geometries, fields["scalerank"], strict=True)
                    for line in _lines([g])
                ]
            return [(line, "") for line, r in self._ranked if rank is None or r <= rank]
        if source_id == HYDRO_NETWORK:
            return merged(self.hydro()[0])
        msg = f"{source_id} is not a source of rivers"
        raise ValueError(msg)

    def lakes(self, source_id: str) -> list[Any]:
        return self.hydro()[1] if source_id == HYDRO_NETWORK else []

    def hydro(self) -> tuple[list[tuple[Any, str]], list[Any]]:
        """The named watercourses and the water bodies of the five work units round the Ya Ha Tinda.

        Only the named watercourses: the unnamed streams are thousands of kilometres and drew the
        plate solid.
        """
        if self._hydro is None:
            named: list[tuple[Any, str]] = []
            water: list[Any] = []
            for unit, digest in HYDRO_UNITS.items():
                name = f"nhn_rhn_{unit}_shp_en.zip"
                url = f"{catalog.get(HYDRO_NETWORK).download_uri}/{name}"
                path = fetch(
                    RemoteFile(url=url, name=name, checksum=Checksum("sha256", digest)),
                    HYDRO_NETWORK,
                )
                lines, fields = _read(
                    f"/vsizip/{path}", layer=_layer(path, "_HD_SLWATER_1"), columns=["NAME_1"]
                )
                for geometry, label in zip(
                    _transformed(lines, "EPSG:4617"), fields["NAME_1"], strict=True
                ):
                    if label:
                        named += [(line, str(label)) for line in _lines([geometry])]
                bodies = _read(f"/vsizip/{path}", layer=_layer(path, "_HD_WATERBODY_2"))[0]
                water += _polygons(_transformed(bodies, "EPSG:4617"))
            self._hydro = (named, water)
        return self._hydro


# --- Writing -------------------------------------------------------------------------------------
def _coords(geometry: Any) -> list[list[float]]:
    return [[round(x, ROUND), round(y, ROUND)] for x, y in geometry.coords]


def feature(role: str, geometry: Any, **properties: object) -> dict[str, object]:
    """One GeoJSON feature: a polygon's outer ring and holes, or a line."""
    if geometry.geom_type == "Polygon":
        shape: dict[str, object] = {
            "type": "Polygon",
            "coordinates": [
                _coords(geometry.exterior),
                *(_coords(ring) for ring in geometry.interiors),
            ],
        }
    else:
        shape = {"type": "LineString", "coordinates": _coords(geometry)}
    return {"type": "Feature", "properties": {"role": role, **properties}, "geometry": shape}


def _clearance(source_id: str) -> PublicationClearance:
    source = catalog.get(source_id)
    return clear_for_publication(
        source_id=source.id,
        evidence_type=None,
        realm=Realm.TERRESTRIAL,
        sensitivity=source.default_sensitivity,
        taxon_scope=TaxonScope.UNATTRIBUTED,
        taxon_key=None,
        redistribution_allowed=source.redistribution.allowed,
    )


def build_plates(destination: Path) -> list[PlateExport]:
    """Fetch, cut and write every plate's map, and the credits its sources ask for."""
    used = sorted({s for plate in PLATES for s in (plate.land, plate.rivers) if s is not None})
    # Every clearance before any file, so a refusal leaves nothing half-published behind it.
    for source_id in used:
        _clearance(source_id)

    destination.mkdir(parents=True, exist_ok=True)
    sources = _Sources()
    exports: list[PlateExport] = []
    for plate in PLATES:
        box, tol = rounded(visible_box(plate)), tolerance(plate)
        features = [feature("land", g) for g in cut_land(sources.land(plate.land), box, tol)]
        if plate.rivers is not None:
            for geometry, name in sources.rivers(plate.rivers, plate.river_rank):
                # A creek is drawn but not named; a label is for a river a reader can follow.
                major = " River" in name
                labelled = {"name": name, "major": True} if major else {}
                lines = cut_lines([geometry], box, tol, shortest=0 if major else 8 * tol)
                features += [feature("river", line, **labelled) for line in lines]
            water = cut_land(sources.lakes(plate.rivers), box, tol, smallest=4 * tol)
            features += [feature("lake", g) for g in water]

        payload = json.dumps(
            {
                "type": "FeatureCollection",
                "plate": plate.name,
                "box": list(box),
                "sources": sorted({plate.land, *([plate.rivers] if plate.rivers else [])}),
                "features": features,
            },
            separators=(",", ":"),
        ).encode("utf-8")
        if len(payload) > MAX_BYTES:
            msg = f"{plate.name} is {len(payload):,} bytes, past the {MAX_BYTES:,} ADR 0021 allows"
            raise ValueError(msg)
        path = destination / f"{plate.name}.geojson"
        path.write_bytes(payload)
        exports.append(PlateExport(path=str(path), features=len(features), bytes=len(payload)))
        log.info("%s: %d features, %.0f KiB", plate.name, len(features), len(payload) / 1024)

    (destination / "ATTRIBUTION.md").write_bytes(attribution(used).encode("utf-8"))
    return exports


def attribution(source_ids: list[str]) -> str:
    """The credits the plates' sources ask for, from the registry, so they cannot drift from it."""
    lines = [
        "# The atlas's plates: where each map comes from",
        "",
        "Generated by `migratlas build-plates` from the registry -- edit",
        "`src/migratlas/catalog/registry.yaml`, not this file. Each plate names its sources.",
        "",
    ]
    for source_id in source_ids:
        source = catalog.get(source_id)
        licence = (
            f"[{source.licence}]({source.licence_url})" if source.licence_url else source.licence
        )
        lines += [
            f"## {source.title}",
            "",
            f"- licence: {licence}",
            f"- cite as: {source.citation.strip()}",
            "",
        ]
    return "\n".join(lines)
