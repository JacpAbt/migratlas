"""The CPR reduction: one aggregate row per sample, from the wide taxon matrix."""

import polars as pl
import pytest

from migratlas.evidence import EvidenceType, spec_for
from migratlas.ingest.cpr import to_evidence


def _sample_frame() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "SampleId": ["474BC-23", "474BC-24"],
            "Latitude": [41.272, 41.5],
            "Longitude": [-27.618, -27.9],
            "MidPoint_Date_UTC": ["2010-09-24T04:13Z", "2010-09-24T06:47Z"],
            "Year": [2010, 2010],
            "Month": [9, 9],
            "Day": [24, 24],
            "Hour": [4, 6],
            "id_40": [0.0, 6.0],
            "id_41": [50.0, None],
            "id_84": [0.00000000010, 0.0],
        }
    )


def test_one_aggregate_row_per_sample() -> None:
    rows = to_evidence(_sample_frame())
    assert rows.height == 2
    assert rows["taxon_label"].unique().to_list() == ["plankton (CPR aggregate)"]
    assert rows["taxon_key"].null_count() == 2


def test_the_sum_skips_unassessed_and_keeps_traces_negligible() -> None:
    rows = to_evidence(_sample_frame())
    by_site = {r["site_id"]: r["count"] for r in rows.to_dicts()}
    # First sample: 0 + 50 + trace; the trace is deliberately negligible, not a 1.
    assert abs(by_site["474BC-23"] - 50.0) < 1e-6
    # Second sample: 6 + unassessed (null, contributes nothing) + 0.
    assert by_site["474BC-24"] == 6.0


def test_the_rows_conform_to_the_survey_index_schema() -> None:
    spec = spec_for(EvidenceType.SURVEY_INDEX)
    table = to_evidence(_sample_frame()).select(spec.schema.names).to_arrow().cast(spec.schema)
    spec.validate(table)
    assert table.num_rows == 2


def test_a_layout_change_refuses_loudly() -> None:
    stripped = _sample_frame().select("SampleId", "Latitude", "Longitude", "MidPoint_Date_UTC")
    with pytest.raises(ValueError, match="layout has changed"):
        to_evidence(stripped)
