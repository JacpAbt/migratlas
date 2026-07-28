import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl

from migratlas.evidence import EvidenceType, Realm, TaxonScope
from migratlas.redact import PublicationClearance, Sensitivity, clear_for_publication
from migratlas.tiles.station_series import WEEKS, export_station_series, weekly_climatology


def nights(  # noqa: PLR0913 -- a fixture builder, and every knob is used by some test
    station: str = "KBGM",
    *,
    years: range = range(1995, 2026),
    amplitude: float = 100.0,
    growth: float = 0.0,
    lon: float = -75.98,
    lat: float = 42.2,
) -> pl.DataFrame:
    """A station with a May peak, one value per week per year."""
    rows = []
    for year in years:
        scale = 1.0 + growth * (year - min(years))
        for week in range(WEEKS):
            # Ordinal day at the start of the week, so week indices land where intended.
            day = datetime(year, 1, 1, tzinfo=UTC) + timedelta(days=week * 7)
            peakness = 1.0 if 17 <= week <= 21 else 0.1
            rows.append(
                {
                    "station_id": station,
                    "timestamp": day,
                    "magnitude": amplitude * peakness * scale,
                    "station_longitude": lon,
                    "station_latitude": lat,
                }
            )
    return pl.DataFrame(rows)


def clearance(sensitivity: Sensitivity = Sensitivity.NOT_SENSITIVE) -> PublicationClearance:
    return clear_for_publication(
        source_id="darkecology_daily",
        evidence_type=EvidenceType.FLUX,
        realm=Realm.AERIAL,
        sensitivity=sensitivity,
        taxon_scope=TaxonScope.UNATTRIBUTED,
        taxon_key=None,
    )


def test_climatology_has_one_row_per_station_week() -> None:
    frame = weekly_climatology(nights())
    assert frame.height == WEEKS
    assert sorted(frame["week"].to_list()) == list(range(WEEKS))


def test_climatology_finds_the_seasonal_peak() -> None:
    frame = weekly_climatology(nights()).sort("median", descending=True)
    assert 17 <= frame["week"][0] <= 21


def test_climatology_counts_the_years_behind_each_week() -> None:
    frame = weekly_climatology(nights(years=range(2000, 2020)))
    assert frame["years"].unique().to_list() == [20]


def test_export_writes_one_feature_per_station(tmp_path: Path) -> None:
    frame = pl.concat([nights("KBGM"), nights("KDOX", lon=-75.44, lat=38.83)])
    result = export_station_series(frame, clearance(), tmp_path / "aerial.geojson")

    assert result.stations == 2
    assert result.features == result.stations
    payload = json.loads((tmp_path / "aerial.geojson").read_text(encoding="utf-8"))
    assert {f["properties"]["station"] for f in payload["features"]} == {"KBGM", "KDOX"}
    for feature in payload["features"]:
        # The whole animation depends on this being a fixed-length array MapLibre can index.
        assert len(feature["properties"]["weeks"]) == WEEKS


def test_missing_weeks_are_null_not_zero(tmp_path: Path) -> None:
    """A gap in coverage must not read as "no animals passed"."""
    frame = nights().filter(pl.col("timestamp").dt.ordinal_day() > 40)
    export_station_series(frame, clearance(), tmp_path / "aerial.geojson")
    weeks = json.loads((tmp_path / "aerial.geojson").read_text(encoding="utf-8"))["features"][0][
        "properties"
    ]["weeks"]
    assert weeks[0] is None
    assert weeks[20] is not None


def coordinates(path: Path) -> list[float]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    coords: list[float] = payload["features"][0]["geometry"]["coordinates"]
    return coords


def test_not_sensitive_sites_keep_their_coordinates(tmp_path: Path) -> None:
    """Radar sites are published infrastructure; snapping them would be noise, not safety."""
    export_station_series(nights(), clearance(), tmp_path / "aerial.geojson")
    assert coordinates(tmp_path / "aerial.geojson") == [-75.98, 42.2]


