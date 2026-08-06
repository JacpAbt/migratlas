"""The Swedish Bird Survey ingest, and the redaction it has to work around.

No network. Every test drives the parsing path with literal Darwin Core tables, because what is
worth pinning is what the adapter refuses and what it derives, and both are easiest to trust when
the input that triggers them is visible.
"""

from pathlib import Path

import polars as pl
import pytest

from migratlas.evidence import EvidenceType, spec_for
from migratlas.ingest import sbs
from migratlas.redact import IngestRefusedError

EVENT_HEADER = (
    "eventID\teventDate\teventTime\tsamplingProtocol\tlocality\tdecimalLatitude\tdecimalLongitude"
)
OCCURRENCE_HEADER = "eventID\tscientificName\tindividualCount\trecordedBy\toccurrenceStatus"

POINTS = sbs.BY_SOURCE["sbs_point_counts"]


def _event(  # noqa: PLR0913 -- a Darwin Core event row has as many columns as it has
    event_id: str,
    *,
    date: str = "1996-05-23",
    time: str = "04:00/09:30",
    protocol: str = "point transect survey",
    site: str = "SFTpkt:siteId:500",
    lat: str = "55.789",
    lon: str = "13.215",
) -> str:
    return f"{event_id}\t{date}/{date}\t{time}\t{protocol}\t{site}\t{lat}\t{lon}"


def _record(
    event_id: str,
    name: str,
    count: str = "3",
    recorder: str = "SFT:recorderId:835",
    status: str = "present",
) -> str:
    return f"{event_id}\t{name}\t{count}\t{recorder}\t{status}"


def _write(tmp_path: Path, events: list[str], records: list[str]) -> tuple[Path, Path]:
    event = tmp_path / "event.txt"
    occurrence = tmp_path / "occurrence.txt"
    event.write_text("\n".join([EVENT_HEADER, *events]) + "\n", encoding="utf-8")
    occurrence.write_text("\n".join([OCCURRENCE_HEADER, *records]) + "\n", encoding="utf-8")
    return event, occurrence


def test_a_visit_joins_to_its_event_and_carries_the_effort(tmp_path: Path) -> None:
    """The whole reason a sampling-event archive is worth more than an occurrence one.

    Effort is a column of the event table, so it is measured rather than inferred, and it reaches
    every species row belonging to that visit.
    """
    event, occurrence = _write(
        tmp_path,
        [_event("E1", time="04:00/09:30")],
        [_record("E1", "Turdus merula"), _record("E1", "Fringilla coelebs")],
    )
    frame = sbs.read_visits(POINTS, event, occurrence)

    assert frame.height == 2
    assert frame["hours"].to_list() == [pytest.approx(5.5), pytest.approx(5.5)]
    assert frame["locality"].unique().to_list() == ["SFTpkt:siteId:500"]


def test_a_withheld_species_is_dropped_by_name(tmp_path: Path) -> None:
    """The publisher removes every taxon at Swedish security class 4 or higher, so those species are
    absent from *every* event in the archive.

    An occupancy model derives absence from "surveyed and not recorded", which for a withheld
    species is true everywhere -- it would read a national redaction as a national extinction. If
    one ever appears in the data the redaction has changed, and this is where that is noticed.
    """
    event, occurrence = _write(
        tmp_path,
        [_event("E1")],
        [
            _record("E1", "Turdus merula"),
            _record("E1", "Haliaeetus albicilla"),
            _record("E1", "Canis lupus"),
        ],
    )
    frame = sbs.read_visits(POINTS, event, occurrence)

    assert frame["scientificName"].to_list() == ["Turdus merula"]
    assert "Haliaeetus albicilla" in sbs.WITHHELD
    assert "Lynx lynx" in sbs.WITHHELD, "the fixed routes record mammals and withhold five of them"


def test_an_absent_record_is_not_counted_as_a_sighting(tmp_path: Path) -> None:
    """Every row in both archives is `present` today. A future `absent` is real information and
    must not be summed into a count as though the bird had been seen."""
    event, occurrence = _write(
        tmp_path,
        [_event("E1")],
        [_record("E1", "Turdus merula"), _record("E1", "Parus major", status="absent")],
    )
    assert sbs.read_visits(POINTS, event, occurrence)["scientificName"].to_list() == [
        "Turdus merula"
    ]


