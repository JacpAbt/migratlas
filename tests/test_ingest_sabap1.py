"""SABAP1 atlas cards, on records whose reporting rate is known by construction.

A reporting rate is a ratio of two counts of the same thing, which makes it exactly the quantity
that produces a plausible number from a wrong denominator. So the cards here are planted: the
numerator, the denominator and the cell each have one right answer.
"""

import contextlib
from pathlib import Path
from types import SimpleNamespace

import polars as pl
import pytest

from migratlas.evidence import EvidenceType, spec_for
from migratlas.ingest import sabap1
from migratlas.taxonomy import gbif


def _cards(rows: list[dict[str, object]]) -> pl.DataFrame:
    """The frame `read_cards` produces, without needing the two-gigabyte archive."""
    return pl.DataFrame(
        rows,
        schema={
            "card": pl.String,
            "year": pl.Int32,
            "month": pl.Int32,
            "cell_latitude": pl.Float64,
            "cell_longitude": pl.Float64,
            "name": pl.String,
        },
    )


def _card(card: str, name: str, *, lat: float = -26.125, lon: float = 31.875) -> dict[str, object]:
    return {
        "card": card,
        "year": 1988,
        "month": 6,
        "cell_latitude": lat,
        "cell_longitude": lon,
        "name": name,
    }


def test_the_rate_is_cards_with_the_species_over_cards() -> None:
    frame = _cards(
        [
            _card("a", "Accipiter badius"),
            _card("b", "Accipiter badius"),
            _card("b", "Bubo africanus"),
            _card("c", "Bubo africanus"),
            _card("d", "Bubo africanus"),
        ]
    )
    rates = sabap1.reporting_rates(frame).sort("name")
    assert rates["name"].to_list() == ["Accipiter badius", "Bubo africanus"]
    assert rates["count"].to_list() == [2, 3]
    # Four cards surveyed the cell, so both species share that denominator.
    assert rates["effort"].to_list() == [4, 4]


def test_a_species_seen_twice_on_one_card_counts_once() -> None:
    """The unit is the card, not the record: a card is a species list, and a list is a set."""
    frame = _cards([_card("a", "Accipiter badius")] * 3)
    rates = sabap1.reporting_rates(frame)
    assert rates["count"].to_list() == [1]
    assert rates["effort"].to_list() == [1]


def test_a_card_spanning_two_cells_contributes_effort_to_both() -> None:
    """830 of 98,878 real cards do this, and dropping one of the cells would understate effort."""
    frame = _cards(
        [
            _card("a", "Accipiter badius", lat=-26.125, lon=31.875),
            _card("a", "Accipiter badius", lat=-26.375, lon=31.875),
            _card("b", "Accipiter badius", lat=-26.125, lon=31.875),
        ]
    )
    rates = sabap1.reporting_rates(frame).sort("cell_latitude")
    assert rates["cell_latitude"].to_list() == [-26.375, -26.125]
    assert rates["effort"].to_list() == [1, 2]


def test_months_and_years_are_separate_periods() -> None:
    frame = _cards([_card("a", "Accipiter badius"), _card("b", "Accipiter badius")]).with_columns(
        month=pl.Series([6, 7], dtype=pl.Int32)
    )
    rates = sabap1.reporting_rates(frame)
    assert rates.height == 2
    assert rates["effort"].to_list() == [1, 1]


def test_the_cell_snap_is_idempotent_on_a_published_centre() -> None:
    """The archive's coordinates are already cell centres, so snapping must not move them."""
    centres = pl.DataFrame(
        {"latitude": [-26.125, -26.375, -34.875, -22.625], "longitude": [31.875] * 4}
    )
    snapped = centres.select(lat=sabap1._cell_centre("latitude"))
    assert snapped["lat"].to_list() == pytest.approx([-26.125, -26.375, -34.875, -22.625])


def test_the_cell_snap_puts_a_corner_coordinate_in_one_cell() -> None:
    """A value on a cell boundary has to land in exactly one cell, and deterministically."""
    edges = pl.DataFrame({"latitude": [-26.0, -26.25, -25.9999]})
    snapped = edges.select(lat=sabap1._cell_centre("latitude"))
    assert snapped["lat"].to_list() == pytest.approx([-25.875, -26.125, -25.875])


def test_evidence_rows_match_the_schema_and_carry_the_effort_unit() -> None:
    rates = sabap1.reporting_rates(_cards([_card("a", "Accipiter badius")]))
    table = sabap1.to_evidence(rates, {"Accipiter badius": 2480637})
    schema = spec_for(EvidenceType.SURVEY_INDEX).schema
    assert table.schema == schema
    assert table.column("effort_unit").to_pylist() == ["atlas_cards"]
    assert table.column("realm").to_pylist() == ["terrestrial"]
    assert table.column("taxon_key").to_pylist() == [2480637]
    assert table.column("site_id").to_pylist() == ["qdgc:-26.125:31.875"]


def test_the_period_covers_the_month_the_card_belongs_to() -> None:
    """A card is a month of coverage, so the row says so rather than implying a day."""
    rates = sabap1.reporting_rates(_cards([_card("a", "Accipiter badius")]))
    table = sabap1.to_evidence(rates, {"Accipiter badius": 1})
    start = table.column("period_start").to_pylist()[0]
    end = table.column("period_end").to_pylist()[0]
    assert (start.year, start.month, start.day) == (1988, 6, 1)
    assert (end.year, end.month, end.day) == (1988, 6, 30)


