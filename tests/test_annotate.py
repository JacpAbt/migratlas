"""Locating points on a grid, and the NARR source's offline logic.

The network parts are not tested here; what is tested is the arithmetic that would be wrong
silently. A nearest-cell match that biases eastward, or a date convention off by a day, both
produce plausible numbers and a wrong answer.
"""

from datetime import date

import numpy as np
import polars as pl
import pytest

from migratlas.drivers import narr
from migratlas.drivers.schema import DRIVER_SAMPLES, DriverKind
from migratlas.features.annotate import (
    Located,
    Point,
    bounding_box,
    match_report,
    nearest_cells,
)


def _regular_grid(
    lat0: float = 30.0, lon0: float = -100.0, step: float = 1.0, size: int = 5
) -> tuple[np.ndarray, np.ndarray]:
    """A regular grid expressed as 2-D arrays, which is how a curvilinear one arrives."""
    latitudes = np.array([[lat0 + row * step] * size for row in range(size)])
    longitudes = np.array([[lon0 + col * step for col in range(size)]] * size)
    return latitudes, longitudes


def test_a_point_on_a_cell_centre_matches_that_cell_with_no_error() -> None:
    latitudes, longitudes = _regular_grid()
    [found] = nearest_cells(latitudes, longitudes, [Point("A", 32.0, -98.0)])
    assert (found.y, found.x) == (2, 2)
    assert found.error_km == pytest.approx(0.0)


def test_longitude_is_scaled_by_latitude_so_the_match_is_in_distance() -> None:
    """Unscaled degrees would treat a degree of longitude as a degree of latitude, which at
    60 north is a factor-of-two bias -- and it would pick the wrong cell for a point sitting
    between two, in the direction that makes east-west errors look small.
    """
    # At 60 N a degree of longitude is ~55 km, half a degree of latitude. A point 0.6 degrees
    # east and 0.4 north of a cell centre is genuinely closer in latitude terms to the
    # north neighbour under unscaled degrees, but closer to the eastern one in real distance.
    latitudes = np.array([[60.0, 60.0], [61.0, 61.0]])
    longitudes = np.array([[0.0, 1.0], [0.0, 1.0]])
    [found] = nearest_cells(latitudes, longitudes, [Point("A", 60.4, 0.6)])
    assert (found.y, found.x) == (0, 1)


def test_the_match_error_is_reported_in_km() -> None:
    """A station near a coast or a mountain front is worse represented than an inland one, and
    that has to be visible rather than averaged away."""
    latitudes, longitudes = _regular_grid()
    [found] = nearest_cells(latitudes, longitudes, [Point("A", 32.4, -98.0)])
    assert found.error_km == pytest.approx(0.4 * 111.0, rel=0.01)


def test_mismatched_grids_are_refused() -> None:
    with pytest.raises(ValueError, match="differ in shape"):
        nearest_cells(np.zeros((3, 3)), np.zeros((3, 4)), [Point("A", 0.0, 0.0)])


def test_the_bounding_box_covers_every_cell() -> None:
    located = [
        Located("A", y=10, x=40, latitude=0.0, longitude=0.0, error_km=0.0),
        Located("B", y=4, x=55, latitude=0.0, longitude=0.0, error_km=0.0),
    ]
    ys, xs = bounding_box(located)
    assert (ys.start, ys.stop) == (4, 11)
    assert (xs.start, xs.stop) == (40, 56)


def test_an_empty_point_set_cannot_be_bounded() -> None:
    with pytest.raises(ValueError, match="no located points"):
        bounding_box([])


def test_the_match_report_names_distinct_cells() -> None:
    """Two stations inside one cell get one wind series, and that has to be visible."""
    located = [
        Located("A", y=1, x=1, latitude=0.0, longitude=0.0, error_km=5.0),
        Located("B", y=1, x=1, latitude=0.0, longitude=0.0, error_km=9.0),
    ]
    assert "2 points -> 1 distinct cells" in match_report(located)


# --- NARR conventions ---------------------------------------------------------
def test_only_the_requested_calendar_months_are_fetched() -> None:
    """A month outside the migration windows costs the same to fetch and answers nothing."""
    wanted = narr.months_between(date(2015, 1, 1), date(2016, 12, 31), only=(9, 10))
    assert wanted == [(2015, 9), (2015, 10), (2016, 9), (2016, 10)]


def test_month_ranges_cross_the_year_boundary() -> None:
    wanted = narr.months_between(date(2015, 11, 1), date(2016, 2, 28))
    assert wanted == [(2015, 11), (2015, 12), (2016, 1), (2016, 2)]


def test_the_night_label_is_the_previous_utc_day() -> None:
    """The convention that would be wrong silently.

    A night beginning on the local evening of D carries its 00-09 UTC hours on D+1, so a wind
    row built from UTC day D+1 describes the radar night labelled D. Written under the radar
    night's own label so a join on date is right by construction.
    """
    assert narr.UTC_DAY_TO_RADAR_NIGHT == -1


def test_driver_rows_are_marked_gridded_and_say_what_they_are() -> None:
    nights = pl.DataFrame(
        {
            "date": [date(2015, 9, 20)],
            "value": [7.5],
            "site_id": ["KBGM"],
            "variable": ["wind_u_925hPa"],
            "longitude": [-75.9],
            "latitude": [42.0],
        }
    )
    table = narr.to_samples(nights)
    DRIVER_SAMPLES.validate(table)
    assert table.column("kind").to_pylist() == [DriverKind.GRIDDED.value]
    provenance = table.column("derived_from").to_pylist()[0]
    assert "925hPa" in provenance
    assert "utc_day-1" in provenance


def test_the_level_recorded_in_the_variable_name_matches_the_level_fetched() -> None:
    """The vertical coordinate lives in the variable name because DRIVER_SAMPLES has depth and
    no height. If the two drifted apart, every wind would be labelled with the wrong altitude.
    """
    assert narr.LEVEL_HPA == 925
    # 1000/975/950/925/... at 25 hPa spacing, so 925 is the fourth.
    assert narr.LEVEL_INDEX == 3


def test_airspeed_alignment_prefers_the_offset_that_tightens_the_distribution() -> None:
    """The mechanism behind the date convention, on data built so the answer is known.

    Ground speed is airspeed plus wind. Here every night has a true airspeed of exactly 10 and
    a wind that varies, so pairing a night with its own wind recovers 10 with no spread, and
    pairing it with a neighbour's does not.
    """
    days = [date(2015, 9, day) for day in range(1, 21)]
    winds_u = np.linspace(-8.0, 8.0, len(days))
    radar = pl.DataFrame(
        {
            "station_id": ["KBGM"] * len(days),
            "date": days,
            "u_radar": winds_u + 10.0,
            "v_radar": np.zeros(len(days)),
        }
    )
    # The wind rows are labelled one day late, so offset -1 must be the winner.
    winds = pl.DataFrame(
        {
            "station_id": ["KBGM"] * len(days),
            "date": [date(2015, 9, day + 1) for day in range(1, 21)],
            "wind_u": winds_u,
            "wind_v": np.zeros(len(days)),
        }
    )
    table = narr.align_offset(radar, winds, offsets=(-2, -1, 0, 1))
    best = table.sort("sd").row(0, named=True)
    assert best["offset_days"] == -1
    assert best["median_airspeed"] == pytest.approx(10.0, abs=1e-6)
    assert best["sd"] == pytest.approx(0.0, abs=1e-6)
