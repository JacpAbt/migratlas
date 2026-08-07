"""Sample a gridded driver onto a point set.

The generic half of the driver panel: locating points on a grid, and the contract a gridded
source has to satisfy. Everything specific to one product -- URLs, levels, time conventions --
belongs in a module under `drivers/`, so adding CMEMS or CMIP6 later means writing a source
rather than touching this.

Nearest cell rather than interpolation, deliberately. Bilinear interpolation across a coarse
reanalysis grid invents structure it does not have, and the honest error to report is the
distance to the cell centre, which interpolation hides.
"""

from typing import TYPE_CHECKING, Final, NamedTuple, Protocol

import numpy as np

if TYPE_CHECKING:
    from datetime import date

    import polars as pl


class Point(NamedTuple):
    """Somewhere an animal was observed, and which needs a driver value."""

    site_id: str
    latitude: float
    longitude: float


class Located(NamedTuple):
    """A point matched to a grid cell, with the cost of the match recorded.

    ``error_km`` exists so a station near a coast or a mountain front can be identified as
    poorly represented rather than silently treated like an inland one.
    """

    site_id: str
    y: int
    x: int
    latitude: float
    longitude: float
    error_km: float


class GriddedSource(Protocol):
    """A product that can return driver values at points over a date range."""

    source_id: str

    def sample(
        self, points: list[Point], start: date, end: date
    ) -> pl.DataFrame:  # pragma: no cover -- structural
        """One row per site, period and variable, ready for `DRIVER_SAMPLES`."""
        ...


# The coarsest grid this project samples is CMIP6 at a quarter of a degree or worse, so a legitimate
# match is tens of kilometres and never hundreds. Above this the point is not in the grid at all --
# and "not in the grid" has to be an error rather than a nearest cell, because a nearest cell is
# always available and always looks like an answer.
#
# Written after sampling 496 southern African cells against a North American grid. Every point
# matched, to the bottom edge of the box, roughly four thousand kilometres away. `error_km` recorded
# that faithfully and nothing read it, so the wrong continent landed in the lake under the right
# site ids and overwrote a variable that a published finding depends on.
MAX_MATCH_KM: Final = 250.0


def nearest_cells(
    latitudes: np.ndarray,
    longitudes: np.ndarray,
    points: list[Point],
    *,
    max_error_km: float = MAX_MATCH_KM,
) -> list[Located]:
    """Match each point to the closest cell of a curvilinear grid.

    Takes the 2-D latitude and longitude arrays rather than 1-D axes, because the grids that
    matter here are not regular: NARR is Lambert Conformal, so there is no latitude axis to
    search. Brute force over the whole grid, which is 97k cells for NARR and costs nothing
    once per run.

    Longitude difference is scaled by cos(latitude) so the search is in approximate distance
    rather than in degrees, which would bias matches eastward or westward at high latitude.
    """
    if latitudes.shape != longitudes.shape:
        msg = (
            f"latitude and longitude grids differ in shape: {latitudes.shape} vs {longitudes.shape}"
        )
        raise ValueError(msg)

    located: list[Located] = []
    for point in points:
        scale = np.cos(np.radians(point.latitude))
        dlat = latitudes - point.latitude
        dlon = (longitudes - point.longitude) * scale
        distance = dlat**2 + dlon**2
        flat = int(np.argmin(distance))
        yi, xi = (int(index) for index in np.unravel_index(flat, distance.shape))
        located.append(
            Located(
                site_id=point.site_id,
                y=yi,
                x=xi,
                latitude=float(latitudes[yi, xi]),
                longitude=float(longitudes[yi, xi]),
                error_km=float(np.hypot(dlat[yi, xi], dlon[yi, xi]) * 111.0),
            )
        )

    worst = max(located, key=lambda one: one.error_km, default=None)
    if worst is not None and worst.error_km > max_error_km:
        far = sum(1 for one in located if one.error_km > max_error_km)
        msg = (
            f"{far} of {len(located)} points are more than {max_error_km:g} km from any cell of "
            f"this grid -- the worst, {worst.site_id!r}, by {worst.error_km:,.0f} km. The points "
            f"and the grid are not describing the same place. A nearest cell exists for every "
            f"point on earth, so this cannot be caught downstream."
        )
        raise ValueError(msg)
    return located


def bounding_box(located: list[Located]) -> tuple[slice, slice]:
    """The smallest index box containing every matched cell.

    One request for the box beats one request per point when the cost is dominated by
    per-request latency, which is the case over OPeNDAP -- a single point column took 47 s
    while the whole station box for the same period took under 3 s. The box wastes bytes on
    cells nobody asked for and is still far cheaper.
    """
    if not located:
        msg = "no located points to bound"
        raise ValueError(msg)
    ys = [item.y for item in located]
    xs = [item.x for item in located]
    return (slice(min(ys), max(ys) + 1), slice(min(xs), max(xs) + 1))


def match_report(located: list[Located]) -> str:
    """How well the point set is represented by the grid, for the run log and the method note."""
    errors = np.array([item.error_km for item in located], dtype=float)
    cells = len({(item.y, item.x) for item in located})
    return (
        f"{len(located)} points -> {cells} distinct cells; "
        f"error median {np.median(errors):.1f} km, max {errors.max():.1f} km"
    )
