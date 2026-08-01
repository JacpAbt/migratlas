"""The Movebank ingest, and the things about it that are refusals.

No network. Every test drives the parsing and screening path with a literal CSV, because what is
worth pinning is what the ingest *refuses*, and a refusal is easiest to trust when the input that
triggers it is visible in the test.
"""

import pytest

from migratlas.evidence import EvidenceType, spec_for
from migratlas.ingest import movebank
from migratlas.redact import IngestRefusedError

HEADER = (
    "individual_local_identifier,timestamp,location_lat,location_long,"
    "individual_taxon_canonical_name,sensor_type_id,deployment_id,visible"
)


def _row(  # noqa: PLR0913 -- a CSV row has as many columns as it has
    individual: str,
    timestamp: str,
    lat: str,
    lon: str,
    taxon: str,
    *,
    sensor: str = "GPS",
    deployment: str = "dep1",
    visible: str = "true",
) -> str:
    """One event row. Deployed and visible by default, since that is the ordinary case."""
    return f'"{individual}",{timestamp},{lat},{lon},"{taxon}","{sensor}",{deployment},{visible}'


def _csv(*rows: str) -> str:
    return "\n".join([HEADER, *rows]) + "\n"


ELK = movebank.BY_SOURCE["movebank_yahatinda_elk"]


def test_every_registered_study_has_a_source_and_a_unique_id() -> None:
    """The study id is the identifier, so two sources pointing at one study would double-count."""
    ids = [study.study_id for study in movebank.STUDIES]
    assert len(ids) == len(set(ids))
    assert len(movebank.BY_SOURCE) == len(movebank.STUDIES)


def test_the_request_asks_for_deployment_and_visibility() -> None:
    """Asserted on the constant, because omitting either is silent rather than an error.

    The endpoint answers 200 with a perfectly well-formed CSV either way. The only signal that the
    wrong thing was asked for is the row count, and only if someone compares it to the study's
    published one.
    """
    assert "deployment_id" in movebank.ATTRIBUTES
    assert "visible" in movebank.ATTRIBUTES


# --- Parsing -----------------------------------------------------------------
def test_rows_without_a_position_are_dropped_not_failed() -> None:
    """A transmission can carry a sensor reading and no fix. Normal in this feed, not an error."""
    frame = movebank.parse(
        _csv(
            _row("A", "2010-06-01 12:00:00.000", "51.5", "-115.4", "Cervus elaphus"),
            _row("A", "2010-06-02 12:00:00.000", "", "", "Cervus elaphus"),
            _row("B", "2011-06-01 12:00:00.000", "51.6", "-115.3", "Cervus elaphus"),
        )
    )
    assert frame.height == 2


def test_an_unparseable_timestamp_does_not_become_a_null_row() -> None:
    """`strict=False` turns a bad timestamp into null, and a null timestamp in a phenology source is
    worse than a missing row: it would be counted and then silently excluded downstream."""
    frame = movebank.parse(
        _csv(
            _row("A", "2010-06-01 12:00:00.000", "51.5", "-115.4", "Cervus elaphus"),
            _row("A", "not-a-date", "51.5", "-115.4", "Cervus elaphus"),
        )
    )
    assert frame.height == 1
    assert frame["timestamp"].null_count() == 0


# --- Deployed and visible ----------------------------------------------------
#
# The correctness bug this ingest actually had. The event endpoint returns every fix a tag ever
# transmitted: for the Bylot Argos study, 696,640 rows against the 64,489 its metadata calls
# deployed locations. 618,915 of the positioned rows carry `visible = false`, the data owners' own
# outlier flag. The first run landed 607,135 rows, 89% of them positions somebody had already marked
# as wrong, and nothing failed -- the count only looked wrong beside the published one.
def test_fixes_the_owners_flagged_as_outliers_are_dropped() -> None:
    frame = movebank.parse(
        _csv(
            _row("A", "2010-06-01 12:00:00.000", "51.5", "-115.4", "Cervus elaphus"),
            _row("A", "2011-06-02 12:00:00.000", "0.0", "0.0", "Cervus elaphus", visible="false"),
        )
    )
    assert frame.height == 1
    assert frame["location_lat"].to_list() == [51.5]


