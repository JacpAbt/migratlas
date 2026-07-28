"""Dark Ecology adapter. Column mapping is where a silent ingest bug would live."""

from datetime import date
from pathlib import Path

import polars as pl
import pytest

from migratlas.catalog.loader import get
from migratlas.evidence import EvidenceType, Realm, TaxonScope, spec_for
from migratlas.ingest import darkecology, zenodo

# Rows copied verbatim from the published station file, over-length lines included: a
# reformatted fixture would stop being a faithful test of the real parser input.
STATIONS_CSV = """callsign,ncdcid,wban,name,country,st,county,lat,lon,elev,utc,stntype,tz
KABR,30001794,14929,ABERDEEN,UNITED STATES,SD,BROWN,45.455833,-98.413333,1383,-6,NEXRAD,America/Chicago
KBGM,30001830,4725,BINGHAMTON,UNITED STATES,NY,TIOGA,42.19972,-75.98472,1606,-5,NEXRAD,America/New_York
KBAD,,,NO COORDS,UNITED STATES,LA,,,,,,,
"""  # noqa: E501


def _stations(tmp_path: Path) -> dict[str, darkecology.Station]:
    path = tmp_path / "nexrad-stations.csv"
    path.write_text(STATIONS_CSV, encoding="utf-8")
    return darkecology.load_stations(path)


def _daily() -> pl.DataFrame:
    """Two nights at KBGM plus one row for a station we have no coordinates for."""
    return pl.DataFrame(
        {
            "station": ["KBGM", "KBGM", "KUNKNOWN"],
            # datetime.date, not pl.date -- the latter builds an expression, which lands
            # in the frame as Object dtype and fails to cast.
            "date": [date(2019, 5, 15), date(2019, 9, 20), date(2019, 5, 15)],
            "period": ["night", "night", "night"],
            "period_length": [9.5, 11.0, 9.5],
            "fraction_missing": [0.0, 0.25, 0.0],
            "traffic": [1000.0, 5000.0, 7.0],
            "traffic_unfiltered": [1200.0, 5200.0, 8.0],
            "u": [1.0, -2.0, 0.0],
            "v": [3.0, -4.0, 0.0],
            "direction": [20.0, 200.0, 0.0],
            "speed": [8.0, 9.0, 0.0],
        }
    ).with_columns(pl.col("date").cast(pl.Date))


def test_load_stations_parses_coordinates(tmp_path: Path) -> None:
    stations = _stations(tmp_path)
    assert stations["KBGM"].latitude == pytest.approx(42.19972)
    assert stations["KBGM"].longitude == pytest.approx(-75.98472)


def test_load_stations_skips_rows_without_coordinates(tmp_path: Path) -> None:
    """A blank lat/lon must not become 0,0 -- that is in the Gulf of Guinea."""
    assert "KBAD" not in _stations(tmp_path)
    assert len(_stations(tmp_path)) == 2


def test_to_evidence_conforms_to_the_flux_spec(tmp_path: Path) -> None:
    table = darkecology.to_evidence(_daily(), _stations(tmp_path))
    spec_for(EvidenceType.FLUX).validate(table)


def test_to_evidence_emits_one_row_per_quantity(tmp_path: Path) -> None:
    """Both filtered and unfiltered are kept: comparing them is the rain sensitivity test."""
    table = darkecology.to_evidence(_daily(), _stations(tmp_path))
    quantities = table.column("quantity").to_pylist()
    assert sorted(set(quantities)) == [
        "reflectivity_traffic",
        "reflectivity_traffic_unfiltered",
    ]
    # Two KBGM nights x two quantities. The unplaceable station is gone.
    assert table.num_rows == 4


def test_to_evidence_drops_stations_without_coordinates(tmp_path: Path) -> None:
    table = darkecology.to_evidence(_daily(), _stations(tmp_path))
    assert set(table.column("station_id").to_pylist()) == {"KBGM"}


def test_to_evidence_marks_the_signal_unattributed(tmp_path: Path) -> None:
    """Radar measures aerial biomass. Claiming a taxon would be inventing an attribution."""
    table = darkecology.to_evidence(_daily(), _stations(tmp_path))
    assert set(table.column("taxon_scope").to_pylist()) == {TaxonScope.UNATTRIBUTED.value}
    assert table.column("taxon_key").null_count == table.num_rows
    assert set(table.column("realm").to_pylist()) == {Realm.AERIAL.value}


def test_coverage_fraction_is_the_complement_of_fraction_missing(tmp_path: Path) -> None:
    table = darkecology.to_evidence(_daily(), _stations(tmp_path))
    frame = pl.from_arrow(table)
    assert isinstance(frame, pl.DataFrame)
    by_date = dict(
        zip(
            frame["timestamp"].dt.date().cast(pl.String),
            frame["coverage_fraction"],
            strict=True,
        )
    )
    assert by_date["2019-05-15"] == pytest.approx(1.0)
    assert by_date["2019-09-20"] == pytest.approx(0.75)


def test_integration_hours_carries_period_length(tmp_path: Path) -> None:
    """A nightly total is uninterpretable without knowing how long the night was."""
    table = darkecology.to_evidence(_daily(), _stations(tmp_path))
    assert sorted(set(table.column("integration_hours").to_pylist())) == [9.5, 11.0]


def test_height_is_null_because_the_product_is_vertically_integrated(tmp_path: Path) -> None:
    table = darkecology.to_evidence(_daily(), _stations(tmp_path))
    assert table.column("height_min_m").null_count == table.num_rows
    assert table.column("height_max_m").null_count == table.num_rows


def test_instrument_generation_is_left_null(tmp_path: Path) -> None:
    """The daily product does not label hardware, and the dual-polarisation break must be
    established from upgrade dates rather than guessed at ingest."""
    table = darkecology.to_evidence(_daily(), _stations(tmp_path))
    assert table.column("instrument_generation").null_count == table.num_rows


def test_rows_with_no_measurement_are_dropped(tmp_path: Path) -> None:
    daily = _daily().with_columns(
        traffic=pl.Series([None, 5000.0, 7.0], dtype=pl.Float64),
        traffic_unfiltered=pl.Series([None, 5200.0, 8.0], dtype=pl.Float64),
    )
    table = darkecology.to_evidence(daily, _stations(tmp_path))
    assert table.num_rows == 2
    assert table.column("magnitude").null_count == 0


# --- Live source, opt-in -----------------------------------------------------
@pytest.mark.network
def test_pinned_zenodo_record_still_matches_the_registry() -> None:
    """Catches the upstream publishing a new version under the same record id."""
    record = zenodo.record(darkecology.RECORD_ID)
    assert record.version_doi == get(darkecology.SOURCE_ID).doi
    assert darkecology.DAILY_ARCHIVE in record.files
    assert record.files[darkecology.DAILY_ARCHIVE].checksum
