"""Phase 1a report: replicate Horton et al. 2020, then extend to 2025.

Method and caveats in docs/methods/phase1-phenology.md. The analysis choices here are
theirs, not ours -- the point of a replication is to not improvise.
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np
import polars as pl

from migratlas.evidence import EvidenceType, spec_for
from migratlas.lake.reader import scan
from migratlas.metrics.phenology import Season, passage_quantiles, passage_trends

if TYPE_CHECKING:
    from collections.abc import Sequence

log = logging.getLogger(__name__)

# Horton et al. Fig. 1b,c axes: spring March-June, autumn August-November.
SPRING: Final = Season("spring", 60, 181)
AUTUMN: Final = Season("autumn", 213, 334)

# Contiguous US only. The paper used 143 CONUS stations; Alaska, Hawaii, Puerto Rico and
# Guam are in the source data but have no counterpart in the published result.
CONUS_LAT: Final = (24.0, 50.0)
CONUS_LON: Final = (-125.0, -66.0)

# Longitude bands read off their Fig. 1a station map. Approximate, and flagged as such
# wherever the flyway breakdown is reported.
FLYWAYS: Final[tuple[tuple[str, float, float], ...]] = (
    ("western", -180.0, -104.0),
    ("central", -104.0, -90.0),
    ("eastern", -90.0, 0.0),
)

# Named explicitly. `flux` holds one source today, so pooling would be invisible now and
# would silently change every number the day a second radar network is ingested.
SOURCE_ID: Final = "darkecology_daily"

# Their Fig. 2 latitude bands. Named here rather than inline so the hierarchical report can
# fit inside the same bands and be read against this one.
LATITUDE_BANDS: Final[tuple[tuple[int, int], ...]] = ((24, 32), (32, 37), (37, 42), (42, 50))

MIN_COVERAGE: Final = 0.9
MIN_NIGHTS: Final = 40
MIN_YEARS: Final = 15
QUANTILES: Final = (0.1, 0.5, 0.9)

PUBLISHED: Final = {
    "spring_q50": "-0.60 +/- 0.15",
    "autumn_western": "-0.89 +/- 0.14",
    "autumn_central": "-0.34 +/- 0.18",
    "autumn_eastern": "-0.52 +/- 0.12",
}


@dataclass(frozen=True, slots=True)
class Trend:
    """A mean decadal trend across stations, with a normal-approximation interval."""

    label: str
    stations: int
    days_per_decade: float
    ci95: float

    def __str__(self) -> str:
        return (
            f"{self.label:<22} n={self.stations:>3}  "
            f"{self.days_per_decade:+.2f} +/- {self.ci95:.2f}"
        )


def load_conus_traffic(window_kind: str = "night") -> pl.DataFrame:
    """Filtered reflectivity traffic for contiguous-US stations, for one window kind.

    ``window_kind="day"`` gives the placebo series: nocturnal migration does not happen by
    day, so a trend there points at the instrument or the processing rather than at birds.
    """
    return (
        scan(EvidenceType.FLUX, source_id=SOURCE_ID)
        .filter(
            pl.col("window_kind") == window_kind,
            pl.col("quantity") == "reflectivity_traffic",
            pl.col("station_latitude").is_between(*CONUS_LAT),
            pl.col("station_longitude").is_between(*CONUS_LON),
        )
        .select(
            "station_id",
            "timestamp",
            "magnitude",
            "coverage_fraction",
            "station_latitude",
            "station_longitude",
        )
        .collect()
    )


def flyway_of(longitude: float) -> str:
    for name, west, east in FLYWAYS:
        if west <= longitude < east:
            return name
    return "other"


def station_slopes(nights: pl.DataFrame, *, max_year: int) -> pl.DataFrame:
    """Per-station least-squares trend in passage date, one row per station-season-quantile."""
    quantiles = passage_quantiles(
        nights.filter(pl.col("timestamp").dt.year() <= max_year),
        spec_for(EvidenceType.FLUX),
        seasons=[SPRING, AUTUMN],
        quantiles=QUANTILES,
        min_coverage=MIN_COVERAGE,
        min_observations=MIN_NIGHTS,
    )
    sites = nights.group_by("station_id").agg(
        pl.col("station_latitude").first(), pl.col("station_longitude").first()
    )
    slopes = passage_trends(
        quantiles,
        columns=[f"q{int(q * 100)}_doy" for q in QUANTILES],
        min_years=MIN_YEARS,
    )
    if slopes.is_empty():
        return slopes

    return slopes.join(sites, on="station_id").select(
        pl.exclude("station_latitude", "station_longitude"),
        pl.col("station_latitude").alias("latitude"),
        pl.col("station_longitude").map_elements(flyway_of, return_dtype=pl.String).alias("flyway"),
    )


def _trend(label: str, values: pl.Series) -> Trend | None:
    """Mean and normal-approximation interval over per-station slopes.

    Computed in numpy rather than polars: polars' mean/std are typed to a union including
    timedelta, which is right for its generality and awkward here.
    """
    if values.is_empty():
        return None
    slopes = values.to_numpy().astype(float)
    ci = 1.96 * float(slopes.std(ddof=1)) / np.sqrt(slopes.size) if slopes.size > 1 else 0.0
    return Trend(label, int(slopes.size), float(slopes.mean()), ci)


def summarise(slopes: pl.DataFrame, *, bands: Sequence[tuple[int, int]]) -> list[str]:
    """Render the trend table for one time window."""
    lines: list[str] = []
    for season in ("spring", "autumn"):
        seasonal = slopes.filter(pl.col("season") == season)
        lines.append(f"\n  {season}")
        for column in (f"q{int(q * 100)}_doy" for q in QUANTILES):
            trend = _trend(column, seasonal.filter(pl.col("quantile") == column)["days_per_decade"])
            if trend:
                lines.append(f"    {trend}")

        median = seasonal.filter(pl.col("quantile") == "q50_doy")
        lines.append("    by flyway, q50 (longitude bands approximate):")
        for name, _, _ in FLYWAYS:
            trend = _trend(name, median.filter(pl.col("flyway") == name)["days_per_decade"])
            if trend:
                lines.append(f"      {trend}")

        lines.append("    by latitude band, q50:")
        for low, high in bands:
            selected = median.filter(pl.col("latitude").is_between(low, high, closed="left"))
            trend = _trend(f"{low}-{high}N", selected["days_per_decade"])
            if trend:
                lines.append(f"      {trend}")
    return lines


def render() -> str:
    """Run both windows and render the comparison."""
    nights = load_conus_traffic()
    bands = LATITUDE_BANDS

    out = [
        "Phase 1a -- nocturnal passage phenology",
        "=" * 70,
        f"CONUS nights: {nights.height:,} rows, {nights['station_id'].n_unique()} stations",
        "Metric: date by which 50% of cumulative seasonal passage occurred (Horton et al.).",
        f"Filters: coverage >= {MIN_COVERAGE}, >= {MIN_NIGHTS} nights/season-year, "
        f">= {MIN_YEARS} years/station.",
    ]

    for max_year, label in ((2018, "REPLICATION -- Horton et al. window"), (2025, "EXTENSION")):
        out += ["", "=" * 70, f"{label}  (1995-{max_year})", "=" * 70]
        out += summarise(station_slopes(nights, max_year=max_year), bands=bands)

    out += [
        "",
        "=" * 70,
        "Published, for comparison (143 CONUS stations, 1995-2018)",
        f"  spring q50        {PUBLISHED['spring_q50']} d/decade",
        f"  autumn western    {PUBLISHED['autumn_western']}",
        f"  autumn central    {PUBLISHED['autumn_central']}",
        f"  autumn eastern    {PUBLISHED['autumn_eastern']}",
        "  spring: advance at 35/40/45N, no change at 30N",
        "",
        "The extension is NOT blind and the dual-polarisation break is NOT yet modelled.",
        "See docs/methods/phase1-phenology.md before quoting any number here.",
    ]
    return "\n".join(out)