def test_fixes_from_outside_a_deployment_are_dropped() -> None:
    """A tag transmits before it is fitted, after it comes off, and while it sits in a lab."""
    frame = movebank.parse(
        _csv(
            _row("A", "2010-06-01 12:00:00.000", "51.5", "-115.4", "Cervus elaphus"),
            _row("A", "2011-06-02 12:00:00.000", "51.5", "-115.4", "Cervus elaphus", deployment=""),
        )
    )
    assert frame.height == 1


def test_both_filters_are_needed_not_either() -> None:
    """On the real study, `deployment_id` alone leaves 607,135 rows and `visible` alone leaves
    75,188. Only both together reproduce the published 64,489."""
    frame = movebank.parse(
        _csv(
            _row("A", "2010-06-01 12:00:00.000", "51.5", "-115.4", "Cervus elaphus"),
            _row(
                "B", "2011-06-01 12:00:00.000", "51.5", "-115.4", "Cervus elaphus", visible="false"
            ),
            _row("C", "2012-06-01 12:00:00.000", "51.5", "-115.4", "Cervus elaphus", deployment=""),
            _row(
                "D",
                "2013-06-01 12:00:00.000",
                "51.5",
                "-115.4",
                "Cervus elaphus",
                deployment="",
                visible="false",
            ),
        )
    )
    assert frame.height == 1
    assert frame["individual_local_identifier"].to_list() == ["A"]


# --- The never-ingested floor ------------------------------------------------
def test_a_human_row_stops_the_ingest_rather_than_being_filtered() -> None:
    """The pre-registered stop condition.

    Filtering would be the tempting fix and the wrong one: a human row inside a mammal study means
    the taxon field is not what the ingest assumes it is, and everything downstream of that
    assumption needs re-checking by a person rather than routing around it.
    """
    frame = movebank.parse(
        _csv(
            _row("A", "2010-06-01 12:00:00.000", "51.5", "-115.4", "Cervus elaphus"),
            _row("H", "2011-06-01 12:00:00.000", "51.5", "-115.4", "Homo sapiens"),
        )
    )
    with pytest.raises(IngestRefusedError, match="never enters this lake"):
        movebank.screen_taxa("movebank_yahatinda_elk", frame)


def test_the_floor_screens_every_taxon_present_not_the_advertised_one() -> None:
    """Movebank's human rows sit inside multi-taxon animal studies.

    "Poultry network Thailand 2022" lists fourteen taxa -- a turtle, six raptors, waterfowl,
    `Canis lupus` and `Homo sapiens`. A check against the study's headline species would pass it.
    """
    frame = movebank.parse(
        _csv(
            _row("A", "2010-06-01 12:00:00.000", "51.5", "-115.4", "Milvus migrans"),
            _row("B", "2011-06-02 12:00:00.000", "51.5", "-115.4", "Varanus salvator"),
            _row("H", "2012-06-03 12:00:00.000", "51.5", "-115.4", "Homo sapiens"),
        )
    )
    with pytest.raises(IngestRefusedError):
        movebank.screen_taxa("movebank_yahatinda_elk", frame)


def test_an_ordinary_study_passes_the_floor_and_reports_its_taxa() -> None:
    frame = movebank.parse(
        _csv(
            _row("A", "2010-06-01 12:00:00.000", "51.5", "-115.4", "Cervus elaphus"),
            _row("B", "2011-06-01 12:00:00.000", "51.6", "-115.3", "Cervus elaphus"),
        )
    )
    assert movebank.screen_taxa("movebank_yahatinda_elk", frame) == ["Cervus elaphus"]


