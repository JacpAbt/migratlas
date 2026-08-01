"""Terrestrial mammal movement timing, and whether the tracks can support a trend at all.

Pre-registered in ``docs/methods/phase1d-tracks.md``. The order here is the order that note commits
to: screen coverage first, and only fit a trend if a cell survives. Prediction 1 says fewer than
fifteen cells will, and the stop condition says that if none does, no trend is reported and the
output is a detectability entry instead.

**The metric is the analogue of the radar's ``q50_doy``.** For the radar, that is the day half the
season's passage has gone by. For one animal in one year it is the day it crosses the middle of its
own annual latitudinal range, heading north -- so both response variables mean "the day the movement
was half done" rather than two different things sharing a unit.

**The unit is (cell x taxon), and the bare cell was wrong.** The pre-registration chose a 1-degree
cell to match the radar's per-station trend, and the first run showed how far that analogy goes: a
radar station measures one aggregate signal, but cell (51, -116) at Ya Ha Tinda holds *elk and
wolves*, and pooling their medians merges a predator's calendar with its prey's. The cell still
earns its place -- Bylot's two fox studies pool into one 17-year series where neither reaches 15
alone -- so the fix adds the taxon rather than abandoning the cell. Closer to `phase1b-marine`'s
species-region unit than the note anticipated.

**It is a timing metric and not a migration detector, and the first run proved it the hard way.**
The pre-registration expected residents to yield no date. In fact 1,477 of 1,517 individual-years
get one, because *any* animal that moves crosses the middle of its own annual range. Svalbard's
sedentary reindeer score as readily as the elk. So the date says when a year's latitudinal movement
was half done, whatever its size -- a phenology question, and all this is. Deciding whether an
animal migrates needs a different tool (net-squared-displacement fitting), and this is not it.
"""

import logging
from typing import TYPE_CHECKING, Final, NamedTuple

import numpy as np
import polars as pl

from migratlas.evidence import EvidenceType
from migratlas.lake.reader import scan
from migratlas.metrics.thermal import Trend, _trend
from migratlas.reports.phase1 import MIN_YEARS

if TYPE_CHECKING:
    from collections.abc import Sequence

log = logging.getLogger(__name__)

CELL: Final = 1.0
"""Degrees. The unit the radar's own trend uses, per station; here, per place."""

MIN_FIXES: Final = 30
"""Fixes an individual-year needs before it can carry a date."""

MIN_MONTHS: Final = 6
"""Calendar months an individual-year must span.

A collar that failed in April cannot contribute a spring date, and a metric defined on an annual
range needs enough of the year to have a range at all.
"""

SENSORS_FOR_A_BREAK: Final = 2
"""Instruments a cell needs before there is a break to measure. One instrument cannot disagree."""

PREDICTED_CELLS: Final = 15
"""Prediction 1's threshold: fewer than this many cells were expected to clear the year floor.

Named rather than inlined because it is a claim registered before the run, not a tuning parameter.
The answer was two.
"""

SHOWN: Final = 12
"""Cells listed in the coverage table before the rest are summarised."""

MIN_INDIVIDUALS: Final = 3
"""Animals a cell-year needs before its median date is reported.

One animal's date is one animal's decision. The radar's equivalent is a station-night threshold, and
the same argument applies: a cell-year resting on a single collar is an anecdote with a decimal
point.
"""


class Cell(NamedTuple):
    """One 1-degree cell's coverage, and whether it can carry a trend."""

    lat: int
    lon: int
    years: int
    individual_years: int
    sensors: int
    first: int
    last: int

    @property
    def detectable(self) -> bool:
        return self.years >= MIN_YEARS


def _fixes(sources: Sequence[str] | None = None) -> pl.LazyFrame:
    return scan(EvidenceType.TRACK, source_id=sources).select(
        "source_id",
        "individual_id",
        "taxon_label",
        "sensor_type",
        "latitude",
        "longitude",
        year=pl.col("timestamp").dt.year(),
        month=pl.col("timestamp").dt.month(),
        doy=pl.col("timestamp").dt.ordinal_day(),
        timestamp="timestamp",
    )


def individual_years(sources: Sequence[str] | None = None) -> pl.DataFrame:
    """One row per (individual, year) that clears the fix and coverage thresholds.

    The cell is the *centroid* of that individual-year's own fixes. A migrating animal crosses many
    cells, so the cell has to mean "where this animal was based this year" rather than "where it was
    when something happened" -- the latter would file the same journey under a different place
    depending on which end of it the metric looked at.
    """
    return (
        _fixes(sources)
        .group_by("source_id", "individual_id", "taxon_label", "year")
        .agg(
            fixes=pl.len(),
            months=pl.col("month").n_unique(),
            lat_mean=pl.col("latitude").mean(),
            lon_mean=pl.col("longitude").mean(),
            lat_min=pl.col("latitude").min(),
            lat_max=pl.col("latitude").max(),
            sensors=pl.col("sensor_type").n_unique(),
            sensor=pl.col("sensor_type").first(),
        )
        .filter(pl.col("fixes") >= MIN_FIXES, pl.col("months") >= MIN_MONTHS)
        .with_columns(
            cell_lat=(pl.col("lat_mean") / CELL).floor().cast(pl.Int32),
            cell_lon=((pl.col("lon_mean") + 180) / CELL).floor().cast(pl.Int32),
            latitudinal_range=pl.col("lat_max") - pl.col("lat_min"),
        )
        .collect()
    )


