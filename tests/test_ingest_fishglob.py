"""FISHGLOB adapter. The source Phase 1b's whole result rests on, and it had no test.

The cases here are the ones that cost real time to find in the data: dtypes that vary per
survey for the same column, three surveys that publish no raw catch at all, dates that have
to be built from parts because the timestamp column is free text, and two readers where the
fast one is optional.
"""

from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import pyarrow as pa
import pytest
import rdata

from migratlas.evidence import EvidenceType, Realm, TaxonScope, spec_for
from migratlas.ingest import fishglob


def _haul_rows(**overrides: object) -> pl.DataFrame:
    """One haul with two species, in the shape `prepare` produces."""
    base: dict[str, object] = {
        "survey_unit": ["NEUS-Fall", "NEUS-Fall"],
        "haul_id": ["h1", "h1"],
        "year": [2015, 2015],
        "month": [9, 9],
        "day": [14, 14],
        "latitude": [42.5, 42.5],
        "longitude": [-70.5, -70.5],
        "depth": [90.0, 90.0],
        "num": [12.0, 3.0],
        "area_swept": [0.04, 0.04],
        "gear": ["trawl", "trawl"],
        "accepted_name": ["Gadus morhua", "Ammodytes dubius"],
        "sst": ["14.2", "14.2"],
        "sbt": ["8.1", "8.1"],
        "effort_unit": [fishglob.EFFORT_UNIT] * 2,
    }
    base.update(overrides)
    return pl.DataFrame(base)


KEYS = {"Gadus morhua": 2291432, "Ammodytes dubius": 2413621}


# --- Dates, which are built rather than parsed --------------------------------
def test_a_haul_date_is_built_from_the_numeric_parts() -> None:
    """`timestamp` is free text in inconsistent formats, so it is not used at all."""
    dated = _haul_rows().select(when=fishglob._haul_date())
    assert dated["when"][0] == datetime(2015, 9, 14, tzinfo=UTC)


def test_a_missing_day_becomes_the_first_rather_than_a_null() -> None:
    """Day is null for every European survey. Month precision is enough for an annual metric,
    and recording the real precision beats dropping the haul."""
    dated = _haul_rows(day=[None, None]).select(when=fishglob._haul_date())
    assert dated["when"][0] == datetime(2015, 9, 1, tzinfo=UTC)


def test_an_impossible_day_is_clipped_not_an_error() -> None:
    """A 31 in a 30-day month would make pl.date raise and lose the whole survey."""
    dated = _haul_rows(month=[2, 2], day=[31, 31]).select(when=fishglob._haul_date())
    assert dated["when"][0] == datetime(2015, 2, 28, tzinfo=UTC)


# --- Evidence shape -----------------------------------------------------------
def test_evidence_conforms_to_the_survey_index_spec() -> None:
    table = fishglob.to_evidence(_haul_rows(), KEYS)
    spec = spec_for(EvidenceType.SURVEY_INDEX)
    assert table.schema.equals(spec.schema)
    spec.validate(table)


def test_the_haul_is_the_site_and_carries_the_survey_prefix() -> None:
    """Several surveys randomise stations within strata, so the haul is the only identifier
    that means the same thing everywhere -- and a bare station number would collide."""
    table = fishglob.to_evidence(_haul_rows(), KEYS)
    assert set(table.column("site_id").to_pylist()) == {"NEUS-Fall:h1"}


def test_gear_travels_with_the_row() -> None:
    """A gear change is a step change in the instrument, and a break term cannot be fitted
    for something the lake did not keep."""
    table = fishglob.to_evidence(_haul_rows(), KEYS)
    assert table.column("protocol").to_pylist()[0] == "NEUS-Fall gear=trawl"


def test_a_taxon_with_no_gbif_key_is_dropped_not_keyed_to_zero() -> None:
    table = fishglob.to_evidence(_haul_rows(), {"Gadus morhua": 2291432})
    assert table.num_rows == 1
    assert table.column("taxon_label").to_pylist() == ["Gadus morhua"]


def test_the_realm_and_scope_are_marine_and_exact() -> None:
    table = fishglob.to_evidence(_haul_rows(), KEYS)
    assert set(table.column("realm").to_pylist()) == {Realm.MARINE.value}
    assert set(table.column("taxon_scope").to_pylist()) == {TaxonScope.EXACT.value}


# --- Drivers ------------------------------------------------------------------
def test_drivers_are_deduplicated_to_the_haul() -> None:
    """FISHGLOB repeats a haul's temperature on every species row. Writing them as they come
    would multiply the driver table by the length of each catch list."""
    hauls = fishglob.haul_drivers(_haul_rows())
    assert hauls.height == 1


