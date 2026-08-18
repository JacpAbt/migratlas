"""The green-up metric and its reduction plumbing, pinned before the archives are run."""

import numpy as np

from migratlas.drivers.greenup import (
    BINS_PER_YEAR,
    MIN_AMPLITUDE,
    _to_frame,
    greenup_day,
)
from migratlas.drivers.schema import DRIVER_SAMPLES
from migratlas.tiles.greenwave import _year_of


def _year(*, low: float = 0.2, high: float = 0.8, rise_at: int = 8) -> np.ndarray:
    """A northern year: flat winter, a step to summer at ``rise_at``, flat summer, decline."""
    values = np.full(BINS_PER_YEAR, low)
    values[rise_at:18] = high
    values[18:] = low + (high - low) / 4
    return values


def test_the_crossing_lands_inside_the_rising_bin() -> None:
    day = greenup_day(_year(rise_at=8))
    assert day is not None
    # The midpoint is crossed between bins 7 and 8; the step means the crossing sits at the
    # boundary, whose bin-centre convention places it half a bin before bin 8's midpoint.
    assert (7 + 0.5) * (365.0 / BINS_PER_YEAR) < day <= (8 + 0.5) * (365.0 / BINS_PER_YEAR)


def test_a_later_spring_is_a_later_day() -> None:
    early = greenup_day(_year(rise_at=6))
    late = greenup_day(_year(rise_at=10))
    assert early is not None
    assert late is not None
    assert late > early


def test_a_flat_cell_has_no_greenup() -> None:
    flat = np.full(BINS_PER_YEAR, 0.5)
    flat[10] += MIN_AMPLITUDE / 2
    assert greenup_day(flat) is None


def test_a_gap_is_not_a_date() -> None:
    year = _year()
    year[3] = np.nan
    assert greenup_day(year) is None


def test_a_year_that_opens_green_is_skipped_not_guessed() -> None:
    """A southern-hemisphere calendar year starts above its own midpoint."""
    year = np.concatenate([_year()[12:], _year()[:12]])
    assert greenup_day(year) is None


def test_the_year_is_read_off_the_product_name() -> None:
    assert _year_of("some/dir/PKU_GIMMS_NDVI_V1.2_19900801.tif") == 1990
    assert _year_of("PKU_GIMMS_NDVI_V1.2_20221202.tif") == 2022
    assert _year_of("readme.tif") is None


def test_samples_conform_to_the_driver_schema() -> None:
    """The frame must cast to DRIVER_SAMPLES exactly; a drift here fails before the lake does."""
    frame = _to_frame(
        np.array([1990, 1991]),
        np.array([45.5, 45.5]),
        np.array([-110.5, -110.5]),
        np.array([120.0, 133.5]),
    )
    table = frame.select(DRIVER_SAMPLES.schema.names).to_arrow().cast(DRIVER_SAMPLES.schema)
    DRIVER_SAMPLES.validate(table)
    assert table.num_rows == 2


def test_interpolation_splits_a_gradual_rise() -> None:
    values = np.full(BINS_PER_YEAR, 0.2)
    values[8] = 0.5  # halfway up a 0.2 -> 0.8 rise: the exact midpoint
    values[9:18] = 0.8
    values[18:] = 0.3
    day = greenup_day(values)
    assert day is not None
    # The midpoint is reached exactly at bin 8, so the crossing is the whole of the 7 -> 8
    # step: interpolation places it at bin 8's centre.
    assert abs(day - (8 + 0.5) * (365.0 / BINS_PER_YEAR)) < 1.0