def coverage(eligible: pl.DataFrame) -> list[Cell]:
    """Per-cell coverage, which is the pre-registered go/no-go."""
    grouped = (
        eligible.group_by("cell_lat", "cell_lon")
        .agg(
            years=pl.col("year").n_unique(),
            individual_years=pl.len(),
            sensors=pl.col("sensor").n_unique(),
            first=pl.col("year").min(),
            last=pl.col("year").max(),
        )
        .sort("years", descending=True)
    )
    return [
        Cell(
            lat=row["cell_lat"],
            lon=row["cell_lon"],
            years=row["years"],
            individual_years=row["individual_years"],
            sensors=row["sensors"],
            first=row["first"],
            last=row["last"],
        )
        for row in grouped.iter_rows(named=True)
    ]


def _crossing(doy: np.ndarray, latitude: np.ndarray, midpoint: float) -> float | None:
    """First day-of-year the animal is at or north of ``midpoint`` having been south of it.

    Requires the south-then-north order rather than just the first day above the midpoint. An animal
    that begins its year already north and moves south would otherwise be handed a date of day one,
    which is a statement about the calendar rather than about the animal.
    """
    order = np.argsort(doy)
    days, lats = doy[order], latitude[order]
    below = lats < midpoint
    if not below.any():
        return None
    first_below = int(np.argmax(below))
    after = np.nonzero(lats[first_below:] >= midpoint)[0]
    if after.size == 0:
        return None
    return float(days[first_below + int(after[0])])


def passage_dates(eligible: pl.DataFrame, sources: Sequence[str] | None = None) -> pl.DataFrame:
    """The crossing day for every eligible individual-year that has one."""
    keys = eligible.select("source_id", "individual_id", "year", "lat_min", "lat_max", "sensor")
    fixes = (
        _fixes(sources)
        .select("source_id", "individual_id", "year", "latitude", "doy")
        .collect()
        .join(keys, on=["source_id", "individual_id", "year"], how="inner")
    )

    rows: list[dict[str, object]] = []
    grouping = ["source_id", "individual_id", "year", "sensor"]
    for (source, individual, year, sensor), group in fixes.group_by(grouping, maintain_order=True):
        low, high = group["lat_min"][0], group["lat_max"][0]
        if high - low <= 0:
            continue
        day = _crossing(
            group["doy"].to_numpy(),
            group["latitude"].to_numpy(),
            float(low) + (float(high) - float(low)) / 2,
        )
        if day is None:
            continue
        rows.append(
            {
                "source_id": str(source),
                "individual_id": str(individual),
                "year": int(year),
                "sensor": str(sensor),
                "crossing_doy": day,
            }
        )
    return pl.DataFrame(
        rows,
        schema={
            "source_id": pl.String,
            "individual_id": pl.String,
            "year": pl.Int32,
            "sensor": pl.String,
            "crossing_doy": pl.Float64,
        },
    )


class CellTrend(NamedTuple):
    """One cell's timing trend, with the protocol break it had to survive."""

    lat: int
    lon: int
    taxa: tuple[str, ...]
    sources: tuple[str, ...]
    trend: Trend | None
    years: int
    individual_years: int
    sensors: tuple[str, ...]
    break_shift: float | None
    """Days the sensor change moves the date, where a cell holds two. None where it holds one."""


def _sensor_break(dated: pl.DataFrame) -> float | None:
    """Mean date difference between sensor types, in overlapping years where possible.

    Mountain caribou mixes GPS with older radio transmitters whose fix rates differ by an order of
    magnitude, and `phase1c` is the standing reminder that an instrument change reads as a
    behaviour change. Reported rather than corrected: a shift this is measuring may be real
    behaviour in the years the instruments changed, and the honest output is the number plus the
    warning, not a silently adjusted series.
    """
    sensors = sorted(dated["sensor"].unique().to_list())
    if len(sensors) < SENSORS_FOR_A_BREAK:
        return None
    means = dated.group_by("sensor").agg(mean=pl.col("crossing_doy").mean()).sort("sensor")
    return float(means["mean"][-1] - means["mean"][0])


