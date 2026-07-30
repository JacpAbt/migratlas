"""Breeding Bird Survey rows, on runs whose counts and effort are known by construction.

The joins are the risk here, not the arithmetic: a count row means nothing until it is attached to
the run that produced it and the route that run drove, and the release keys those three files three
different ways. So the cases plant a route, a run and a count and assert what has to survive.
"""

import contextlib
from pathlib import Path
from types import SimpleNamespace

import polars as pl
import pytest

from migratlas.evidence import EvidenceType, spec_for
from migratlas.ingest import bbs
from migratlas.taxonomy import gbif


def _joined(**overrides: object) -> pl.DataFrame:
    """The frame `prepare` produces, without needing the release."""
    fields: dict[str, object] = {
        "run_id": "6234747",
        "aou": "02010",
        "total": 12,
        "stops": 4,
        "route_key": "840-02-001",
        "rpid": 101,
        "year": 1990,
        "month": 6,
        "day": 15,
        "run_type": "1",
        "observer": "1150175",
        "route_name": "ST FLORIAN",
        "latitude": 34.873263,
        "longitude": -87.604225,
        "name": "Dendrocygna autumnalis",
        "common": "Black-bellied Whistling-Duck",
    }
    fields.update(overrides)
    return pl.DataFrame([fields])


def test_effort_is_the_run_not_the_stops_the_species_was_found_at() -> None:
    """StopTotal is part of the response: a species detected at more stops is more abundant.

    Using it as effort would divide the response by itself and turn a real signal into a constant.
    """
    table = bbs.to_evidence(_joined(total=12, stops=4), {"Dendrocygna autumnalis": 2498325})
    assert table.column("count").to_pylist() == [12.0]
    assert table.column("effort").to_pylist() == [1.0]
    assert table.column("effort_unit").to_pylist() == [bbs.EFFORT_UNIT]


def test_the_protocol_carries_the_observer_the_run_type_and_the_rpid() -> None:
    """All three are break terms, and a break term cannot be fitted for what was not kept."""
    table = bbs.to_evidence(_joined(), {"Dendrocygna autumnalis": 2498325})
    protocol = table.column("protocol").to_pylist()[0]
    assert "rpid=101" in protocol
    assert "runtype=1" in protocol
    assert "observer=1150175" in protocol


def test_the_period_is_the_day_the_route_was_run() -> None:
    table = bbs.to_evidence(_joined(year=1990, month=6, day=15), {"Dendrocygna autumnalis": 1})
    start = table.column("period_start").to_pylist()[0]
    end = table.column("period_end").to_pylist()[0]
    assert (start.year, start.month, start.day) == (1990, 6, 15)
    assert start == end


def test_rows_match_the_schema_and_land_as_terrestrial() -> None:
    table = bbs.to_evidence(_joined(), {"Dendrocygna autumnalis": 2498325})
    assert table.schema == spec_for(EvidenceType.SURVEY_INDEX).schema
    assert table.column("realm").to_pylist() == ["terrestrial"]
    assert table.column("site_id").to_pylist() == ["840-02-001"]
    assert table.column("taxon_key").to_pylist() == [2498325]


def test_an_unresolved_binomial_is_dropped_rather_than_landed_without_a_taxon() -> None:
    frame = pl.concat([_joined(), _joined(aou="99999", name="Accipiter sp")])
    table = bbs.to_evidence(frame, {"Dendrocygna autumnalis": 2498325})
    assert table.num_rows == 1
    assert table.column("taxon_label").to_pylist() == ["Dendrocygna autumnalis"]


def test_the_standard_protocol_id_is_the_one_the_survey_uses() -> None:
    """Landed rows keep every RPID; the constant exists so an analysis can filter deliberately."""
    assert bbs.STANDARD_PROTOCOL == 101


def test_the_release_is_pinned_rather_than_discovered() -> None:
    """USGS publishes a new release most years as a separate item, so "latest" would drift."""
    assert bbs.ITEM == "6a0b0b0ab66b0188da36aedd"
    assert all(name in bbs.files() for name in (bbs.ROUTES, bbs.WEATHER, bbs.COUNTS, bbs.MIGRANTS))


def test_every_file_is_requested_by_name_not_by_disk_hash() -> None:
    """The `?f=__disk__<hash>` form the item also publishes is opaque and changes per release."""
    for name, remote in bbs.files().items():
        assert remote.url.endswith(f"?name={name}")
        assert "__disk__" not in remote.url


@pytest.mark.parametrize(
    ("padded", "clean"),
    [("001   ", "001"), ("  840", "840"), ("02010", "02010"), (" 12 ", "12")],
)
def test_fixed_width_padding_is_stripped_before_a_key_is_built(padded: str, clean: str) -> None:
    """The release pads its exports with spaces, and a padded key joins to nothing."""
    frame = pl.DataFrame({"CountryNum": [padded]})
    assert frame.select(bbs._trimmed("CountryNum"))["CountryNum"].to_list() == [clean]


def test_every_synonym_replacement_differs_from_the_name_it_replaces() -> None:
    """A no-op entry would look handled and resolve exactly as badly as before."""
    assert all(source != target for source, target in bbs.SYNONYMS.items())


def test_the_synonym_table_covers_only_genus_changes_not_groupings() -> None:
    """66 of the 70 failures are slash pairs, hybrids and 'sp.' groupings.

    Those are real records not attributable to a taxon, so they are dropped rather than patched.
    Only the four whose genus the survey changed ahead of the Backbone are replaced.
    """
    assert set(bbs.SYNONYMS) == {
        "Anarhynchus montanus",
        "Anarhynchus nivosus",
        "Anarhynchus wilsonia",
        "Botaurus exilis",
    }
    for source in bbs.SYNONYMS:
        assert "/" not in source
        assert not source.endswith("sp.")


def test_resolution_asks_gbif_for_the_replacement_and_keys_by_the_survey_name(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    asked: list[str] = []

    class _Match:
        usage_key = 6065879

    def _match(_: object, name: str) -> object:
        asked.append(name)
        return _Match()

    def _client() -> contextlib.AbstractContextManager[None]:
        return contextlib.nullcontext(None)

    monkeypatch.setattr(gbif, "match_name", _match)
    monkeypatch.setattr(gbif, "client", _client)
    monkeypatch.setattr(
        "migratlas.config.get_settings", lambda: SimpleNamespace(cache_dir=tmp_path)
    )

    keys = bbs.taxon_keys(["Anarhynchus nivosus"])
    assert asked == ["Charadrius nivosus"]
    assert keys == {"Anarhynchus nivosus": 6065879}
