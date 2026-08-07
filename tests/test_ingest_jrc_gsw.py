"""The fetch list and the read list must be the same list.

`read_cell` opens the tile named by a cell's north-west corner; `tiles_for` is the fetch side of
the same arithmetic. If the two ever use different corners, the command downloads one set of tiles
and opens another, and the first symptom is a FileNotFoundError halfway through a 185 MB fetch.
"""

import polars as pl

from migratlas.ingest import jrc_gsw


def test_the_footprint_names_the_notes_five_tiles() -> None:
    """One cell per tile the method note records, on its quarter-degree grid."""
    cells = pl.DataFrame(
        {
            "cell_lat": [-31.875, -22.125, -33.375, -24.625, -30.625],
            "cell_lon": [18.375, 24.875, 25.125, 31.875, 32.125],
        }
    )
    expected = sorted(
        f"{layer}_{tile}v1_4_2021.tif"
        for layer in jrc_gsw.LAYERS
        for tile in ("10E_30S", "20E_20S", "20E_30S", "30E_20S", "30E_30S")
    )
    assert jrc_gsw.tiles_for(cells, 0.25) == expected


def test_a_cell_touching_a_tile_edge_stays_in_the_tile_that_contains_it() -> None:
    """A cell whose top edge sits exactly on a 10-degree line resolves to the tile holding it.

    The naming ceil is discontinuous exactly there, so the case is pinned rather than assumed.
    """
    on_boundary = pl.DataFrame({"cell_lat": [-30.125], "cell_lon": [20.125]})
    assert jrc_gsw.tiles_for(on_boundary, 0.25) == [
        "change_20E_30Sv1_4_2021.tif",
        "occurrence_20E_30Sv1_4_2021.tif",
    ]