# --- Readers ------------------------------------------------------------------
def test_an_unreadable_file_names_the_survey_rather_than_raising_reader_internals(
    tmp_path: Path,
) -> None:
    """The caller skips one survey on this error, so it has to say which one."""
    not_rdata = tmp_path / "junk.RData"
    not_rdata.write_bytes(b"this is not an R data file")
    with pytest.raises(fishglob.SurveyUnreadableError, match="NEUS"):
        fishglob._read_rdata(not_rdata, "NEUS", force_latin1=False)


def test_the_slow_reader_retries_before_forcing_an_encoding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Forcing Latin-1 on a file that is really UTF-8 mangles accented species and vessel
    names silently, in a column used as a join key -- so the default encoding is tried first
    and the forced one is the fallback, not the entry point.
    """
    attempts: list[bool] = []

    def fake_read_rda(_path: object, **options: object) -> dict[str, object]:
        forced = bool(options.get("force_default_encoding"))
        attempts.append(forced)
        if not forced:
            # What pyreadr raises on the French-Canadian survey, and what sends the reader
            # down the forced-encoding path.
            not_utf8 = UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")
            raise not_utf8
        return {"frame": pl.DataFrame({"x": [1]})}

    monkeypatch.setattr(rdata, "read_rda", fake_read_rda)
    result = fishglob._read_rdata(Path("ignored.RData"), "GSL-N", force_latin1=False)
    assert attempts == [False, True]
    assert "frame" in result


# --- The three surveys that publish no raw catch ------------------------------
def test_a_cpua_only_survey_gets_its_catch_from_cpua_with_effort_one() -> None:
    """The branch EBS, AI and GOA depend on entirely -- they publish no raw catch at all."""
    frame = _haul_rows(num=[None, None], area_swept=[None, None]).with_columns(
        num_cpua=pl.Series([4.5, 1.1])
    )
    table = fishglob.to_evidence(fishglob.standardise_effort(frame, "EBS"), KEYS)
    assert set(table.column("effort").to_pylist()) == {1.0}
    assert set(table.column("effort_unit").to_pylist()) == {fishglob.PRESTANDARDISED_UNIT}
    assert table.column("count").to_pylist() == [4.5, 1.1]


def test_a_survey_with_raw_catch_keeps_its_swept_area() -> None:
    """The CPUA branch must not fire on a survey that has real effort to divide by."""
    frame = _haul_rows().with_columns(num_cpua=pl.Series([999.0, 999.0]))
    standardised = fishglob.standardise_effort(frame, "NEUS")
    assert standardised["effort_unit"][0] == fishglob.EFFORT_UNIT
    assert standardised["num"].to_list() == [12.0, 3.0]
    assert standardised["area_swept"].to_list() == [0.04, 0.04]


def test_a_survey_missing_both_catch_measures_is_not_silently_zeroed() -> None:
    """No raw catch and no CPUA either. It must fall through to the swept-area branch and be
    dropped downstream by the null filter, rather than acquire a fabricated count."""
    empty = pl.Series([None, None], dtype=pl.Float64)
    frame = _haul_rows(num=[None, None]).with_columns(num_cpua=empty)
    standardised = fishglob.standardise_effort(frame, "MYSTERY")
    assert standardised["effort_unit"][0] == fishglob.EFFORT_UNIT
    assert standardised["num"].null_count() == 2


def test_every_needed_column_is_either_written_or_a_driver() -> None:
    """Guards against a column being added to NEEDED and then silently unused."""
    written = set(fishglob.NUMERIC) | set(fishglob.INTEGER) | set(fishglob.TEXT)
    accounted = written | set(fishglob.DRIVERS)
    assert set(fishglob.NEEDED) - accounted == set()


def test_the_survey_list_has_no_duplicates() -> None:
    """Listed rather than discovered so an ingest is reproducible, which makes the list
    something that can drift."""
    assert len(fishglob.SURVEYS) == len(set(fishglob.SURVEYS))


def test_evidence_columns_are_ordered_by_the_schema_not_by_keyword_order() -> None:
    """polars does not guarantee that select() keyword order survives, and cast() matches by
    position, so a reordering upstream would silently swap two float columns."""
    table = fishglob.to_evidence(_haul_rows(), KEYS)
    assert table.schema.names == spec_for(EvidenceType.SURVEY_INDEX).schema.names
    assert isinstance(table, pa.Table)
