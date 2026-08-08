"""Export a station time series as one feature per station with per-week values.

The globe animates by changing a MapLibre filter or paint expression, never by rebuilding a
layer (ADR 0002). That dictates the shape: a station is one feature, and its 52 weekly values
are properties on it, so a week change is an expression evaluation rather than a fetch.

One scalar property per week -- ``w0`` to ``w51`` -- rather than a single array. MapLibre hands
array-valued properties to the paint path natively and to the query path as a JSON string, so an
``["at", week, ["get", "weeks"]]`` filter passed while drawing and failed while querying: the
layer rendered 161 stations that queryRenderedFeatures could not see. Scalars round-trip
identically in both paths. A week with no data omits its key entirely, which makes the filter a
plain ``["has", "w30"]`` and removes any need to encode null at all.

Thirty years of nightly values would be ~11,000 properties per station, so the series is
reduced to a weekly climatology. That is a deliberate loss: the globe shows the seasonal
cycle, and anyone wanting a specific night should be querying the lake, not a map layer.

Anything published *about* the change over time arrives through ``annotations`` rather than
being computed here, because a defensible trend needs confound handling this module has no
business containing.
"""

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Final

import numpy as np
import polars as pl

from migratlas.redact import delay_cutoff, snap_to_grid

if TYPE_CHECKING:
    from pathlib import Path

    from migratlas.redact import PublicationClearance

log = logging.getLogger(__name__)

WEEKS: Final = 52


@dataclass(frozen=True, slots=True)
class SeriesExport:
    path: str
    stations: int
    weeks: int
    generalization: str

    @property
    def features(self) -> int:
        """One feature per station -- the whole point of this export shape."""
        return self.stations


