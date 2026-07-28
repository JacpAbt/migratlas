"""Passage-date quantiles: when a season's movement happened, not how much of it.

Works on any evidence type that records a quantity through time, so the same code answers
"when did half the night-time aerial passage cross this radar" and "when did half the
season's counted individuals pass this survey site". Nothing here knows about taxa.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np
import polars as pl

if TYPE_CHECKING:
    from collections.abc import Sequence

    from migratlas.evidence import EvidenceSpec


DAYS_IN_LEAP_YEAR: Final = 366


@dataclass(frozen=True, slots=True)
class Season:
    """A day-of-year window. Inclusive at both ends.

    Fixed windows rather than data-driven ones: a window chosen from the same data whose
    trend you then estimate will absorb part of the trend.
    """

    name: str
    start_doy: int
    end_doy: int

    def __post_init__(self) -> None:
        if not 1 <= self.start_doy <= self.end_doy <= DAYS_IN_LEAP_YEAR:
            msg = f"Season {self.name!r} has an invalid window: {self.start_doy}-{self.end_doy}"
            raise ValueError(msg)


# Northern-hemisphere defaults, wide enough to contain the passage at any latitude in the
# US radar network without overlapping each other. Any real analysis should state its
# windows in the method note rather than inherit these silently.
NORTHERN_SPRING: Final = Season("spring", 60, 180)
NORTHERN_AUTUMN: Final = Season("autumn", 213, 334)


class MetricNotApplicableError(TypeError):
    """The evidence type does not record a quantity through time."""


def passage_quantiles(  # noqa: PLR0913 -- each argument is a distinct analysis choice that
    # belongs in a method note, so collapsing them into a config object would hide them
    observations: pl.DataFrame,
    spec: EvidenceSpec,
    *,
    seasons: Sequence[Season] = (NORTHERN_SPRING, NORTHERN_AUTUMN),
    quantiles: Sequence[float] = (0.1, 0.5, 0.9),
    group_by: Sequence[str] = ("station_id",),
    min_coverage: float | None = 0.9,
    min_observations: int = 20,
) -> pl.DataFrame:
    """Day of year by which each quantile of a season's passage had occurred.

    Args:
        observations: Rows conforming to ``spec``.
        spec: Supplies the time and value columns, so this function never names them.
        seasons: Day-of-year windows to summarise separately.
        quantiles: Fractions of cumulative passage to locate.
        group_by: Columns identifying a series, e.g. station, or station and quantity.
        min_coverage: Drop rows whose ``coverage_fraction`` falls below this. A night the
            instrument mostly missed is not a night with little movement, and treating it
            as one drags the quantiles toward whenever coverage happened to be good.
        min_observations: Below this many usable rows, a season-year yields nulls rather
            than a quantile computed from a handful of nights.

    Raises:
        MetricNotApplicableError: if the evidence type records no quantity.
    """
    if spec.time_column is None or spec.value_column is None:
        msg = (
            f"{spec.evidence_type} has no {'time' if not spec.time_column else 'value'} "
            f"column, so passage quantiles are undefined for it. Presence-only evidence "
            f"needs a different metric."
        )
        raise MetricNotApplicableError(msg)

    time, value = spec.time_column, spec.value_column
    frame = observations.lazy().filter(pl.col(value).is_not_null(), pl.col(time).is_not_null())

    if min_coverage is not None and "coverage_fraction" in observations.columns:
        # Null coverage means "not reported", which is not the same as "poor", so it is
        # kept rather than dropped.
        frame = frame.filter(
            pl.col("coverage_fraction").is_null() | (pl.col("coverage_fraction") >= min_coverage)
        )

    frame = frame.with_columns(
        _doy=pl.col(time).dt.ordinal_day(),
        _year=pl.col(time).dt.year(),
    )

    keys = [*group_by, "_year"]
    results: list[pl.DataFrame] = []

    for season in seasons:
        seasonal = (
            frame.filter(pl.col("_doy").is_between(season.start_doy, season.end_doy))
            .select([*keys, "_doy", value])
            .sort([*keys, "_doy"])
            .collect()
        )
        if seasonal.is_empty():
            continue

        rows: list[dict[str, object]] = []
        for key_values, group in seasonal.group_by(keys, maintain_order=True):
            doy = group["_doy"].to_numpy()
            magnitude = group[value].to_numpy().astype(float)
            usable = len(doy) >= min_observations and magnitude.sum() > 0

            base: dict[str, object] = dict(zip(keys, key_values, strict=True))
            base["season"] = season.name
            base["observations"] = len(doy)
            base["total"] = float(magnitude.sum())
            for q in quantiles:
                base[f"q{int(q * 100)}_doy"] = (
                    _interpolated_crossing(doy, magnitude, q) if usable else None
                )
            rows.append(base)

        results.append(pl.DataFrame(rows))

    if not results:
        return pl.DataFrame()

    return (
        pl.concat(results, how="vertical_relaxed")
        .rename({"_year": "year"})
        .sort([*group_by, "year", "season"])
    )


def _interpolated_crossing(doy: np.ndarray, magnitude: np.ndarray, quantile: float) -> float:
    """Day of year at which the cumulative curve reaches ``quantile`` of its total.

    Linear interpolation between the bracketing observations rather than the first day
    that crosses the threshold. Passage is continuous but sampled nightly, so snapping to
    a sampled day quantises the estimate to whole days -- which matters when the shift
    being measured is a few days per decade.
    """
    cumulative = np.cumsum(magnitude)
    target = quantile * cumulative[-1]
    index = int(np.searchsorted(cumulative, target, side="left"))
    index = min(index, len(doy) - 1)

    if index == 0:
        return float(doy[0])

    span = cumulative[index] - cumulative[index - 1]
    if span <= 0:
        return float(doy[index])
    fraction = (target - cumulative[index - 1]) / span
    return float(doy[index - 1] + fraction * (doy[index] - doy[index - 1]))
