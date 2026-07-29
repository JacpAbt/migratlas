"""The gate is a capability, and this is where it gets spent.

The point of these tests is that nothing publishable can be written without a clearance, and
that the generalisation the clearance mandates is actually applied rather than merely
recorded.
"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl
import pytest

from migratlas.evidence import EvidenceType, Realm, TaxonScope
from migratlas.redact import (
    OwnerPermission,
    PublicationClearance,
    PublicationRefusedError,
    Sensitivity,
    clear_for_publication,
    snap_to_grid,
)
from migratlas.tiles.export import (
    apply_generalization,
    export_surface,
    snap_expr,
)

NOW = datetime(2026, 7, 28, tzinfo=UTC)


def _clearance(
    sensitivity: Sensitivity = Sensitivity.LOW,
    evidence_type: EvidenceType = EvidenceType.ABUNDANCE_SURFACE,
    permission: OwnerPermission | None = None,
) -> PublicationClearance:
    return clear_for_publication(
        source_id="test",
        evidence_type=evidence_type,
        realm=Realm.MARINE,
        sensitivity=sensitivity,
        taxon_scope=TaxonScope.EXACT,
        taxon_key=12345,
        redistribution_allowed=True,
        permission=permission,
        now=NOW,
    )


def _surface() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "cell_longitude": [10.2, 10.8, -3.4, 100.0],
            "cell_latitude": [20.2, 20.8, -30.4, 0.0],
            "value": [1.0, 2.0, 4.0, 8.0],
            "period_start": [NOW - timedelta(days=d) for d in (5000, 5000, 5000, 1)],
            "individual_id": ["a", "b", "c", "d"],
        }
    )


# --- The formula duplication is pinned -------------------------------------
@pytest.mark.parametrize("grid", [0.1, 0.25, 0.5, 1.0, 2.0])
def test_snap_expr_matches_the_scalar_definition(grid: float) -> None:
    """Two implementations exist for speed; this is what stops them drifting."""
    values = [-179.9, -104.3, -45.6, -0.1, 0.0, 0.4, 12.7, 58.6, 179.9]
    frame = pl.DataFrame({"x": values})
    vectorised = frame.select(snap_expr("x", grid))["x"].to_list()
    scalar = [snap_to_grid(v, grid) for v in values]
    assert vectorised == pytest.approx(scalar)


# --- Generalisation is applied, not just recorded ---------------------------
def test_coordinates_are_coarsened_to_the_permitted_grid() -> None:
    clearance = _clearance(evidence_type=EvidenceType.TRACK, sensitivity=Sensitivity.MODERATE)
    assert clearance.generalization.grid_deg == 1.0
    out = apply_generalization(
        _surface(), clearance, longitude="cell_longitude", latitude="cell_latitude", now=NOW
    )
    # 10.2 and 10.8 both fall in the same one-degree cell, centred on 10.5.
    snapped = sorted(out["cell_longitude"].to_list())
    assert snapped == pytest.approx([-3.5, 10.5, 10.5, 100.5])


def test_identifiers_are_removed_when_the_clearance_says_so() -> None:
    clearance = _clearance(evidence_type=EvidenceType.TRACK)
    assert clearance.generalization.drop_individual_id is True
    out = apply_generalization(
        _surface(),
        clearance,
        longitude="cell_longitude",
        latitude="cell_latitude",
        identifier_columns=("individual_id",),
        now=NOW,
    )
    assert "individual_id" not in out.columns


def test_recent_records_are_withheld() -> None:
    clearance = _clearance(evidence_type=EvidenceType.TRACK)
    assert clearance.generalization.delay_days == 30
    out = apply_generalization(
        _surface(),
        clearance,
        longitude="cell_longitude",
        latitude="cell_latitude",
        time_column="period_start",
        now=NOW,
    )
    # The row one day old is inside the withheld window.
    assert out.height == 3


def test_aggregate_clearance_leaves_coordinates_alone() -> None:
    """An already-summarised surface at LOW sensitivity publishes as-is."""
    clearance = _clearance(sensitivity=Sensitivity.LOW)
    assert clearance.generalization.grid_deg is None
    out = apply_generalization(
        _surface(), clearance, longitude="cell_longitude", latitude="cell_latitude", now=NOW
    )
    assert out["cell_longitude"].to_list() == _surface()["cell_longitude"].to_list()


# --- Export ----------------------------------------------------------------
def test_export_writes_geojson_and_a_terms_sidecar(tmp_path: Path) -> None:
    """A published layer must never be separable from the terms it was published under."""
    result = export_surface(_surface(), _clearance(), tmp_path, "layer", now=NOW)

    assert result.format == "geojson"
    assert result.path.endswith("layer.geojson")
    payload = json.loads(Path(result.path).read_text(encoding="utf-8"))
    assert payload["type"] == "FeatureCollection"
    assert len(payload["features"]) == result.rows_out

    meta = json.loads((tmp_path / "layer.meta.json").read_text(encoding="utf-8"))
    assert meta["source_id"] == "test"
    assert meta["format"] == "geojson"
    assert meta["dwc:dataGeneralizations"] == result.generalization
    assert meta["cleared_at"] == NOW.isoformat()


def _gridded() -> pl.DataFrame:
    """A surface whose coordinates really are one-degree cell centres."""
    return _surface().with_columns(
        cell_longitude=pl.Series([10.5, 11.5, -3.5, 100.5]),
        cell_latitude=pl.Series([20.5, 21.5, -30.5, 0.5]),
    )


def test_a_grid_export_decodes_to_the_same_cells_as_geojson(tmp_path: Path) -> None:
    """The compaction must be exact: same cells, same values, 8x smaller.

    This is the whole justification for a second format, so it is pinned rather than trusted.
    """
    points = export_surface(_gridded(), _clearance(), tmp_path / "a", "layer", now=NOW)
    grid = export_surface(
        _gridded(), _clearance(), tmp_path / "b", "layer", cell_size_deg=1.0, now=NOW
    )
    assert grid.format == "grid"
    assert grid.path.endswith("layer.grid.json")

    expected = {
        (
            round(f["geometry"]["coordinates"][0], 6),
            round(f["geometry"]["coordinates"][1], 6),
            f["properties"]["value"],
        )
        for f in json.loads(Path(points.path).read_text(encoding="utf-8"))["features"]
    }

    payload = json.loads(Path(grid.path).read_text(encoding="utf-8"))
    size = payload["cell_size_deg"]
    decoded = {
        (
            round((x + 0.5) * size - 180.0, 6),
            round((y + 0.5) * size - 90.0, 6),
            v,
        )
        for x, y, v in zip(payload["x"], payload["y"], payload["v"], strict=True)
    }
    assert decoded == expected


def test_a_grid_file_is_never_named_geojson(tmp_path: Path) -> None:
    """A grid in a .geojson file is a trap; the extension follows the format."""
    result = export_surface(_gridded(), _clearance(), tmp_path, "layer", cell_size_deg=1.0, now=NOW)
    assert not result.path.endswith(".geojson")
    assert not (tmp_path / "layer.geojson").exists()


def test_a_coarsening_clearance_forces_the_grid_size_it_imposed(tmp_path: Path) -> None:
    """Publishing generalised cells at the source's finer size would overstate the resolution."""
    clearance = _clearance(evidence_type=EvidenceType.TRACK, sensitivity=Sensitivity.MODERATE)
    assert clearance.generalization.grid_deg == 1.0
    result = export_surface(_surface(), clearance, tmp_path, "layer", cell_size_deg=0.1, now=NOW)
    payload = json.loads(Path(result.path).read_text(encoding="utf-8"))
    assert payload["cell_size_deg"] == 1.0


