"""The track timing metric, and the two things about it that were wrong on the first run.

No lake. The crossing rule is pure arithmetic on arrays, and that is the part worth pinning: it is
the one place a date is decided, and every failure mode is a shape of track rather than a shape of
data volume.
"""

import numpy as np
import polars as pl

from migratlas.reports import phase1d


def _days(*pairs: tuple[int, float]) -> tuple[np.ndarray, np.ndarray]:
    doy = np.array([day for day, _ in pairs], dtype=float)
    lat = np.array([value for _, value in pairs], dtype=float)
    return doy, lat


# --- The crossing rule -------------------------------------------------------
def test_a_northward_animal_crosses_at_the_middle_of_its_own_range() -> None:
    doy, lat = _days((1, 50.0), (100, 51.0), (200, 52.0))
    assert phase1d._crossing(doy, lat, 51.0) == 100.0


def test_an_animal_already_north_at_the_start_gets_no_date() -> None:
    """Not day one.

    Taking the first day above the midpoint would hand a southbound animal a date of day one, which
    is a fact about the calendar rather than about the animal. The rule requires south *then* north.
    """
    doy, lat = _days((1, 52.0), (100, 51.5), (200, 50.0))
    assert phase1d._crossing(doy, lat, 51.0) is None


def test_the_date_is_the_first_crossing_not_the_last() -> None:
    """An animal that oscillates has one arrival, and it is the first."""
    doy, lat = _days((1, 50.0), (60, 52.0), (120, 50.0), (180, 52.0))
    assert phase1d._crossing(doy, lat, 51.0) == 60.0


def test_fixes_out_of_time_order_do_not_change_the_answer() -> None:
    """The lake promises no ordering, and a sort inside the metric is cheaper than trusting one."""
    ordered, _ = _days((1, 50.0), (100, 52.0))
    shuffled = np.array([100.0, 1.0]), np.array([52.0, 50.0])
    assert phase1d._crossing(*shuffled, 51.0) == phase1d._crossing(
        ordered, np.array([50.0, 52.0]), 51.0
    )


def test_an_animal_that_never_reaches_the_midpoint_gets_no_date() -> None:
    doy, lat = _days((1, 50.0), (100, 50.2), (200, 50.4))
    assert phase1d._crossing(doy, lat, 51.0) is None


# --- Thresholds --------------------------------------------------------------
def test_the_thresholds_are_the_ones_the_note_registered() -> None:
    """Asserted so a later loosening has to change a test that names the reason.

    `MIN_INDIVIDUALS` decided the result: Bylot's foxes have 17 years of coverage and 13 once a
    cell-year needs three animals, which is what put them under the floor.
    """
    assert phase1d.MIN_FIXES == 30
    assert phase1d.MIN_MONTHS == 6
    assert phase1d.MIN_INDIVIDUALS == 3
    assert phase1d.CELL == 1.0


# --- The sensor break --------------------------------------------------------
def test_one_sensor_reports_no_break() -> None:
    dated = pl.DataFrame({"sensor": ["GPS"] * 3, "crossing_doy": [100.0, 110.0, 120.0]})
    assert phase1d._sensor_break(dated) is None


def test_two_sensors_report_the_shift_between_them() -> None:
    """Measured and reported, never silently corrected.

    On the real caribou cell this is -46.8 days between GPS and radio transmitters, against a trend
    of order one day per decade. The instrument is the story, and a series that adjusted it away
    quietly would hide the only thing worth knowing about that cell.
    """
    dated = pl.DataFrame(
        {
            "sensor": ["Argos Doppler Shift", "Argos Doppler Shift", "GPS", "GPS"],
            "crossing_doy": [100.0, 100.0, 150.0, 150.0],
        }
    )
    assert phase1d._sensor_break(dated) == 50.0


# --- Detectability -----------------------------------------------------------
def test_a_cell_is_detectable_only_at_the_fifteen_year_floor() -> None:
    """The same floor `phase1` applies per station, applied here per cell."""
    short = phase1d.Cell(
        lat=51, lon=64, years=14, individual_years=99, sensors=1, first=2003, last=2016
    )
    long = phase1d.Cell(
        lat=51, lon=64, years=15, individual_years=99, sensors=1, first=2002, last=2016
    )
    assert not short.detectable
    assert long.detectable
