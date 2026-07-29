"""Distribution centroids from any repeated survey: where the animals were, weighted by how many.

Two metrics, both abundance-weighted means over the sites sampled in a year: latitude, and depth.
Depth is not an afterthought -- marine species respond to warming by going deeper about as often as
they go poleward, and reporting latitude alone would let a real response look like none.

Nothing here is taxon-aware or gear-aware. The input is a table of (site, position, period, count,
effort), which a trawl survey, a bird ringing scheme or a camera-trap array can all produce.

The footprint rule lives here rather than in the report because it is not presentation: a survey
that added northern stations in 2005 shows a poleward centroid shift with no animal having moved,
and restricting to consistently sampled cells is the only thing that separates the two. See
docs/methods/phase1b-marine.md, where the thresholds are pre-registered.
"""

import logging
from dataclasses import dataclass
from typing import Final

import numpy as np
import polars as pl

log = logging.getLogger(__name__)

# One degree, matching every gridded surface in the lake.
CELL_DEG: Final = 1.0

# Pre-registered in the method note. A cell counts toward the footprint if it was sampled in at
# least this share of the survey's years.
CONSISTENCY: Final = 0.8

# Below this a "consistent footprint" is a handful of cells and a centroid computed in it is noise.
MIN_CELLS: Final = 10

# Coefficient count when a break term was fitted: intercept, slope, step.
WITH_BREAK: Final = 2


@dataclass(frozen=True, slots=True)
class Footprint:
    """Which cells a survey sampled consistently, and what restricting to them cost."""

    cells: int
    cells_dropped: int
    rows_kept: int
    rows_dropped: int
    years: tuple[int, int]

    @property
    def rows_share(self) -> float:
        total = self.rows_kept + self.rows_dropped
        return self.rows_kept / total if total else 0.0

    def __str__(self) -> str:
        return (
            f"{self.cells} consistent cells (dropped {self.cells_dropped}), "
            f"{self.rows_share:.0%} of rows kept, {self.years[0]}-{self.years[1]}"
        )


def to_cells(observations: pl.DataFrame, *, cell_deg: float = CELL_DEG) -> pl.DataFrame:
    """Add a cell index and a year to survey rows, and compute catch per unit effort.

    CPUE rather than raw catch: a haul that swept twice the area is not evidence of twice as many
    animals, and every weighted mean below uses this as the weight.
    """
    half = cell_deg / 2
    return observations.with_columns(
        year=pl.col("period_start").dt.year(),
        cell_longitude=(pl.col("site_longitude") / cell_deg).floor() * cell_deg + half,
        cell_latitude=(pl.col("site_latitude") / cell_deg).floor() * cell_deg + half,
        cpue=pl.col("count") / pl.col("effort"),
    )


def consistent_footprint(
    cells: pl.DataFrame, *, consistency: float = CONSISTENCY
) -> tuple[pl.DataFrame, Footprint]:
    """Keep only cells sampled in at least ``consistency`` of the survey's years.

    Sampled means "a haul happened there", which is why this is computed from the distinct
    cell-years present rather than from catch: a cell where the target species was absent was still
    surveyed, and dropping it would turn absence into non-observation.
    """
    years = cells["year"].unique().to_numpy()
    required = max(1, round(consistency * years.size))

    sampled = (
        cells.select("cell_longitude", "cell_latitude", "year")
        .unique()
        .group_by("cell_longitude", "cell_latitude")
        .agg(pl.len().alias("years_sampled"))
    )
    keep = sampled.filter(pl.col("years_sampled") >= required).select(
        "cell_longitude", "cell_latitude"
    )

    restricted = cells.join(keep, on=["cell_longitude", "cell_latitude"], how="inner")
    footprint = Footprint(
        cells=keep.height,
        cells_dropped=sampled.height - keep.height,
        rows_kept=restricted.height,
        rows_dropped=cells.height - restricted.height,
        years=(int(years.min()), int(years.max())),
    )
    return restricted, footprint


def centroids(
    cells: pl.DataFrame, *, group_by: tuple[str, ...] = ("taxon_key", "taxon_label")
) -> pl.DataFrame:
    """Abundance-weighted mean latitude and depth per group per year.

    Weighted by CPUE. A year in which a species was caught nowhere yields no row rather than a
    centroid of zero, because "not found" has no position.
    """
    keys = [*group_by, "year"]
    weighted = cells.filter(pl.col("cpue") > 0)
    if weighted.is_empty():
        return pl.DataFrame()

    aggregations = [
        (pl.col("site_latitude") * pl.col("cpue")).sum().alias("_lat"),
        pl.col("cpue").sum().alias("_weight"),
        pl.len().alias("hauls"),
    ]
    if "site_depth_m" in cells.columns:
        aggregations.append((pl.col("site_depth_m") * pl.col("cpue")).sum().alias("_depth"))

    out = weighted.group_by(keys).agg(aggregations)
    out = out.with_columns(mean_latitude=pl.col("_lat") / pl.col("_weight"))
    if "_depth" in out.columns:
        out = out.with_columns(mean_depth=pl.col("_depth") / pl.col("_weight"))
    return out.drop([c for c in ("_lat", "_depth", "_weight") if c in out.columns]).sort(
        [*group_by, "year"]
    )


def shift_per_decade(
    series: pl.DataFrame,
    *,
    column: str = "mean_latitude",
    group_by: tuple[str, ...] = ("taxon_key", "taxon_label"),
    min_years: int = 15,
    break_year: int | None = None,
) -> pl.DataFrame:
    """Least-squares trend in a centroid, per group, in units per decade.

    ``break_year`` adds a level shift, for a survey that changed gear. The same treatment the
    NEXRAD dual-polarisation upgrade gets in Phase 1a, and for the same reason: an instrument
    change that moves every measurement is not a trend.
    """
    rows: list[dict[str, object]] = []
    for key_values, group in series.group_by(list(group_by), maintain_order=True):
        usable = group.filter(pl.col(column).is_not_null())
        if usable.height < min_years:
            continue

        year = usable["year"].to_numpy().astype(float)
        value = usable[column].to_numpy().astype(float)
        design = [np.ones_like(year), year - year.mean()]
        if break_year is not None:
            step = (year >= break_year).astype(float)
            # A break outside this group's own span is not identifiable. Skip the term, not
            # the group -- a species with no data across the gear change still has a trend.
            if 0 < step.sum() < step.size:
                design.append(step)

        matrix = np.column_stack(design)
        if np.linalg.matrix_rank(matrix) < matrix.shape[1]:
            continue
        coefficients, *_ = np.linalg.lstsq(matrix, value, rcond=None)
        rows.append(
            {
                **dict(zip(group_by, key_values, strict=True)),
                "years": usable.height,
                "per_decade": float(coefficients[1]) * 10,
                "break_shift": (float(coefficients[2]) if len(coefficients) > WITH_BREAK else None),
            }
        )
    return pl.DataFrame(rows)
