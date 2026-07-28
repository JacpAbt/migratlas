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

# How far a coordinate may sit from a cell centre and still be called on-grid, as a fraction of
# a cell. Generous enough to absorb float error in a snap, tight enough to catch real
# misalignment: a half-cell offset means the coordinate is a cell *corner*, not a centre.
GRID_CENTRE_TOLERANCE = 1e-6


@dataclass(frozen=True, slots=True)
class ExportResult:
    path: str
    format: str
    """``grid`` or ``geojson``. The reader must not infer it from the extension alone."""
    rows_in: int
    rows_out: int
    generalization: str
    """The dwc:dataGeneralizations statement written alongside the data."""

    @property
    def features(self) -> int:
        """Features written, so callers can report any export uniformly."""
        return self.rows_out


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
    root: Path,
    name: str,
    *,
    value_column: str = "value",
    longitude: str = "cell_longitude",
    latitude: str = "cell_latitude",
    time_column: str | None = "period_start",
    cell_size_deg: float | None = None,
    now: datetime | None = None,
) -> ExportResult:
    """Write a gridded surface, generalised per the clearance.

    Takes a directory and a name rather than a path, because the output format is decided here
    and the extension has to follow it. A grid written to a ``.geojson`` file would be a trap
    for the next reader.

    With ``cell_size_deg`` the output is the grid itself -- parallel index arrays -- rather
    than one GeoJSON point feature per cell. Measured on the MegaMove one-degree global
    surface: 29,304 cells cost 2,909 KiB as GeoJSON and 350 KiB as a grid, because a compact
    GeoJSON point feature spends about 101 bytes carrying roughly 20 bytes of information, and
    a regular grid does not need to repeat its structure per cell. The transform is exact --
    a test pins the two representations to the same cells -- and the frontend expands it.

    Without it the output is GeoJSON, which is right for anything not on a regular grid.
    Vector tiles are not used at either size: the alternative to this was tippecanoe, which
    needs a system package the development machine cannot install, and MVT would quantise
    coordinates to a tile extent for a layer that measurably does not need tiling (33.5 MB
    heap against a 150 MB budget).

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

    # A clearance that coarsens overrides the source's own cell size, or the frontend would
    # draw generalised cells at the resolution the data no longer has.
    effective = clearance.generalization.grid_deg or cell_size_deg
    payload = (
        _grid_payload(aggregated, effective, value_column)
        if effective
        else _geojson_payload(aggregated, value_column)
    )

    destination = root / f"{name}.{'grid.json' if effective else 'geojson'}"
    root.mkdir(parents=True, exist_ok=True)
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
        # Which shape the frontend should expect. Read rather than guessed from the extension,
        # so a layer whose clearance starts coarsening cannot be misread as points.
        "format": "grid" if effective else "geojson",
    }
    # Not with_suffix: on "name.grid.json" that would yield "name.grid.meta.json".
    (root / f"{name}.meta.json").write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8")

    log.info("exported %d cells to %s", aggregated.height, destination)
    return ExportResult(
        path=str(destination),
        format="grid" if effective else "geojson",
        rows_in=frame.height,
        rows_out=aggregated.height,
        generalization=statement,
    )


def _geojson_payload(aggregated: pl.DataFrame, value_column: str) -> dict[str, object]:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [row[0], row[1]]},
                "properties": {value_column: row[2]},
            }
            for row in aggregated.iter_rows()
        ],
    }


class OffGridError(ValueError):
    """Coordinates do not lie on the cell grid they were declared to be on."""


def _grid_payload(
    aggregated: pl.DataFrame, cell_size_deg: float, value_column: str
) -> dict[str, object]:
    """The grid as integer indices from the south-west corner, plus values.

    Indices rather than coordinates: an index is two or three characters where a coordinate is
    six, and it cannot drift out of alignment with the stated cell size the way a rounded
    coordinate can. The reader reconstructs a cell centre as
    ``(index + 0.5) * cell_size_deg - 180``.

    Raises:
        OffGridError: if any coordinate is not a cell centre of ``cell_size_deg``. Encoding an
            off-grid coordinate as an index would move the data to the nearest cell centre
            without saying so, which is the kind of silent relocation the ethics gate exists to
            prevent -- and it would misreport the resolution besides.
    """
    longitude, latitude = aggregated.columns[0], aggregated.columns[1]

    def cells(column: str, offset: float) -> pl.Expr:
        return (pl.col(column) + offset) / cell_size_deg

    def off_centre(column: str, offset: float) -> pl.Expr:
        """How far a coordinate sits from the nearest cell centre, as a fraction of a cell."""
        return (cells(column, offset).mod(1.0) - 0.5).abs()

    indexed = aggregated.select(
        # floor, not round: the stored coordinate is a cell centre, so dividing by the size
        # lands mid-cell and truncation recovers the index.
        x=cells(longitude, 180.0).floor().cast(pl.Int32),
        y=cells(latitude, 90.0).floor().cast(pl.Int32),
        v=pl.col(value_column),
        residual=pl.max_horizontal(off_centre(longitude, 180.0), off_centre(latitude, 90.0)),
    )
    residuals = indexed["residual"].to_numpy()
    worst = float(residuals.max()) if residuals.size else 0.0
    if worst > GRID_CENTRE_TOLERANCE:
        msg = (
            f"Coordinates are not cell centres of a {cell_size_deg} degree grid: worst "
            f"offset {worst:.4f} of a cell. Publishing them as grid indices would move them. "
            f"Either pass the source's real cell size or export as GeoJSON."
        )
        raise OffGridError(msg)

    return {
        "format": "grid",
        "cell_size_deg": cell_size_deg,
        "value_kind": value_column,
        "x": indexed["x"].to_list(),
        "y": indexed["y"].to_list(),
        "v": indexed["v"].to_list(),
    }


__all__ = ["ExportResult", "OffGridError", "apply_generalization", "export_surface"]
