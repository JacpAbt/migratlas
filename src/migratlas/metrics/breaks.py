"""Find instrument outages from data availability alone.

An upgrade that takes a sensor offline leaves a run of absent days. Detecting it uses only
*whether* a record exists, never its value, so a break found this way cannot import the
trend it is later used to control for.

Detection is not the same as knowing. See ``docs/methods/phase1-phenology.md``: for the
NEXRAD dual-polarisation rollout this method matched the one documented non-beta station
exactly and produced a plausible fleet-wide distribution, but could not be validated
against the beta sites. Treat the output as one specification among several, never as
ground truth.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING

import polars as pl

if TYPE_CHECKING:
    from collections.abc import Iterable


@dataclass(frozen=True, slots=True)
class Outage:
    site: str
    start: date
    days: int


def find_outages(  # noqa: PLR0913 -- every argument is a detection threshold worth stating
    observations: pl.DataFrame,
    *,
    site_column: str,
    time_column: str,
    window: tuple[date, date],
    min_days: int = 4,
    max_days: int = 40,
) -> list[Outage]:
    """Longest qualifying absence per site inside ``window``.

    ``max_days`` excludes a site that was simply not reporting for months, which is a
    different phenomenon from a scheduled upgrade.
    """
    days = (
        observations.select(
            pl.col(site_column).alias("site"),
            pl.col(time_column).dt.date().alias("day"),
        )
        .unique()
        .group_by("site")
        .agg(pl.col("day"))
    )

    outages: list[Outage] = []
    for site, present in days.iter_rows():
        gap = _longest_gap(set(present), *window)
        if gap and min_days <= gap[1] <= max_days:
            outages.append(Outage(site=site, start=gap[0], days=gap[1]))
    return outages


def _longest_gap(present: set[date], low: date, high: date) -> tuple[date, int] | None:
    best: tuple[date, int] | None = None
    cursor, start, run = low, None, 0
    while cursor <= high:
        if cursor not in present:
            if start is None:
                start = cursor
            run += 1
        else:
            if start is not None and (best is None or run > best[1]):
                best = (start, run)
            start, run = None, 0
        cursor += timedelta(days=1)
    if start is not None and (best is None or run > best[1]):
        best = (start, run)
    return best


def as_frame(outages: Iterable[Outage]) -> pl.DataFrame:
    """Outages as a frame, for joining onto a per-site analysis."""
    rows = [{"station_id": o.site, "break_date": o.start, "outage_days": o.days} for o in outages]
    if not rows:
        return pl.DataFrame(
            schema={"station_id": pl.String, "break_date": pl.Date, "outage_days": pl.Int64}
        )
    return pl.DataFrame(rows)
