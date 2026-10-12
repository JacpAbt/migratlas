"""The atlas plates' cutting, pinned without a download, and the committed files held to it.

The build fetches about 33 MB; CI exercises what could lie silently instead -- an island thinned to
nothing, a box edge inked as a shore, a camera that sees more than the file covers -- and checks
the committed plates against the registry and the size the ADR allows.
"""

import json
from pathlib import Path

import shapely

from migratlas.catalog import loader as catalog
from migratlas.tiles import plates
from migratlas.tiles.plates import PLATES, Box, cut_land, cut_lines, merged, rounded, visible_box

ROOT = Path(__file__).resolve().parents[1]
COMMITTED = ROOT / "web" / "public" / "basemap" / "plates"
BOX = Box(0.0, 10.0, 0.0, 10.0)


def test_an_island_inside_the_box_survives_its_thinning() -> None:
    """A closed ring thinned as a line has its two ends on one point, and collapsed to it."""
    island = shapely.Polygon([(4, 4), (6, 4), (6, 6), (4, 6)])
    [kept] = cut_land([island], BOX, tol=0.1)
    assert kept.area == island.area


def test_a_cut_shore_lays_its_vertices_exactly_on_the_box() -> None:
    """The atlas tells a shore from an edge by vertices equal to the box's own coordinates."""
    across = shapely.Polygon([(-5, 2), (5, 3), (5, 7), (-5, 8)])
    [kept] = cut_land([across], BOX, tol=0.01)
    on_edge = [x for x, _ in kept.exterior.coords if x == BOX.west]
    assert len(on_edge) >= 2


def test_thinning_never_takes_the_corner_the_cut_puts_back() -> None:
    """Thinned after the cut, a corner could go and leave a diagonal that would ink as a coast."""
    covering = shapely.Polygon([(-5, -5), (15, -5), (15, 15), (-5, 15)])
    [kept] = cut_land([covering], BOX, tol=3.0)
    corners = {
        (BOX.west, BOX.south),
        (BOX.east, BOX.south),
        (BOX.east, BOX.north),
        (BOX.west, BOX.north),
    }
    assert corners <= set(kept.exterior.coords)


def test_a_pond_below_a_few_pixels_is_dropped() -> None:
    pond = shapely.Polygon([(5, 5), (5.01, 5), (5.01, 5.01), (5, 5.01)])
    lake = shapely.Polygon([(2, 2), (4, 2), (4, 4), (2, 4)])
    assert len(cut_land([pond, lake], BOX, tol=0.01, smallest=0.1)) == 1


def test_a_creek_shorter_than_its_floor_is_not_drawn() -> None:
    creek = shapely.LineString([(1, 1), (1.05, 1)])
    river = shapely.LineString([(1, 2), (9, 2)])
    assert len(cut_lines([creek, river], BOX, tol=0.01, shortest=0.5)) == 1


def test_a_named_river_in_pieces_becomes_one_line() -> None:
    reaches = [
        (shapely.LineString([(0, 0), (1, 0)]), "Red Deer River"),
        (shapely.LineString([(1, 0), (2, 1)]), "Red Deer River"),
        (shapely.LineString([(5, 5), (6, 6)]), "Panther River"),
    ]
    joined = {name: line for line, name in merged(reaches)}
    assert len(merged(reaches)) == 2
    assert joined["Red Deer River"].length == reaches[0][0].length + reaches[1][0].length


def test_a_rounded_box_matches_a_rounded_vertex() -> None:
    box = rounded(Box(-117.456512, -114.04349, 51.07338, 52.20583))
    assert box == Box(-117.4565, -114.0435, 51.0734, 52.2058)


def test_the_camera_sees_wider_than_the_frame_far_north() -> None:
    """On Bylot at 70 N the spread shows about three times the frame's longitudes."""
    bylot = next(plate for plate in PLATES if plate.name == "bylot")
    seen = visible_box(bylot)
    frame = bylot.frame
    assert seen.west < frame.west
    assert seen.east > frame.east
    assert (seen.east - seen.west) > 2 * (frame.east - frame.west)


def test_every_plate_is_named_for_a_place_and_drawn_from_a_map_source() -> None:
    for plate in PLATES:
        for source_id in filter(None, (plate.land, plate.rivers)):
            assert catalog.get(source_id).cartographic, f"{plate.name} draws on {source_id}"


def test_every_committed_plate_is_current_in_shape_size_and_source() -> None:
    for plate in PLATES:
        path = COMMITTED / f"{plate.name}.geojson"
        assert path.stat().st_size <= plates.MAX_BYTES, plate.name
        document = json.loads(path.read_text(encoding="utf-8"))
        assert document["plate"] == plate.name
        assert Box(*document["box"]) == rounded(visible_box(plate))
        roles = {feature["properties"]["role"] for feature in document["features"]}
        assert "land" in roles
        assert roles <= {"land", "river", "lake"}
        assert set(document["sources"]) == {s for s in (plate.land, plate.rivers) if s}


def test_the_committed_attribution_is_the_registry_s() -> None:
    used = sorted({s for plate in PLATES for s in (plate.land, plate.rivers) if s is not None})
    committed = (COMMITTED / "ATTRIBUTION.md").read_text(encoding="utf-8")
    assert committed == plates.attribution(used)
