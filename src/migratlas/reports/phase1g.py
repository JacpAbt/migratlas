"""Phase 1g — the per-cell atlas change against surface-water change.

Pre-registered in `docs/methods/phase1g-water.md`, including the thing that makes or breaks it: an
ordinary p-value here is meaningless and looks fine. Both maps are spatially autocorrelated, and two
autocorrelated surfaces agree far more often than independent sampling implies. Significance is
judged against nulls that keep the factor's spatial structure and destroy only its alignment with
the response; the naive test is computed too and published beside them, labelled as the wrong one.

The instrument is weak by construction and the note says so: the product compares 1984-1999 with
2000-2021 against atlas windows of five years each, which attenuates. A surviving effect means
something. A null means "not detectable with the only instrument available" and must say so.
"""

import logging
from dataclasses import dataclass
from typing import Final

import numpy as np
import polars as pl
from scipy import stats

from migratlas.lake.reader import scan_dataset
from migratlas.reports import phase1e, phase1f

log = logging.getLogger(__name__)

SOURCE_ID: Final = "jrc_gsw"
CHANGE_VARIABLE: Final = "surface_water_change_km2"
EXTENT_VARIABLE: Final = "surface_water_extent_km2"

DRAWS: Final = 999
SEED: Final = 1_984_2021

# Note §3 prediction 4 asked for cells with "essentially no water at baseline" and did not define
# it. Six cells hold literally none, which is too few to test anything, so the placebo subset is
# the driest quartile by long-run extent. Fixed from the factor's own marginal distribution before
# any relationship with the response was computed, which keeps it a placebo rather than a choice.
PLACEBO_QUANTILE: Final = 0.25

ALPHA: Final = 0.05

# A draw whose shift lands almost everything on a hole cannot be fitted at all, and one fitted
# on two points is not a draw. Skipped and counted rather than allowed to return a slope.
MIN_DRAW_CELLS: Final = 3


@dataclass(frozen=True, slots=True)
class Fit:
    """One regression of the per-cell change on water, conditioned on effort."""

    cells: int
    water: float
    """Coefficient on water change, in analysed taxa per km2."""

    effort: float
    partial_r: float
    """Correlation of the response with water once effort is removed from both."""

    naive_p: float
    """The wrong test, kept and labelled."""

    @property
    def direction(self) -> str:
        return "positive" if self.water > 0 else "negative" if self.water < 0 else "flat"


def _design() -> pl.DataFrame:
    """Every footprint cell with its change, its water, and its effort, joined on the cell."""
    surface = phase1f.surface()
    response = pl.DataFrame(
        {
            "cell_lat": [cell.cell_lat for cell in surface.cells],
            "cell_lon": [cell.cell_lon for cell in surface.cells],
            "delta": [cell.delta_detected for cell in surface.cells],
            "delta_corrected": [cell.delta for cell in surface.cells],
            "effort": [cell.cards_second - cell.cards_first for cell in surface.cells],
        }
    )

    water = (
        scan_dataset("driver_samples", source_id=SOURCE_ID)
        .filter(pl.col("variable").is_in([CHANGE_VARIABLE, EXTENT_VARIABLE]))
        .select(
            cell_lat=pl.col("latitude"),
            cell_lon=pl.col("longitude"),
            variable=pl.col("variable"),
            value=pl.col("value"),
        )
        .collect()
        .pivot(on="variable", index=["cell_lat", "cell_lon"], values="value")
        .rename({CHANGE_VARIABLE: "water", EXTENT_VARIABLE: "extent"})
    )

    joined = response.join(water, on=["cell_lat", "cell_lon"], how="inner")
    if joined.height != response.height:
        msg = (
            f"water covers {joined.height} of {response.height} footprint cells; the join is on "
            f"the cell centre and a mismatch means the two grids have drifted apart."
        )
        raise ValueError(msg)
    return joined


def _partial(response: np.ndarray, water: np.ndarray, effort: np.ndarray) -> tuple[float, float]:
    """Slope on water and the partial correlation, both conditioning on effort.

    Conditioning rather than ignoring: Phase 1f already showed the response tracks effort at
    rho -0.199, and a water coefficient that was really an effort coefficient would be the second
    stop condition firing.
    """
    design = np.column_stack([np.ones_like(water), water, effort])
    slope = np.linalg.lstsq(design, response, rcond=None)[0]

    # Residualise both sides on effort, which is what a partial correlation is.
    control = np.column_stack([np.ones_like(effort), effort])
    left = response - control @ np.linalg.lstsq(control, response, rcond=None)[0]
    right = water - control @ np.linalg.lstsq(control, water, rcond=None)[0]
    if np.std(left) == 0 or np.std(right) == 0:
        return float(slope[1]), 0.0
    return float(slope[1]), float(np.corrcoef(left, right)[0, 1])