def test_coarsening_merges_cells_by_summing_not_duplicating(tmp_path: Path) -> None:
    """Snapping two cells together must combine their values, or the total inflates."""
    clearance = _clearance(evidence_type=EvidenceType.TRACK, sensitivity=Sensitivity.MODERATE)
    # Only the three old rows survive the 90-day delay at MODERATE.
    result = export_surface(_surface(), clearance, tmp_path, "merged", now=NOW)
    assert result.rows_out < result.rows_in
    # A clearance that snaps to a grid produces a grid, whatever the caller asked for.
    assert result.format == "grid"

    payload = json.loads(Path(result.path).read_text(encoding="utf-8"))
    total = sum(payload["v"])
    # 1 + 2 + 4 from the surviving rows; the 8 was withheld as too recent.
    assert total == pytest.approx(7.0)


def test_export_is_impossible_without_a_clearance() -> None:
    """There is no code path that writes a layer from an unpublishable combination."""
    with pytest.raises(PublicationRefusedError):
        _clearance(sensitivity=Sensitivity.HIGH, evidence_type=EvidenceType.TRACK)


def test_permission_relaxes_what_the_export_degrades() -> None:
    permission = OwnerPermission(
        reference="perm-test",
        granted_by="Owner",
        contact="owner@example.org",
        granted_on="2026-07-01",
        max_grid_deg=None,
        allow_individual_id=True,
        min_delay_days=0,
    )
    clearance = _clearance(evidence_type=EvidenceType.TRACK, permission=permission)
    out = apply_generalization(
        _surface(),
        clearance,
        longitude="cell_longitude",
        latitude="cell_latitude",
        time_column="period_start",
        identifier_columns=("individual_id",),
        now=NOW,
    )
    assert out.height == _surface().height
    assert "individual_id" in out.columns
    assert out["cell_longitude"].to_list() == _surface()["cell_longitude"].to_list()
