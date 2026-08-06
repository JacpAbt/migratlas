"""The floor purge: deleting rows an ingest should have refused, and nothing else.

Every test builds a real lake under tmp_path and reads it back, because the operation being tested
is a rewrite of Parquet partitions -- a mocked writer would prove nothing about the thing that can
actually go wrong, which is a partition left behind or a row deleted that should have stayed.
"""

from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pytest

from migratlas.evidence import EvidenceType, Realm, TaxonScope, spec_for
from migratlas.lake.purge import floor_rows, purge_floor_taxa
from migratlas.lake.reader import scan
from migratlas.lake.writer import write_evidence

SPEC = spec_for(EvidenceType.ABUNDANCE_SURFACE)
TS = pa.timestamp("ms", tz="UTC")

HUMAN_KEY = 2436436
WHALE_KEY = 8123917


def _surface(rows: list[tuple[int | None, str | None, int]], source_id: str = "obis") -> pa.Table:
    """`(taxon_key, taxon_label, year)` triples as an ABUNDANCE_SURFACE table."""
    count = len(rows)
    columns: dict[str, object] = {
        "source_id": [source_id] * count,
        "realm": [Realm.MARINE.value] * count,
        "taxon_scope": [TaxonScope.EXACT.value] * count,
        "taxon_key": pa.array([key for key, _label, _year in rows], type=pa.int64()),
        "taxon_label": pa.array([label for _key, label, _year in rows], type=pa.string()),
        "cell_longitude": [0.5] * count,
        "cell_latitude": [0.5] * count,
        "period_start": pa.array(
            [datetime(year, 1, 1, tzinfo=UTC) for _key, _label, year in rows], type=TS
        ),
        "period_end": pa.array(
            [datetime(year, 12, 31, tzinfo=UTC) for _key, _label, year in rows], type=TS
        ),
        "value": [1.0] * count,
        "value_kind": ["occurrence_count"] * count,
    }
    # Everything the schema allows to be absent stays absent, so the round trip is tested with
    # nulls in it rather than only with a fully populated row.
    for field in SPEC.schema:
        if field.name not in columns:
            columns[field.name] = pa.array([None] * count, type=field.type)
    return pa.table({field.name: columns[field.name] for field in SPEC.schema}, schema=SPEC.schema)


def _land(table: pa.Table, root: Path, source_id: str = "obis") -> None:
    write_evidence(table, SPEC, source_id=source_id, root=root)


def _keys(root: Path, source_id: str = "obis") -> list[int | None]:
    frame = scan(EvidenceType.ABUNDANCE_SURFACE, source_id=source_id, root=root).collect()
    return sorted(frame["taxon_key"].to_list(), key=lambda key: (key is None, key))


# --- Finding them ------------------------------------------------------------
def test_a_floor_taxon_is_found_by_its_key(tmp_path: Path) -> None:
    _land(_surface([(HUMAN_KEY, "Homo sapiens", 2015), (WHALE_KEY, "Physeter", 2015)]), tmp_path)
    [found] = floor_rows(tmp_path)
    assert found.rows == 1
    assert found.source_id == "obis"
    assert found.partitions == ("2015",)


def test_a_floor_taxon_is_found_by_its_name_when_the_key_is_missing(tmp_path: Path) -> None:
    """Movebank supplies names and the lake stores keys, so a check on one route is satisfiable
    by accident. `admit_taxon_for_ingest` refuses on both, and so does this."""
    _land(_surface([(None, "  HOMO   SAPIENS ", 2015), (WHALE_KEY, "Physeter", 2015)]), tmp_path)
    [found] = floor_rows(tmp_path)
    assert found.rows == 1


def test_a_clean_lake_reports_nothing(tmp_path: Path) -> None:
    _land(_surface([(WHALE_KEY, "Physeter macrocephalus", 2015)]), tmp_path)
    assert floor_rows(tmp_path) == []


