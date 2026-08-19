"""The CMEMS conversions, which are the parts that fail by returning a plausible number.

Nothing here touches the network. What is tested is the depth lookup -- whose axis the client signs
opposite to the store -- and the footprint mean, whose job is to average the water and report
nothing where there is none.
"""

import numpy as np

from migratlas.drivers import cmems

# The client's convention: positive metres, thinning with depth. Trimmed from the real axis.
DEPTHS = np.array([0.506, 1.541, 2.646, 5.078, 9.573, 15.810, 25.211, 40.344, 55.764, 92.326])


def test_the_depth_lookup_uses_the_clients_positive_convention() -> None:
    """The raw store signs this axis negative and the client signs it positive.

    A picker written for one reads the surface for every survey when handed the other, and surface
    oxygen is entirely plausible-looking -- so this is pinned rather than trusted.
    """
    assert cmems.nearest_depth(DEPTHS, 38.0) == 7  # 40.344 m
    assert cmems.nearest_depth(DEPTHS, 8.0) == 4  # 9.573 m
    assert cmems.nearest_depth(DEPTHS, 258.0) == len(DEPTHS) - 1  # the deepest offered


def test_the_shallowest_survey_does_not_land_on_the_surface() -> None:
    """SEUS fishes at 8 m. If the sign were wrong this would return index 0 and look fine."""
    assert cmems.nearest_depth(DEPTHS, 8.0) != 0


def test_either_depth_sign_finds_the_same_water() -> None:
    """Some sources sign depth downward; the target must not decide the answer."""
    assert cmems.nearest_depth(DEPTHS, -40.0) == cmems.nearest_depth(DEPTHS, 40.0)


def test_a_coordinate_maps_to_the_cell_that_contains_it() -> None:
    """`to_cells` builds a cell as floor(coord) + 0.5, and this has to invert exactly that.

    If the two disagreed, the footprint's cells would never match the grid's and every survey would
    come back with no water.
    """
    assert list(cmems.cell_of(np.array([55.0, 55.3, 55.99, -0.2, -1.0]))) == [
        55.5,
        55.5,
        55.5,
        -0.5,
        -0.5,
    ]


def _grid() -> tuple[np.ndarray, np.ndarray]:
    """Quarter-degree points spanning two 1° cells in each direction."""
    return np.arange(55.0, 57.0, 0.25), np.arange(3.0, 5.0, 0.25)


def test_the_mean_covers_only_the_cells_in_the_footprint() -> None:
    """A box read for one survey holds cells that survey never fished; they must not be averaged."""
    latitudes, longitudes = _grid()
    oxygen = np.zeros((2, latitudes.size, longitudes.size))
    # Mark one cell's points 300 and everything else 100.
    lat_in = (latitudes >= 55.0) & (latitudes < 56.0)
    lon_in = (longitudes >= 3.0) & (longitudes < 4.0)
    oxygen[:, :, :] = 100.0
    oxygen[:, np.ix_(lat_in)[0][:, None], np.ix_(lon_in)[0][None, :]] = 300.0

    series, used = cmems.mean_over_footprint(oxygen, latitudes, longitudes, {(55.5, 3.5)})
    assert used == 1
    assert np.allclose(series, 300.0), "cells outside the footprint leaked into the mean"


def test_a_footprint_cell_absent_from_the_box_is_not_counted() -> None:
    """`used` is the count of cells actually found, so a coverage report cannot overstate itself."""
    latitudes, longitudes = _grid()
    oxygen = np.full((2, latitudes.size, longitudes.size), 250.0)
    series, used = cmems.mean_over_footprint(
        oxygen, latitudes, longitudes, {(55.5, 3.5), (80.5, 120.5)}
    )
    assert used == 1
    assert np.allclose(series, 250.0)


def test_a_footprint_with_no_water_reports_nothing_rather_than_a_nan() -> None:
    """A landlocked or below-floor footprint contributes no series at all.

    A NaN series here would reach the trend and the unit would look like it had a driver.
    """
    latitudes, longitudes = _grid()
    oxygen = np.full((3, latitudes.size, longitudes.size), np.nan)
    series, used = cmems.mean_over_footprint(oxygen, latitudes, longitudes, {(80.5, 120.5)})
    assert used == 0
    assert series.size == 0


def test_a_partly_land_cell_averages_its_water_only() -> None:
    """Half a cell on land gives the mean of the wet half -- not a NaN, and not a zero."""
    latitudes, longitudes = _grid()
    oxygen = np.full((3, latitudes.size, longitudes.size), np.nan)
    oxygen[:, :2, :] = 250.0
    series, used = cmems.mean_over_footprint(oxygen, latitudes, longitudes, {(55.5, 3.5)})
    assert used == 1
    assert np.allclose(series, 250.0)


def test_a_month_with_no_water_anywhere_is_nan_and_not_zero() -> None:
    """The product has gaps. A gap must not read as an oxygen measurement of zero."""
    latitudes, longitudes = _grid()
    oxygen = np.full((3, latitudes.size, longitudes.size), 250.0)
    oxygen[1] = np.nan
    series, used = cmems.mean_over_footprint(oxygen, latitudes, longitudes, {(55.5, 3.5)})
    assert used == 1
    assert np.isnan(series[1])
    assert np.allclose(series[[0, 2]], 250.0)
