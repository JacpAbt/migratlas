"""The Movebank ingest, and the things about it that are refusals.

No network. Every test drives the parsing and screening path with a literal CSV, because what is
worth pinning is what the ingest *refuses*, and a refusal is easiest to trust when the input that
triggers it is visible in the test.
"""

import polars as pl
import pytest

from migratlas.evidence import EvidenceType, spec_for
from migratlas.ingest import movebank
from migratlas.redact import IngestRefusedError, admit_taxon_for_ingest

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
# deployed locations. 618,915 of the positioned rows carry `visible = false`, which is the owners'
# own outlier flag. The first run landed 607,135 rows, 89% of them positions somebody had already
# marked as wrong, and nothing failed -- the count only looked wrong beside the published one.
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


# --- Coordinates -------------------------------------------------------------
#
# From real rows, and the detectability grid encoder is what noticed: it decodes a cell index back
# to a longitude and returned -223.5.
def test_a_longitude_past_the_antimeridian_is_wrapped_into_range() -> None:
    """Two Bylot fox fixes arrive at -207 and -223 degrees, which are not coordinates."""
    frame = movebank.parse(
        _csv(
            _row("A", "2010-06-01 12:00:00.000", "83.4", "-207.342167", "Vulpes lagopus"),
            _row("A", "2011-06-01 12:00:00.000", "71.0", "-223.353917", "Vulpes lagopus"),
        )
    )
    assert all(-180 <= value <= 180 for value in frame["location_long"].to_list())
    assert frame["location_long"].to_list() == pytest.approx([152.657833, 136.646083])


def test_a_bench_test_before_deployment_is_removed() -> None:
    """The 617 Berlin rows. Five collars tested at the manufacturer under the same animal id as the
    real Missouri track, carrying a deployment and marked visible, so nothing else here rejects
    them.

    Berlin to St Louis is 7,150 km across 27.0 days -- 265 km/day, against a bison ceiling of 80.
    """
    frame = movebank.parse(
        _csv(
            # Five days on a bench in Berlin.
            *[
                _row("Patti_PSP", f"2022-08-2{day} 15:00:00.000", "52.43", "13.52", "Bison bison")
                for day in range(6, 10)
            ],
            # Then a month of standing in a Missouri field.
            *[
                _row(
                    "Patti_PSP",
                    f"2022-09-{day:02d} 15:00:00.000",
                    "38.63",
                    "-90.23",
                    "Bison bison",
                )
                for day in range(27, 31)
            ],
            *[
                _row(
                    "Patti_PSP",
                    f"2022-10-{day:02d} 15:00:00.000",
                    "38.63",
                    "-90.23",
                    "Bison bison",
                )
                for day in range(1, 10)
            ],
        )
    )
    kept = movebank.unreachable(frame)
    assert kept.height == 13, "the Missouri record survives"
    assert not kept.filter(pl.col("location_long") > 0).height, "Berlin is gone"


def test_a_connected_dispersal_survives_however_far_it_goes() -> None:
    """Arctic fox MMRV: 3,000 km westward to the Mackenzie Delta, and the reason two earlier filters
    were reverted. Its fastest real step is 127.9 km/day against a ceiling of 160.

    Every fix here is 100 km further west than the last, one day apart -- so the *whole animal* is a
    long way from where it started and no single step is impossible. A rule that measured distance
    from the animal's median rather than across consecutive fixes deleted 112 of these.
    """
    frame = movebank.parse(
        _csv(
            *[
                _row(
                    "MMRV",
                    f"2013-04-{day:02d} 16:00:00.000",
                    "73.0",
                    f"{-80.0 - 3.0 * day:.4f}",
                    "Vulpes lagopus",
                )
                for day in range(1, 20)
            ]
        )
    )
    kept = movebank.unreachable(frame)
    assert kept.height == frame.height, "a connected track is one segment, however long"
    assert kept["location_long"].min() == pytest.approx(-137.0)


def test_one_bad_position_is_dropped_and_the_track_either_side_is_not() -> None:
    """The regression that made the first version of this wrong.

    Bylot fox `OBBB` has 107,229 fixes and a real four-day stretch of 1,176 of them had one bad
    position on each side. Judged by *share* of the animal's record, that stretch was 1.1% and was
    deleted -- 1,176 rows of an animal that never left the study area. Size alone cannot tell a
    displaced stay from a real one that was merely cut off, which is why `MAX_STRAY_KM` exists.
    """
    ordinary = [
        _row("OBBB", f"2019-06-{day:02d} 12:00:00.000", "72.88", "-79.95", "Vulpes lagopus")
        for day in range(1, 10)
    ]
    frame = movebank.parse(
        _csv(
            *ordinary[:4],
            # One Argos position 400 km out, then straight back.
            _row("OBBB", "2019-06-05 06:00:00.000", "76.5", "-79.95", "Vulpes lagopus"),
            *ordinary[4:],
        )
    )
    kept = movebank.unreachable(frame)
    assert kept.height == len(ordinary), "only the bad position goes"
    assert kept["location_lat"].max() == pytest.approx(72.88)