def trends(dated: pl.DataFrame, eligible: pl.DataFrame) -> list[CellTrend]:
    """A timing trend per (1-degree cell, taxon).

    Two things this unit gets right that neither alternative does. Bylot's cell holds *both* fox
    studies, seventeen years and two instruments between them, where neither study reaches fifteen
    years alone -- so fitting per source would report that no fox series is long enough, true of
    each study and false of the place. And Ya Ha Tinda's cell holds elk *and* wolves, so fitting
    per bare cell would merge a predator's calendar with its prey's.

    Rows with no taxon label are dropped rather than pooled into an "unlabelled" series: the elk
    study ships 10,438 of them, and a series whose species is unknown cannot be read.

    Never pooled across cells or taxa, by prediction 4.
    """
    keyed = dated.join(
        eligible.select(
            "source_id", "individual_id", "year", "cell_lat", "cell_lon", "taxon_label"
        ),
        on=["source_id", "individual_id", "year"],
        how="inner",
    ).filter(pl.col("taxon_label").is_not_null())
    out: list[CellTrend] = []
    keys = ["cell_lat", "cell_lon", "taxon_label"]
    for (lat, lon, taxon), group in keyed.group_by(keys, maintain_order=True):
        per_year = (
            group.group_by("year")
            .agg(median=pl.col("crossing_doy").median(), animals=pl.col("individual_id").n_unique())
            .filter(pl.col("animals") >= MIN_INDIVIDUALS)
            .sort("year")
        )
        fitted = (
            _trend(per_year["year"].to_numpy(), per_year["median"].to_numpy())
            if per_year.height
            else None
        )
        out.append(
            CellTrend(
                lat=int(lat),
                lon=int(lon),
                taxa=(str(taxon),),
                sources=tuple(sorted(group["source_id"].unique().to_list())),
                trend=fitted,
                years=per_year.height,
                individual_years=group.height,
                sensors=tuple(sorted(group["sensor"].unique().to_list())),
                break_shift=_sensor_break(group),
            )
        )
    return sorted(out, key=lambda cell: -cell.years)


def render() -> str:
    """The screen, then the metric only if the screen allows it."""
    out: list[str] = []
    eligible = individual_years()
    out += [
        f"Eligible individual-years: {eligible.height:,} "
        f"(>= {MIN_FIXES} fixes, >= {MIN_MONTHS} months)",
        f"  from {eligible['individual_id'].n_unique():,} individuals "
        f"across {eligible['source_id'].n_unique()} sources",
        "",
    ]

    cells = coverage(eligible)
    detectable = [cell for cell in cells if cell.detectable]
    out += [
        "=" * 78,
        f"COVERAGE SCREEN -- the pre-registered go/no-go, unit = {CELL:.0f}-degree cell",
        "=" * 78,
        f"cells touched: {len(cells)}",
        f"cells with >= {MIN_YEARS} distinct years: {len(detectable)}",
        "",
        f"prediction 1 said fewer than {PREDICTED_CELLS} cells would clear it: "
        f"{'HOLDS' if len(detectable) < PREDICTED_CELLS else 'FAILS'}",
        "",
    ]
    for cell in cells[:SHOWN]:
        mark = "  <- detectable" if cell.detectable else ""
        out.append(
            f"  cell ({cell.lat:>3}, {cell.lon:>3})  {cell.years:>2} years "
            f"{cell.first}-{cell.last}  {cell.individual_years:>4} individual-years  "
            f"{cell.sensors} sensor(s){mark}"
        )
    if len(cells) > SHOWN:
        out.append(f"  ... and {len(cells) - SHOWN} more")

    if not detectable:
        out += [
            "",
            "STOP. No cell reaches the fifteen-year floor, so no trend is reported. This was",
            "pre-registered: the output is a detectability entry -- terrestrial non-bird movement,",
            "coverage present, change not measurable -- which is the same shape as the marine null",
            "and is content for the coverage claim rather than a disappointment.",
        ]
        return "\n".join(out)

    dated = passage_dates(eligible)
    out += [
        "",
        "=" * 78,
        "TIMING -- day the animal crosses the middle of its own annual latitudinal range",
        "=" * 78,
        f"individual-years with a crossing: {dated.height:,} of {eligible.height:,} eligible",
        "  (the rest have no crossing at all. Note how few: any animal that moves crosses the",
        "   middle of its own range, so this times movement rather than detecting migration)",
        "",
    ]
    for fitted in trends(dated, eligible):
        if not fitted.years:
            continue
        where = f"cell ({fitted.lat}, {fitted.lon})"
        taxa = ", ".join(fitted.taxa) or "unlabelled"
        out.append(f"  {where}  {taxa}")
        out.append(
            f"    {len(fitted.sources)} source(s), {fitted.individual_years:>4} individual-years, "
            f"{fitted.years} year(s) with >= {MIN_INDIVIDUALS} animals"
        )
        out.append(f"    sensors: {', '.join(fitted.sensors)}")
        if fitted.trend is None:
            out.append(f"    no trend: under the {MIN_YEARS}-year floor after the animal threshold")
        else:
            verdict = (
                "distinguishable from zero"
                if fitted.trend.distinguishable
                else "NOT distinguishable from zero"
            )
            out.append(
                f"    {fitted.trend.per_decade:+.2f} +/- {1.96 * fitted.trend.stderr:.2f} "
                f"days per decade over {fitted.trend.years} years -- {verdict}"
            )
        if fitted.break_shift is not None:
            out.append(
                f"    PROTOCOL BREAK: the sensor types differ by {fitted.break_shift:+.1f} days, "
                f"which is what prediction 3 asked about."
            )
        out.append("")

    out += [
        "Not pooled across cells, by pre-registration. Five species on three continents do not",
        "share a response and a number averaged over them would be about nothing.",
    ]
    return "\n".join(out)