def test_an_unresolved_name_is_dropped_rather_than_landed_without_a_taxon() -> None:
    """SURVEY_INDEX allows a null taxon for radar biomass; an atlas record has no such excuse."""
    rates = sabap1.reporting_rates(
        _cards([_card("a", "Accipiter badius"), _card("a", "Nonexistent species")])
    )
    table = sabap1.to_evidence(rates, {"Accipiter badius": 2480637})
    assert table.num_rows == 1
    assert table.column("taxon_label").to_pylist() == ["Accipiter badius"]


def test_the_year_window_excludes_the_impossible_and_keeps_the_merely_old() -> None:
    """The archive holds 529 rows from 1901-1949 and one from 2975. Only the last is an error.

    An early draft of this bound started at 1950 and deleted the old ones while calling them
    implausible. Whether a 1934 card belongs to the atlas is the metric's question, answered
    through ATLAS_CORE -- not the ingest's, answered by deletion.
    """
    low, high = sabap1.PLAUSIBLE_YEARS
    assert low <= sabap1.ATLAS_CORE[0]
    assert high >= sabap1.ATLAS_CORE[1]
    assert low <= 1901
    assert low <= 1934
    assert not (low <= 2975 <= high)


def test_the_atlas_core_is_the_five_years_the_atlas_ran() -> None:
    assert sabap1.ATLAS_CORE == (1987, 1991)


def test_every_synonym_replacement_differs_from_the_name_it_replaces() -> None:
    """A no-op entry would look like a handled case and resolve exactly as badly as before."""
    assert all(source != target for source, target in sabap1.SYNONYMS.items())


def test_the_synonym_table_covers_the_six_names_the_backbone_refused() -> None:
    """Named individually because each was checked against /species/match before being written."""
    assert set(sabap1.SYNONYMS) == {
        "Aquila ayresii",
        "Bubo capensis",
        "Buteo vulpinus",
        "Parisoma subcaeruleum",
        "Psalidoprocne holomelaena",
        "Ptilopsus granti",
    }


def test_resolution_asks_gbif_for_the_replacement_and_keys_by_the_source_name(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The map is an implementation detail of resolution, so callers still see the source's name."""
    asked: list[str] = []

    class _Match:
        usage_key = 5232238

    def _match(_: object, name: str) -> object:
        asked.append(name)
        return _Match()

    def _client() -> contextlib.AbstractContextManager[None]:
        return contextlib.nullcontext(None)

    def _settings() -> object:
        return SimpleNamespace(cache_dir=tmp_path)

    monkeypatch.setattr(gbif, "match_name", _match)
    monkeypatch.setattr(gbif, "client", _client)
    monkeypatch.setattr("migratlas.config.get_settings", _settings)

    keys = sabap1.taxon_keys(["Ptilopsus granti"])
    assert asked == ["Ptilopsis granti"]
    assert keys == {"Ptilopsus granti": 5232238}


def test_effort_belongs_to_the_cell_month_and_must_not_be_summed_over_species() -> None:
    """The trap this source sets, encoded so it cannot be walked into quietly.

    `effort` repeats across every species row of a cell-month, so summing it over rows multiplies it
    by the number of species recorded. One real cell has 13 cards over the atlas core and sums to
    980. Pooling means taking effort once per distinct period and summing counts separately.
    """
    frame = _cards(
        [
            _card("a", "Accipiter badius"),
            _card("a", "Bubo africanus"),
            _card("a", "Pytilia melba"),
            _card("b", "Accipiter badius"),
        ]
    )
    rates = sabap1.reporting_rates(frame)

    # Two cards surveyed the cell-month, and three species rows all carry that same 2.
    assert rates["effort"].to_list() == [2, 2, 2]
    assert rates["effort"].sum() == 6

    keys = ("cell_latitude", "cell_longitude", "year", "month")
    pooled = float(rates.unique(subset=keys)["effort"].sum())
    assert pooled == 2

    # And the pooled rate for the species on both cards is 1, for the others a half.
    counts = dict(zip(rates["name"].to_list(), rates["count"].to_list(), strict=True))
    assert counts["Accipiter badius"] / pooled == pytest.approx(1.0)
    assert counts["Bubo africanus"] / pooled == pytest.approx(0.5)


def test_a_pooled_reporting_rate_cannot_exceed_one() -> None:
    """A species cannot appear on more cards than were submitted, at any pooling."""
    frame = _cards(
        [_card(card, "Accipiter badius") for card in ("a", "b", "c")]
        + [_card("a", "Bubo africanus")]
    ).with_columns(month=pl.Series([6, 7, 8, 6], dtype=pl.Int32))
    rates = sabap1.reporting_rates(frame)

    keys = ("cell_latitude", "cell_longitude", "year", "month")
    cards = float(rates.unique(subset=keys)["effort"].sum())
    for name in ("Accipiter badius", "Bubo africanus"):
        seen = float(rates.filter(pl.col("name") == name)["count"].sum())
        assert 0 < seen / cards <= 1.0