def test_scatter_across_a_rounded_away_gap_is_not_a_break() -> None:
    """Timestamps here are minute-resolution and some pairs share one, so implied speed alone is
    unusable: an elk pair 18.2 km apart with no measurable gap reads as 82,694 km/day, and the bison
    study's 99th percentile is 1,028. `MIN_JUMP_KM` is the floor that makes the speed mean
    something.
    """
    frame = movebank.parse(
        _csv(
            _row("A", "2021-10-02 11:00:00.000", "51.700", "-115.400", "Cervus elaphus"),
            # 200 m in the same minute: 344 km/day implied, and nothing at all in truth.
            _row("A", "2021-10-02 11:00:00.000", "51.7018", "-115.400", "Cervus elaphus"),
            _row("A", "2021-10-02 12:00:00.000", "51.702", "-115.401", "Cervus elaphus"),
            _row("A", "2021-10-03 12:00:00.000", "51.703", "-115.402", "Cervus elaphus"),
            _row("A", "2021-10-04 12:00:00.000", "51.704", "-115.403", "Cervus elaphus"),
            _row("A", "2021-10-05 12:00:00.000", "51.705", "-115.404", "Cervus elaphus"),
            _row("A", "2021-10-06 12:00:00.000", "51.706", "-115.405", "Cervus elaphus"),
            _row("A", "2021-10-07 12:00:00.000", "51.707", "-115.406", "Cervus elaphus"),
            _row("A", "2021-10-08 12:00:00.000", "51.708", "-115.407", "Cervus elaphus"),
        )
    )
    assert movebank.unreachable(frame).height == frame.height


def test_an_animal_with_one_location_keeps_it() -> None:
    """Five caribou in the South Peace study have exactly one location each.

    A lone fix is the textbook bad position -- unreachable from the neighbour on either side -- but
    only when it *has* neighbours. Judged on size alone these five were dropped as spikes, and the
    withheld caribou page went from 260 animals to 255 before the page diff showed it.
    """
    frame = movebank.parse(
        _csv(
            _row("HR_151.535", "1991-10-25 12:00:00.000", "53.83", "-121.56", "Rangifer tarandus"),
            _row("KE_car018", "1992-03-11 12:00:00.000", "54.90", "-121.30", "Rangifer tarandus"),
        )
    )
    kept = movebank.unreachable(frame)
    assert kept.height == 2
    assert sorted(kept["individual_local_identifier"].to_list()) == ["HR_151.535", "KE_car018"]


def test_every_registered_study_species_has_its_own_ceiling() -> None:
    """`DEFAULT_KM_PER_DAY` is a fallback for a taxon nobody has thought about, not a place for the
    seven studies actually registered. A new study lands here before it lands in the lake."""
    missing = [
        study.species for study in movebank.STUDIES if study.species not in movebank.MAX_KM_PER_DAY
    ]
    assert not missing, f"no implied-speed ceiling for {sorted(set(missing))}"


def test_an_empty_frame_survives_the_reachability_filter() -> None:
    """Reachable: a study whose every row is a flagged outlier parses to nothing."""
    assert movebank.unreachable(movebank.parse(_csv())).height == 0


def test_a_row_with_no_taxon_never_reaches_the_lake() -> None:
    """13,966 fixes were in the lake with no species recorded, because `screen_taxa` dropped nulls
    before the floor saw them: the gate was asked about every taxon except the rows that had none.

    Dropped rather than fatal, and the asymmetry is deliberate. A *human* row means the taxon field
    is not what the ingest assumes and a person has to look; a blank one means somebody did not type
    a species. Refusing the study over eight animals would lose 2.5 million good fixes.
    """
    frame = movebank.parse(
        _csv(
            _row("A", "2015-06-01 12:00:00.000", "51.7", "-115.6", "Cervus elaphus"),
            _row("A", "2016-06-01 12:00:00.000", "51.7", "-115.6", "Cervus elaphus"),
            'YL227,2022-06-01 12:00:00.000,51.7,-115.5,,"GPS",dep1,true',
        )
    )
    assert frame.height == 3, "parsing keeps it; only the floor decides"

    kept = movebank.named("movebank_yahatinda_elk", frame)
    assert kept.height == 2
    assert "YL227" not in kept["individual_local_identifier"].to_list()


def test_the_floor_refuses_a_taxon_it_was_not_told() -> None:
    """A gate that answers "fine" when it has not been told what it is looking at is not a gate."""
    with pytest.raises(IngestRefusedError, match="neither a taxon key nor"):
        admit_taxon_for_ingest("movebank_yahatinda_elk")
    with pytest.raises(IngestRefusedError, match="neither a taxon key nor"):
        admit_taxon_for_ingest("movebank_yahatinda_elk", scientific_name="   ")
