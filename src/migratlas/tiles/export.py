"""Export publishable layers. Every entry point demands a PublicationClearance.

This is where the capability designed in Phase 0 is finally spent. There is no function here
that writes a file without a clearance argument, so forgetting the ethics gate is a type
error rather than a reviewer's oversight -- and applying the generalisation is this module's
job, not the caller's, so it cannot be forgotten either.
"""

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import polars as pl

from migratlas.redact import GRID_QUOTIENT_PRECISION, delay_cutoff

if TYPE_CHECKING:
    from pathlib import Path

    from migratlas.redact import PublicationClearance

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ExportResult:
    path: str
    rows_in: int
    rows_out: int
    generalization: str
    """The dwc:dataGeneralizations statement written alongside the data."""


def snap_expr(column: str, grid_deg: float) -> pl.Expr:
    """Vectorised equivalent of :func:`migratlas.redact.snap_to_grid`.

    Duplicating the formula is deliberate -- ``map_elements`` would run a Python call per
    row over millions of cells. ``test_snap_expr_matches_the_scalar_definition`` pins the two
    together so they cannot drift.
    """
    index = (pl.col(column) / grid_deg).round(GRID_QUOTIENT_PRECISION).floor()
    return index * grid_deg + grid_deg / 2


def apply_generalization(  # noqa: PLR0913 -- each column role must be named explicitly
    frame: pl.DataFrame,
    clearance: PublicationClearance,
    *,
    longitude: str,
    latitude: str,
    time_column: str | None = None,
    identifier_columns: tuple[str, ...] = (),
    now: datetime | None = None,
) -> pl.DataFrame:
    """Degrade ``frame`` to exactly what the clearance permits.

    Order matters: drop recent records first, then coarsen coordinates, then remove
    identifiers. Coarsening before dropping would leave the recent rows in the aggregate.
    """
    generalization = clearance.generalization
    now = now or datetime.now(UTC)
    out = frame

    cutoff = delay_cutoff(generalization, now)
    if cutoff is not None and time_column is not None:
        before = out.height
        out = out.filter(pl.col(time_column) <= cutoff)
        if out.height != before:
            log.info(
                "withheld %d rows newer than %d days",
                before - out.height,
                generalization.delay_days,
            )

    if generalization.grid_deg is not None:
        grid = generalization.grid_deg
        out = out.with_columns(
            **{
                longitude: snap_expr(longitude, grid),
                latitude: snap_expr(latitude, grid),
            }
        )

    if generalization.drop_individual_id:
        present = [column for column in identifier_columns if column in out.columns]
        if present:
            out = out.drop(present)

    return out


def export_surface(  # noqa: PLR0913 -- the clearance and the column roles are all required
    frame: pl.DataFrame,
    clearance: PublicationClearance,
    destination: Path,
    *,
    value_column: str = "value",
    longitude: str = "cell_longitude",
    latitude: str = "cell_latitude",
    time_column: str | None = "period_start",
    now: datetime | None = None,
) -> ExportResult:
    """Write a gridded surface as GeoJSON, generalised per the clearance.

    GeoJSON rather than vector tiles for now: a one-degree global grid is tens of thousands
    of cells, which a browser loads in one request. Tiling earns its complexity when a layer
    is large enough to need it, and saying so here is cheaper than pretending otherwise.

    A sibling ``.meta.json`` carries the attribution and the generalisation statement, so a
    published layer can never be separated from the terms it was published under.
    """
    generalised = apply_generalization(
        frame,
        clearance,
        longitude=longitude,
        latitude=latitude,
        time_column=time_column,
        identifier_columns=("individual_id", "station_id", "occurrence_id"),
        now=now,
    )

    # Coarsening merges cells, so values have to be recombined rather than duplicated.
    keys = [longitude, latitude]
    aggregated = (
        generalised.group_by(keys).agg(pl.col(value_column).sum().alias(value_column)).sort(keys)
    )

    features = [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [row[0], row[1]]},
            "properties": {value_column: row[2]},
        }
        for row in aggregated.iter_rows()
    ]
    payload = {"type": "FeatureCollection", "features": features}

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")

    statement = clearance.generalization.statement()
    meta = {
        "source_id": clearance.source_id,
        "evidence_type": str(clearance.evidence_type),
        "realm": str(clearance.realm),
        "sensitivity": str(clearance.sensitivity),
        "dwc:dataGeneralizations": statement,
        "permission_reference": clearance.permission_reference,
        "cleared_at": clearance.issued_at.isoformat(),
        "cells": aggregated.height,
    }
    destination.with_suffix(".meta.json").write_text(
        json.dumps(meta, indent=1) + "\n", encoding="utf-8"
    )

    log.info("exported %d cells to %s", aggregated.height, destination)
    return ExportResult(
        path=str(destination),
        rows_in=frame.height,
        rows_out=aggregated.height,
        generalization=statement,
    )


__all__ = ["ExportResult", "apply_generalization", "export_surface"]
