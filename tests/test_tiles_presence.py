"""The herd surface's three refusals, each tested at the seam where it fires.

The full build needs a lake, so CI exercises the parts that decide whether anything may be
published at all: the grid floor, the visibility bar, and the cell label that is all an id-less
surface may say about a place.
"""

from pathlib import Path

import polars as pl
import pytest

from migratlas.evidence import Realm
from migratlas.tiles.presence import (
    PRESENCE_LAYERS,
    PresenceSpec,
    _cell_label,
    _require_visible,
    build_presence,
)


def _spec(**overrides: object) -> PresenceSpec:
    base = {
        "name": "test-herd",
        "source_id": "movebank_yahatinda_elk",
        "realm": Realm.TERRESTRIAL,
        "title": "t",
        "description": "d",
        "popup_caveat": "c",
        "cell_deg": 0.01,
    }
    base.update(overrides)
    return PresenceSpec(**base)  # type: ignore[arg-type]


def test_a_cell_finer_than_the_clearance_floor_is_refused(tmp_path: Path) -> None:
    """The policy is a floor, and arithmetic must not route around the gate."""
    with pytest.raises(ValueError, match="finer than the clearance"):
        build_presence(_spec(cell_deg=0.001), tmp_path)


def test_a_static_herd_fails_the_visibility_bar() -> None:
    """ADR 0010: a static blob captioned as movement is an overclaim drawn instead of written."""
    still = pl.DataFrame(
        {
            "week": list(range(52)),
            "cell_lat": [51.005] * 52,
            "cell_lon": [-115.005] * 52,
        }
    )
    with pytest.raises(ValueError, match="does not clear"):
        _require_visible(_spec(), still)


def test_a_moving_herd_clears_the_visibility_bar() -> None:
    moving = pl.DataFrame(
        {
            "week": [0, 13, 26, 39],
            "cell_lat": [51.005, 51.005, 51.105, 51.005],
            "cell_lon": [-115.005, -115.005, -115.105, -115.005],
        }
    )
    _require_visible(_spec(), moving)


def test_the_cell_label_is_a_position_and_nothing_else() -> None:
    frame = pl.DataFrame({"lat": [51.715, -33.375], "lon": [-115.535, 25.125]})
    labels = frame.select(out=_cell_label(pl.col("lat"), pl.col("lon")))["out"].to_list()
    # 25.125 sits a hair below .125 in binary, so round-half-even gives .12. The label is a
    # name, not arithmetic, and the pin is to what the machine actually prints.
    assert labels == ["51.72°N 115.54°W", "33.38°S 25.12°E"]


def test_every_registered_surface_sits_on_or_above_its_policy_floor() -> None:
    """MODERATE's floor is 0.01; a registered spec below it would refuse on every build."""
    for spec in PRESENCE_LAYERS:
        assert spec.cell_deg >= 0.01