def test_sensitive_sites_are_snapped_to_the_clearance_grid(tmp_path: Path) -> None:
    """The exporter is generic: a FLUX instrument at a sensitive site must be generalised."""
    export_station_series(nights(), clearance(Sensitivity.MODERATE), tmp_path / "aerial.geojson")
    # MODERATE aggregate policy is a 0.5 degree grid, reported at cell centre.
    assert coordinates(tmp_path / "aerial.geojson") == [-75.75, 42.25]


def test_annotations_land_on_the_features(tmp_path: Path) -> None:
    """A trend reaches the globe only from a caller that computed it, never from here."""
    annotations = pl.DataFrame({"station_id": ["KBGM"], "autumn_shift_days_per_decade": [-0.46]})
    export_station_series(
        nights(), clearance(), tmp_path / "aerial.geojson", annotations=annotations
    )
    payload = json.loads((tmp_path / "aerial.geojson").read_text(encoding="utf-8"))
    assert payload["features"][0]["properties"]["autumn_shift_days_per_decade"] == -0.46


def test_a_station_missing_from_the_annotations_still_publishes(tmp_path: Path) -> None:
    """A station that failed the trend thresholds keeps its seasonal cycle."""
    frame = pl.concat([nights("KBGM"), nights("KDOX", lon=-75.44, lat=38.83)])
    annotations = pl.DataFrame({"station_id": ["KBGM"], "autumn_shift_days_per_decade": [-0.46]})
    result = export_station_series(
        frame, clearance(), tmp_path / "aerial.geojson", annotations=annotations
    )
    assert result.stations == 2
    payload = json.loads((tmp_path / "aerial.geojson").read_text(encoding="utf-8"))
    shifts = {
        f["properties"]["station"]: f["properties"]["autumn_shift_days_per_decade"]
        for f in payload["features"]
    }
    assert shifts == {"KBGM": -0.46, "KDOX": None}


def test_the_metadata_names_the_annotations_it_published(tmp_path: Path) -> None:
    annotations = pl.DataFrame({"station_id": ["KBGM"], "autumn_shift_days_per_decade": [-0.46]})
    export_station_series(
        nights(), clearance(), tmp_path / "aerial.geojson", annotations=annotations
    )
    meta = json.loads((tmp_path / "aerial.meta.json").read_text(encoding="utf-8"))
    assert meta["annotations"] == ["autumn_shift_days_per_decade"]


def test_export_publishes_its_generalisation_statement(tmp_path: Path) -> None:
    result = export_station_series(nights(), clearance(), tmp_path / "aerial.geojson")
    meta = json.loads((tmp_path / "aerial.meta.json").read_text(encoding="utf-8"))
    assert meta["dwc:dataGeneralizations"] == result.generalization
    assert meta["stations"] == 1
    assert "Not a nightly series" in meta["reduction"]


def test_delay_window_withholds_recent_nights(tmp_path: Path) -> None:
    """The clearance governs recency even where the coordinates themselves are public."""
    frame = nights(years=range(2010, 2027))
    # HIGH aggregate policy withholds the last 30 days, so week 0 of 2026 must not appear
    # while week 0 of earlier years must.
    export_station_series(
        frame,
        clearance(Sensitivity.HIGH),
        tmp_path / "delayed.geojson",
        now=datetime(2026, 1, 20, tzinfo=UTC),
    )
    export_station_series(
        frame, clearance(), tmp_path / "open.geojson", now=datetime(2026, 1, 20, tzinfo=UTC)
    )

    delayed = json.loads((tmp_path / "delayed.geojson").read_text(encoding="utf-8"))
    openly = json.loads((tmp_path / "open.geojson").read_text(encoding="utf-8"))
    assert delayed["features"][0]["properties"]["years"] == 16
    assert openly["features"][0]["properties"]["years"] == 17
