"""How this project names things, and the one name two adapters spelled differently."""

import pytest

from migratlas.lake.identifiers import cell_site_id


# --- The name of a grid cell --------------------------------------------------
def test_a_cell_is_spelled_the_same_by_everyone_who_names_it() -> None:
    """`site_id` is how a driver joins back to the evidence without matching coordinates.

    That only works if every adapter spells the cell identically, and two did not: one built the
    string in Python with `.4f` and one with polars' `round(4).cast(String)`, which drops a trailing
    zero. The same cell was `-25.6250_28.3750` in one table and `-25.625_28.375` in the other, and
    the join between them returned zero rows rather than failing.
    """
    assert cell_site_id(-25.625, 28.375) == "-25.6250_28.3750"
    assert cell_site_id(-22.0, 30.0) == "-22.0000_30.0000"


def test_the_trailing_zero_that_the_two_adapters_disagreed_about() -> None:
    """The exact shape of the bug, pinned so a 'tidier' format cannot reintroduce it."""
    assert cell_site_id(-22.125, 29.375).endswith("0")
    assert cell_site_id(-22.125, 29.375) != "-22.125_29.375"


def test_a_cell_id_survives_a_round_trip_through_float() -> None:
    """Parsed back, the id has to give the coordinates it was built from."""
    for lat, lon in ((-34.625, 17.875), (-22.125, 32.875), (0.0, -0.0)):
        text = cell_site_id(lat, lon)
        back = tuple(float(part) for part in text.split("_"))
        assert back == pytest.approx((lat, lon))