def test_a_species_whose_name_merely_contains_homo_is_not_touched(tmp_path: Path) -> None:
    """*Homarus*, *Homalopsis*, and every other genus starting with the same five letters.

    A substring match here would delete real animals, which is a worse failure than the one this
    module exists to fix.
    """
    _land(_surface([(1, "Homarus americanus", 2015), (2, "Homalopsis buccata", 2015)]), tmp_path)
    assert floor_rows(tmp_path) == []


# --- Removing them -----------------------------------------------------------
def test_the_floor_rows_go_and_the_others_stay(tmp_path: Path) -> None:
    _land(
        _surface(
            [
                (HUMAN_KEY, "Homo sapiens", 2015),
                (WHALE_KEY, "Physeter", 2015),
                (WHALE_KEY, "Physeter", 2016),
            ]
        ),
        tmp_path,
    )
    [purged] = purge_floor_taxa(tmp_path)
    assert purged.removed == 1
    assert _keys(tmp_path) == [WHALE_KEY, WHALE_KEY]
    assert floor_rows(tmp_path) == []


def test_a_partition_holding_nothing_else_is_removed_rather_than_left(tmp_path: Path) -> None:
    """The one way this could silently do nothing.

    `write_dataset` deletes the partitions the incoming data covers and writes them again. A year
    whose every row was a floor row has no incoming data, so nothing deletes the old file and the
    rows survive a purge that reported success.
    """
    _land(_surface([(HUMAN_KEY, "Homo sapiens", 1934), (WHALE_KEY, "Physeter", 2016)]), tmp_path)
    purge_floor_taxa(tmp_path)

    assert not (tmp_path / "abundance_surface" / "source_id=obis" / "year=1934").exists()
    assert _keys(tmp_path) == [WHALE_KEY]
    assert floor_rows(tmp_path) == []


def test_partitions_with_no_floor_rows_are_not_rewritten(tmp_path: Path) -> None:
    """Blast radius. OBIS is 17.2 million rows and the floor touched 119 of them."""
    _land(
        _surface([(HUMAN_KEY, "Homo sapiens", 2015), (WHALE_KEY, "Physeter", 2016)]),
        tmp_path,
    )
    untouched = tmp_path / "abundance_surface" / "source_id=obis" / "year=2016"
    before = {path.name: path.stat().st_mtime_ns for path in untouched.rglob("*.parquet")}
    assert before

    purge_floor_taxa(tmp_path)
    after = {path.name: path.stat().st_mtime_ns for path in untouched.rglob("*.parquet")}
    assert after == before


def test_purging_twice_changes_nothing_the_second_time(tmp_path: Path) -> None:
    _land(_surface([(HUMAN_KEY, "Homo sapiens", 2015), (WHALE_KEY, "Physeter", 2015)]), tmp_path)
    assert purge_floor_taxa(tmp_path)[0].removed == 1
    assert purge_floor_taxa(tmp_path) == []
    assert _keys(tmp_path) == [WHALE_KEY]


def test_the_surviving_rows_keep_the_schema_they_had(tmp_path: Path) -> None:
    """A rewrite is where a column quietly changes type, and a mixed directory is then read by
    intersecting schemas with no error at all."""
    _land(_surface([(HUMAN_KEY, "Homo sapiens", 2015), (WHALE_KEY, "Physeter", 2015)]), tmp_path)
    purge_floor_taxa(tmp_path)

    frame = scan(EvidenceType.ABUNDANCE_SURFACE, source_id="obis", root=tmp_path).collect()
    for field in SPEC.schema:
        assert field.name in frame.columns, field.name


# --- The lake this actually ran against --------------------------------------
@pytest.mark.localdata
def test_the_real_lake_holds_no_floor_taxa() -> None:
    """Run with --run-localdata. The rule is that these rows are never stored, so once they are
    gone the only way to notice them coming back is to look."""
    found = floor_rows()
    assert not found, [(item.source_id, item.rows, item.labels) for item in found]
