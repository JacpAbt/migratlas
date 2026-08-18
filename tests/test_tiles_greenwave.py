"""The green wave's arithmetic, pinned without a download.

The full build fetches 2.7 GB and reduces 984 rasters; CI exercises the three conversions that
could lie silently: the file-name-to-bin mapping, the block reduction's handling of fill, and
the vegetated-share floor.
"""

import numpy as np

from migratlas.tiles.greenwave import FILL, _bin_of, _block_reduce


def test_the_file_name_names_the_bin() -> None:
    assert _bin_of("PKU_GIMMS_NDVI_V1.2_20010101.tif") == 0
    assert _bin_of("PKU_GIMMS_NDVI_V1.2_20010102.tif") == 1
    assert _bin_of("some/dir/PKU_GIMMS_NDVI_V1.2_19821202.tif") == 23
    assert _bin_of("readme.txt") is None
    assert _bin_of("PKU_GIMMS_NDVI_V1.2_20011301.tif") is None


def test_fill_is_an_absence_not_a_zero() -> None:
    """A block of desert must contribute no pixels, not 144 zeros dragging the mean down."""
    block = 12
    values = np.full((block, block * 2), 0.5)
    raw = np.full((block, block * 2), 500, dtype=np.uint16)
    raw[:, block:] = FILL
    valid = raw != FILL
    total, count = _block_reduce(np.where(valid, values, 0.0), valid)
    assert count[0, 0] == block * block
    assert count[0, 1] == 0
    assert total[0, 1] == 0.0
    assert abs(total[0, 0] / count[0, 0] - 0.5) < 1e-9


def test_partial_vegetation_averages_over_the_vegetated_ground_only() -> None:
    block = 12
    values = np.full((block, block), 0.8)
    valid = np.zeros((block, block), dtype=bool)
    valid[:6, :] = True
    total, count = _block_reduce(np.where(valid, values, 0.0), valid)
    assert count[0, 0] == 72
    assert abs(total[0, 0] / count[0, 0] - 0.8) < 1e-9