def test_a_survey_window_that_makes_no_sense_yields_no_effort(tmp_path: Path) -> None:
    """Null rather than zero or a wrapped negative: the schema allows an absent effort, and a zero
    divides into infinity somewhere downstream. These are all dawn surveys, so a window that ends
    before it starts means something other than midnight."""
    event, occurrence = _write(
        tmp_path,
        [_event("E1", time="09:30/04:00"), _event("E2", time="")],
        [_record("E1", "Turdus merula"), _record("E2", "Turdus merula")],
    )
    frame = sbs.read_visits(POINTS, event, occurrence)
    assert frame["hours"].to_list() == [None, None]


def test_a_row_with_no_event_is_dropped_rather_than_carrying_a_null_site(tmp_path: Path) -> None:
    """An inner join, deliberately. `site_id` and the coordinates are not nullable in the schema,
    so an occurrence whose event is missing cannot be written and must not be half-written."""
    event, occurrence = _write(
        tmp_path,
        [_event("E1")],
        [_record("E1", "Turdus merula"), _record("E404", "Parus major")],
    )
    assert sbs.read_visits(POINTS, event, occurrence).height == 1


def test_the_floor_screens_every_taxon_present(tmp_path: Path) -> None:
    """The same gate the Movebank studies pass. A human row in a bird scheme means the taxon field
    is not what the ingest assumes, and everything downstream of that needs a person."""
    event, occurrence = _write(
        tmp_path,
        [_event("E1")],
        [_record("E1", "Turdus merula"), _record("E1", "Homo sapiens")],
    )
    frame = sbs.read_visits(POINTS, event, occurrence)
    with pytest.raises(IngestRefusedError):
        sbs.screen_taxa("sbs_point_counts", frame)


def test_the_adapter_emits_the_canonical_survey_index_schema(tmp_path: Path) -> None:
    """And the observer travels with the protocol, as it does for BBS: observer skill is the best
    documented bias in a scheme like this, and a trend fit needs it as a break term."""
    event, occurrence = _write(tmp_path, [_event("E1")], [_record("E1", "Turdus merula")])
    frame = sbs.read_visits(POINTS, event, occurrence)
    table = sbs.to_evidence(POINTS, frame, {"Turdus merula": 2490719})

    assert table.schema.equals(spec_for(EvidenceType.SURVEY_INDEX).schema)
    row = pl.DataFrame(pl.from_arrow(table)).row(0, named=True)
    assert row["source_id"] == "sbs_point_counts"
    assert row["realm"] == "terrestrial"
    assert row["taxon_key"] == 2490719
    assert row["effort"] == pytest.approx(5.5)
    assert row["effort_unit"] == "survey hours"
    assert "SFT:recorderId:835" in row["protocol"]
    assert "point transect survey" in row["protocol"]


def test_an_unresolved_name_lands_as_a_null_key_not_a_wrong_one(tmp_path: Path) -> None:
    event, occurrence = _write(tmp_path, [_event("E1")], [_record("E1", "Turdus merula")])
    frame = sbs.read_visits(POINTS, event, occurrence)
    table = sbs.to_evidence(POINTS, frame, {})
    assert pl.DataFrame(pl.from_arrow(table)).row(0, named=True)["taxon_key"] is None


def test_both_schemes_are_registered_and_distinct() -> None:
    """Two protocols, two DOIs, two spans, so two sources -- the same rule that made seven Movebank
    studies seven sources rather than one."""
    assert {scheme.source_id for scheme in sbs.SCHEMES} == {
        "sbs_point_counts",
        "sbs_fixed_routes",
    }
    assert len({scheme.protocol for scheme in sbs.SCHEMES}) == 2


def test_a_cross_kingdom_homonym_is_asked_for_by_its_authority() -> None:
    """The European greenfinch resolves to nothing as written.

    *Chloris* is also a grass genus, so the Backbone answers `matchType: NONE` with "Multiple equal
    matches for Chloris chloris" and the resolver rightly refuses rather than guessing a kingdom.
    Appending the authority disambiguates it to the accepted Aves key.

    The general fault is in `taxonomy/gbif.py`, which sends no kingdom hint, so any animal sharing a
    binomial with a plant fails identically. This table is the contained fix for the one name that
    actually occurs here.
    """
    assert sbs.SYNONYMS["Chloris chloris"] == "Chloris chloris (Linnaeus, 1758)"