def fit(frame: pl.DataFrame, response_column: str = "delta") -> Fit:
    """Regress the per-cell change on water change, conditioned on the change in cards."""
    response = frame[response_column].to_numpy()
    water = frame["water"].to_numpy()
    effort = frame["effort"].to_numpy()
    slope, partial = _partial(response, water, effort)
    naive = stats.pearsonr(water, response)
    return Fit(
        cells=frame.height,
        water=slope,
        effort=float(
            np.linalg.lstsq(
                np.column_stack([np.ones_like(water), water, effort]), response, rcond=None
            )[0][2]
        ),
        partial_r=partial,
        naive_p=float(naive.pvalue),
    )


def _grid_index(frame: pl.DataFrame, size: float) -> tuple[np.ndarray, np.ndarray]:
    """Row and column indices of each cell within the footprint's bounding grid."""
    lat = frame["cell_lat"].to_numpy()
    lon = frame["cell_lon"].to_numpy()
    return (
        np.round((lat - lat.min()) / size).astype(int),
        np.round((lon - lon.min()) / size).astype(int),
    )


def toroidal_null(frame: pl.DataFrame, response_column: str = "delta") -> tuple[float, int]:
    """Shift the whole water surface over the footprint and refit, keeping its structure intact.

    The factor is moved as one rigid sheet with wraparound, so every spatial property of the water
    map -- its patchiness, its range, its autocorrelation -- survives exactly, and only its
    registration against the response is destroyed. A shifted position landing on a hole in the
    footprint has no water value, so that cell drops from that draw; the mean usable count is
    returned so a reader can see how much of the footprint each draw actually used.
    """
    rows, columns = _grid_index(frame, phase1e.CELL_DEG)
    height, width = rows.max() + 1, columns.max() + 1
    sheet = np.full((height, width), np.nan)
    sheet[rows, columns] = frame["water"].to_numpy()

    response = frame[response_column].to_numpy()
    effort = frame["effort"].to_numpy()
    observed, _ = _partial(response, frame["water"].to_numpy(), effort)

    rng = np.random.default_rng(SEED)
    extreme = 0
    used: list[int] = []
    for _ in range(DRAWS):
        shifted = np.roll(
            sheet, (int(rng.integers(1, height)), int(rng.integers(1, width))), axis=(0, 1)
        )
        drawn = shifted[rows, columns]
        keep = ~np.isnan(drawn)
        used.append(int(keep.sum()))
        if keep.sum() < MIN_DRAW_CELLS:
            continue
        slope, _ = _partial(response[keep], drawn[keep], effort[keep])
        if abs(slope) >= abs(observed):
            extreme += 1
    return (extreme + 1) / (DRAWS + 1), int(np.mean(used))


def spectral_null(frame: pl.DataFrame, response_column: str = "delta") -> float:
    """Moran spectral randomisation: surrogates with the factor's autocorrelation, not its map.

    A second null with a different failure mode, as registered. The toroidal shift preserves the
    surface exactly but can only produce as many distinct draws as the grid has offsets; this
    preserves the spectrum -- and so Moran's I -- while drawing from a much larger space.
    """
    weights = phase1f.weights(
        [
            phase1f.CellChange(
                cell_lat=lat,
                cell_lon=lon,
                first=0.0,
                second=0.0,
                detected_first=0.0,
                detected_second=0.0,
                movers=0,
                cards_first=0.0,
                cards_second=0.0,
            )
            for lat, lon in frame.select("cell_lat", "cell_lon").iter_rows()
        ]
    )
    symmetric = (weights + weights.T) / 2
    centre = np.eye(frame.height) - np.ones((frame.height, frame.height)) / frame.height
    vectors = np.linalg.eigh(centre @ symmetric @ centre)[1]

    water = frame["water"].to_numpy()
    response = frame[response_column].to_numpy()
    effort = frame["effort"].to_numpy()
    observed, _ = _partial(response, water, effort)

    mean = water.mean()
    coefficients = vectors.T @ (water - mean)
    rng = np.random.default_rng(SEED)
    extreme = 0
    for _ in range(DRAWS):
        # Sign-flipping each spectral coefficient preserves every coefficient's magnitude, so the
        # surrogate has the same Moran's I as the factor and a different map.
        surrogate = mean + vectors @ (coefficients * rng.choice([-1.0, 1.0], size=frame.height))
        slope, _ = _partial(response, surrogate, effort)
        if abs(slope) >= abs(observed):
            extreme += 1
    return (extreme + 1) / (DRAWS + 1)