def weekly_climatology(
    nights: pl.DataFrame,
    *,
    site: str = "station_id",
    time_column: str = "timestamp",
    value_column: str = "magnitude",
) -> pl.DataFrame:
    """Median value per station and week of year, with the number of years behind each.

    Median rather than mean, twice over: nightly passage is heavily right-skewed, so a mean
    within a week is dominated by a few enormous nights, and a mean across years is dominated
    by a few exceptional ones. The median of nightly values is what a typical week looks like.
    """
    return (
        nights.with_columns(
            week=((pl.col(time_column).dt.ordinal_day() - 1) // 7).clip(0, WEEKS - 1),
            year=pl.col(time_column).dt.year(),
        )
        .group_by([site, "year", "week"])
        .agg(pl.col(value_column).median().alias("value"))
        .group_by([site, "week"])
        .agg(
            pl.col("value").median().alias("median"),
            pl.col("year").n_unique().alias("years"),
        )
        .sort([site, "week"])
    )


def weekly_flow(  # noqa: PLR0913 -- the column roles are all required, like the exporter's
    nights: pl.DataFrame,
    *,
    site: str = "station_id",
    time_column: str = "timestamp",
    value_column: str = "magnitude",
    direction_column: str = "direction_deg",
    speed_column: str = "speed_ms",
) -> pl.DataFrame:
    """Bearing and speed per station and week of year, from the nightly movement vectors.

    Directions cannot be averaged as numbers -- 350° and 10° mean north, not 180° -- so each
    night becomes a vector, weighted by that night's passage: where the biomass moved, not
    where the average night pointed. Within a year the vectors are averaged per week; across
    years each component takes the median, matching the value climatology's robustness to an
    exceptional year. A night the VVP fit could not give a velocity contributes nothing rather
    than a zero, which would drag the speed toward calm that never happened.
    """
    radians = pl.col(direction_column).radians()
    weighted = (
        nights.filter(
            pl.col(direction_column).is_not_null()
            & pl.col(speed_column).is_not_null()
            & pl.col(value_column).is_not_null()
        )
        .with_columns(
            week=((pl.col(time_column).dt.ordinal_day() - 1) // 7).clip(0, WEEKS - 1),
            year=pl.col(time_column).dt.year(),
            u=pl.col(speed_column) * radians.sin() * pl.col(value_column),
            v=pl.col(speed_column) * radians.cos() * pl.col(value_column),
        )
        .group_by([site, "year", "week"])
        .agg(
            u=pl.col("u").sum() / pl.col(value_column).sum(),
            v=pl.col("v").sum() / pl.col(value_column).sum(),
        )
        .group_by([site, "week"])
        .agg(u=pl.col("u").median(), v=pl.col("v").median())
    )
    bearing = pl.arctan2(pl.col("u"), pl.col("v")).degrees()
    return weighted.select(
        site,
        "week",
        bearing=pl.when(bearing < 0).then(bearing + 360).otherwise(bearing),
        speed=(pl.col("u") ** 2 + pl.col("v") ** 2).sqrt(),
    ).sort([site, "week"])


def export_station_series(  # noqa: PLR0913 -- the clearance and column roles are all required
    nights: pl.DataFrame,
    clearance: PublicationClearance,
    destination: Path,
    *,
    site: str = "station_id",
    longitude: str = "station_longitude",
    latitude: str = "station_latitude",
    time_column: str = "timestamp",
    value_column: str = "magnitude",
    direction_column: str | None = None,
    speed_column: str | None = None,
    annotations: pl.DataFrame | None = None,
    now: datetime | None = None,
) -> SeriesExport:
    """Write one feature per station carrying its weekly climatology.

    ``annotations`` is an optional frame keyed by ``site``; its remaining columns are copied
    onto each feature. That is how a trend or a significance flag reaches the globe -- computed
    by whoever can justify it, not invented here.

    A site's coordinates are generalised when the clearance asks for it. Weather radars come
    out unsnapped because the registry classifies them as not sensitive -- published
    infrastructure whose position is already in the public FCC record -- and not because this
    exporter exempts instruments. An acoustic array beside a nest would land in the same code
    path with a different classification and would be snapped.
    """
    generalization = clearance.generalization
    grid = generalization.grid_deg
    moment = now or datetime.now(UTC)

    cutoff = delay_cutoff(generalization, moment)
    frame = nights if cutoff is None else nights.filter(pl.col(time_column) <= cutoff)

    sites = frame.group_by(site).agg(
        pl.col(longitude).first().alias("lon"), pl.col(latitude).first().alias("lat")
    )
    climatology = weekly_climatology(
        frame, site=site, time_column=time_column, value_column=value_column
    ).join(sites, on=site)
    extra = [] if annotations is None else [c for c in annotations.columns if c != site]
    if annotations is not None:
        climatology = climatology.join(annotations, on=site, how="left")

    flow = None
    if direction_column is not None and speed_column is not None:
        flow = weekly_flow(
            frame,
            site=site,
            time_column=time_column,
            value_column=value_column,
            direction_column=direction_column,
            speed_column=speed_column,
        )

    features = []
    for (station,), group in climatology.group_by([site], maintain_order=True):
        ordered = group.sort("week")
        weeks = np.full(WEEKS, np.nan)
        weeks[ordered["week"].to_numpy()] = ordered["median"].to_numpy()
        # A missing week omits its key rather than carrying a null, so "no data" and "no
        # passage" cannot be confused by a reader or by a MapLibre expression.
        values = {
            f"w{index}": round(float(value), 1)
            for index, value in enumerate(weeks)
            if not np.isnan(value)
        }
        # The movement vector, same shape and same omission rule: `dw` is the bearing the
        # biomass moved toward, degrees clockwise from north, and `sw` its ground speed.
        vectors: dict[str, float | int] = {}
        if flow is not None:
            for row in flow.filter(pl.col(site) == station).iter_rows(named=True):
                vectors[f"dw{row['week']}"] = round(float(row["bearing"])) % 360
                vectors[f"sw{row['week']}"] = round(float(row["speed"]), 1)
        observed = ordered["years"].to_numpy()
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        round(snap_to_grid(float(ordered["lon"][0]), grid), 4),
                        round(snap_to_grid(float(ordered["lat"][0]), grid), 4),
                    ],
                },
                "properties": {
                    "station": station,
                    **values,
                    **vectors,
                    "weeks_present": len(values),
                    "peak": max(values.values(), default=None),
                    "years": int(observed.max()) if observed.size else 0,
                    **{name: ordered[name].to_list()[0] for name in extra},
                },
            }
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")),
        encoding="utf-8",
    )

    statement = generalization.statement()
    destination.with_suffix(".meta.json").write_text(
        json.dumps(
            {
                "source_id": clearance.source_id,
                "evidence_type": str(clearance.evidence_type),
                "realm": str(clearance.realm),
                "sensitivity": str(clearance.sensitivity),
                "dwc:dataGeneralizations": statement,
                "cleared_at": clearance.issued_at.isoformat(),
                "stations": len(features),
                "weeks": WEEKS,
                "reduction": (
                    "Weekly median of nightly values, pooled across years. Not a nightly series."
                    + (
                        " Movement vectors are magnitude-weighted weekly means, "
                        "medianed across years by component."
                        if flow is not None
                        else ""
                    )
                ),
                "annotations": extra,
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )

    log.info("exported %d stations x %d weeks to %s", len(features), WEEKS, destination)
    return SeriesExport(
        path=str(destination), stations=len(features), weeks=WEEKS, generalization=statement
    )
