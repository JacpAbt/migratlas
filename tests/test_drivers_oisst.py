"""The OISST index arithmetic, pinned against the file's own grid definition."""

from migratlas.drivers.oisst import quarter_slice, to_file_longitude

LAT_FIRST = -89.875
LON_FIRST = 0.125


def test_the_bottom_cell_starts_at_index_zero() -> None:
    assert quarter_slice(-89.5, LAT_FIRST) == slice(0, 4)


def test_a_northern_cell_lands_on_its_own_quarters() -> None:
    # Cell centre 50.5°N spans 50.0-51.0; index 560 is 50.125, the first quarter inside it.
    s = quarter_slice(50.5, LAT_FIRST)
    assert s == slice(560, 564)
    assert LAT_FIRST + 0.25 * s.start == 50.125


def test_western_longitudes_shift_into_the_file_convention() -> None:
    assert to_file_longitude(-115.5) == 244.5
    assert to_file_longitude(15.5) == 15.5
    s = quarter_slice(to_file_longitude(-115.5), LON_FIRST)
    assert s == slice(976, 980)
    assert LON_FIRST + 0.25 * s.start == 244.125
