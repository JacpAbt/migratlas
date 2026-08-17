"""The ice builder's two dangerous conversions, pinned without a download.

The full build fetches twenty-four small archives; CI exercises the arithmetic that could lie
silently instead -- a crossing drawn as a streak, or a projection recalled instead of computed.
"""

import pyproj

from migratlas.tiles.ice import _split_antimeridian


def test_a_crossing_splits_rather_than_streaks() -> None:
    """A jump across ±180 drawn naively is a horizontal line across the entire map."""
    run = [(178.0, 72.0), (179.9, 72.1), (-179.8, 72.2), (-178.0, 72.3)]
    split = _split_antimeridian(run)
    assert split == [[(178.0, 72.0), (179.9, 72.1)], [(-179.8, 72.2), (-178.0, 72.3)]]


def test_a_run_with_no_crossing_is_untouched() -> None:
    run = [(10.0, 72.0), (11.0, 72.1), (12.0, 72.2)]
    assert _split_antimeridian(run) == [run]


def test_a_lone_vertex_after_a_crossing_is_not_a_line() -> None:
    run = [(179.0, 72.0), (179.9, 72.1), (-179.9, 72.2)]
    assert _split_antimeridian(run) == [[(179.0, 72.0), (179.9, 72.1)]]


def test_the_polar_stereographic_origin_is_the_pole() -> None:
    """EPSG:3411's origin is the North Pole; a wrong CRS string would land somewhere else."""
    unproject = pyproj.Transformer.from_crs("EPSG:3411", "EPSG:4326", always_xy=True)
    _, lat = unproject.transform(0.0, 0.0)
    assert abs(lat - 90.0) < 0.01