# --- The span rule -----------------------------------------------------------
def test_a_study_shorter_than_the_annual_cycle_is_refused() -> None:
    """`Dolphin_Union_Caribou_UAV` is three days long and holds 450,042 locations -- more than the
    29-year caribou study, because it is an aerial survey rather than tracking. Pooled, it would
    dominate a cell with a single instant, which is the MegaMove failure exactly."""
    frame = movebank.parse(
        _csv(
            _row("A", "2015-11-06 12:00:00.000", "69.1", "-107.0", "Rangifer tarandus"),
            _row("B", "2015-11-08 12:00:00.000", "69.2", "-107.1", "Rangifer tarandus"),
        )
    )
    assert movebank.span_years(frame) < movebank.MIN_STUDY_YEARS


def test_a_study_spanning_two_calendar_years_clears_the_floor() -> None:
    frame = movebank.parse(
        _csv(
            _row("A", "2015-12-31 12:00:00.000", "69.1", "-107.0", "Rangifer tarandus"),
            _row("A", "2016-01-01 12:00:00.000", "69.2", "-107.1", "Rangifer tarandus"),
        )
    )
    assert movebank.span_years(frame) >= movebank.MIN_STUDY_YEARS


def test_an_empty_frame_has_no_span_rather_than_raising() -> None:
    """Reachable: a study whose every row is an outlier parses to nothing."""
    assert movebank.span_years(movebank.parse(_csv())) == 0


# --- The adapter -------------------------------------------------------------
def test_individual_ids_are_namespaced_by_study() -> None:
    """The two Bylot fox studies number their collars from one. Unprefixed, pooling them would
    merge two foxes into one animal and invent a journey neither made."""
    frame = movebank.parse(
        _csv(_row("7", "2010-06-01 12:00:00.000", "51.5", "-115.4", "Cervus elaphus"))
    )
    table = movebank.to_evidence(ELK, frame, {"Cervus elaphus": 2440958})
    assert table.column("individual_id").to_pylist() == [f"{ELK.study_id}:7"]


def test_the_adapter_emits_the_canonical_track_schema() -> None:
    frame = movebank.parse(
        _csv(
            _row("A", "2010-06-01 12:00:00.000", "51.5", "-115.4", "Cervus elaphus"),
            _row("A", "2011-06-01 12:00:00.000", "51.6", "-115.3", "Cervus elaphus"),
        )
    )
    table = movebank.to_evidence(ELK, frame, {"Cervus elaphus": 2440958})
    spec = spec_for(EvidenceType.TRACK)
    spec.validate(table)
    assert table.schema == spec.schema
    assert table.column("taxon_key").to_pylist() == [2440958, 2440958]
    assert table.column("source_id").to_pylist() == [ELK.source_id] * 2
    assert table.column("sensor_type").to_pylist() == ["GPS", "GPS"]


def test_an_unresolved_taxon_lands_as_a_null_key_not_a_wrong_one() -> None:
    """A missing crosswalk entry must not silently borrow another taxon's key.

    The publication gate refuses an EXACT claim with no key, so a null is refused downstream --
    which a borrowed key would not be.
    """
    frame = movebank.parse(
        _csv(_row("A", "2010-06-01 12:00:00.000", "51.5", "-115.4", "Cervus elaphus"))
    )
    table = movebank.to_evidence(ELK, frame, {})
    assert table.column("taxon_key").to_pylist() == [None]


# --- The licence handshake ---------------------------------------------------
def test_a_csv_response_is_recognised_as_data_and_an_html_one_is_not() -> None:
    """The whole handshake turns on telling the two apart, and Movebank signals it with neither a
    status code nor a content type -- both come back 200 text/csv."""
    assert movebank._looks_like_data(HEADER + "\n")
    assert movebank._looks_like_data('"individual_local_identifier",x\n')
    assert not movebank._looks_like_data("<html>\n<p>By accepting this document")
    assert not movebank._looks_like_data("<p>No data are available for download.</p>")
