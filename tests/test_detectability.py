"""The detectability layer, and the unit-counting mistake it was built to avoid.

The layer's one substantive computation is "how many years does this cell have", and there are two
wrong ways to do it that both produce a plausible map. Counting years per *cell* lets a rotating set
of one-year sites add up to a series. Counting per *visit* -- which is what a trawl haul is -- gives
every unit a single year and erases a source that has thirty. The first mistake overstates coverage
and the second understates it, so both get a test.
"""

import json
from pathlib import Path
from typing import Any

import polars as pl
import pytest

from migratlas.catalog import loader
from migratlas.reports import detectability
from migratlas.reports.phase1b import MIN_YEARS as PHASE1B_MIN_YEARS

REPO = Path(__file__).resolve().parents[1]

PUBLISHED = REPO / "web" / "public" / "detectability.json"


def test_the_statuses_run_worst_to_best() -> None:
    """`collect` takes the max across sources, which is only "the best available" if this holds."""
    assert detectability.STATUSES[0] == "no-time-axis"
    assert detectability.STATUSES[-1] == "detectable"


def test_the_year_threshold_is_the_one_the_reports_already_apply() -> None:
    """A second, looser bar on the map than in the analysis would be a map of a different claim."""
    assert detectability.MIN_YEARS == PHASE1B_MIN_YEARS


def test_every_rule_names_a_unit_that_exists() -> None:
    for rule in detectability.RULES:
        assert rule.unit in detectability.UNITS, f"{rule.source_id} has no unit expression"
        assert rule.ceiling in detectability.STATUSES
        assert rule.reason, f"{rule.source_id} gives no reason for its ceiling"


def test_every_rule_names_a_registered_source() -> None:
    """A typo here would drop a source from the map with only a warning in the log."""
    registered = set(loader.load())
    for rule in detectability.RULES:
        assert rule.source_id in registered, f"{rule.source_id} is not in the registry"


def test_a_trawl_haul_is_not_the_unit_of_repetition() -> None:
    """The regression. FISHGLOB's `site_id` is `survey_unit:haul_id`, and a haul happens once.

    Counting years per haul gave the source zero detectable cells out of 1,126 -- twenty-nine
    scientific surveys, several of them running since the 1960s, reported as unable to support a
    trend. What repeats in a stratified trawl survey is the stratum, and `phase1b` pools by survey
    unit for the same reason.
    """
    hauls = pl.DataFrame({"site_id": ["NEFSC-spring:101", "NEFSC-spring:102", "AI:7"]})
    units = hauls.select(unit=detectability.UNITS["survey"])["unit"].to_list()
    assert units == ["NEFSC-spring", "NEFSC-spring", "AI"]

    rule = next(r for r in detectability.RULES if r.source_id == "fishglob")
    assert rule.unit == "survey", "fishglob is back to counting hauls"


def test_a_gridded_surface_falls_back_to_the_cell_and_cannot_reach_detectable() -> None:
    """The honest half of the fallback: it decides how a source reads, never that it passes.

    Both cell-unit sources are capped below "too-short" for reasons that have nothing to do with
    length, so standing the cell in for a missing unit cannot promote either of them.
    """
    for rule in detectability.RULES:
        if rule.unit != "cell":
            continue
        assert detectability.UNITS[rule.unit] is None
        assert detectability.STATUSES.index(rule.ceiling) < detectability.STATUSES.index(
            "too-short"
        ), f"{rule.source_id} uses the cell as its own unit and could pass on length alone"


# --- The published document ----------------------------------------------------
@pytest.fixture
def document() -> dict[str, Any]:
    if not PUBLISHED.is_file():
        pytest.skip("detectability.json not built")
    document: dict[str, Any] = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    return document


def test_the_indices_decode_to_the_longitude_and_latitude_they_came_from(
    document: dict[str, Any],
) -> None:
    """The regression that mattered most, because it looked like a rendering bug rather than a bug.

    `gridToFeatures` inverts the index as `(i + 0.5) * size - 180`. Written without the matching
    offset, every cell decoded 180 degrees west and 90 south, and the layer drew as a crescent along
    the limb of the globe -- plausible enough to be mistaken for a projection artefact.
    """
    grid = document["grid"]
    size = grid["cell_size_deg"]
    longitudes = [(x + 0.5) * size - 180 for x in grid["x"]]
    latitudes = [(y + 0.5) * size - 90 for y in grid["y"]]

    assert all(-180 <= value <= 180 for value in longitudes), (
        f"longitudes decode to [{min(longitudes)}, {max(longitudes)}]"
    )
    assert all(-90 <= value <= 90 for value in latitudes), (
        f"latitudes decode to [{min(latitudes)}, {max(latitudes)}]"
    )
    # The lake is emphatically not global, so a layer that filled both hemispheres evenly would
    # mean the indices had been scrambled into noise rather than merely shifted.
    assert max(latitudes) > 40, "nothing north of 40N, but three of the sources are"
    assert min(latitudes) < 0, "nothing south of the equator, but SABAP and MegaMove are"


def test_the_grid_is_the_shape_the_globe_already_reads(document: dict[str, Any]) -> None:
    grid = document["grid"]
    assert grid["format"] == "grid"
    assert len(grid["x"]) == len(grid["y"]) == len(grid["v"])
    assert grid["x"], "the grid is empty"
    assert grid["categories"] == list(detectability.STATUSES), (
        "the categories must be shipped in order, because `v` indexes into them"
    )
    assert all(0 <= value < len(grid["categories"]) for value in grid["v"])


def test_the_values_are_declared_nominal_rather_than_a_magnitude(document: dict[str, Any]) -> None:
    """A renderer that put these on a continuous ramp would invent an ordering they do not have.

    "effort not measured" is not two thirds of "detectable"; it is a different kind of problem.
    """
    assert document["grid"]["value_kind"] == "detectability"
    assert document["grid"]["categories"], "nothing for a legend to name"


def test_the_summary_accounts_for_every_cell_exactly_once(document: dict[str, Any]) -> None:
    assert sum(document["summary"].values()) == len(document["grid"]["v"])
    assert set(document["summary"]) == set(detectability.STATUSES)


def test_no_cell_is_counted_detectable_by_a_source_that_cannot_be(document: dict[str, Any]) -> None:
    """The ceiling is the whole mechanism: a cell cannot out-rank the source that covers it."""
    for entry in document["coverage"]:
        if entry["ceiling"] != "detectable":
            assert entry["detectable_cells"] == 0, (
                f"{entry['source_id']} is capped at {entry['ceiling']} and claims "
                f"{entry['detectable_cells']} detectable cells"
            )
        assert entry["detectable_cells"] <= entry["cells"]


def test_a_source_admitted_for_its_series_produces_at_least_one(document: dict[str, Any]) -> None:
    """The guard that was missing when the haul bug shipped, stated as the invariant it violates.

    A ceiling of "detectable" is an assertion that this source exists in the lake *because* it can
    support a trend. Zero detectable cells contradicts that assertion, and it is a much stronger
    check than any threshold: it caught nothing about the number 676 being right, but it would have
    refused 0 immediately, which is where the bug was.
    """
    for entry in document["coverage"]:
        if entry["ceiling"] != "detectable":
            continue
        assert entry["detectable_cells"] > 0, (
            f"{entry['source_id']} is in the lake because it can support trends and contributes "
            f"none of {entry['cells']} cells -- check what its unit of repetition is"
        )


def test_the_layer_spans_more_than_one_realm(document: dict[str, Any]) -> None:
    """The same structural guarantee the ledger carries, applied to the map.

    A detectability map of one realm would be a map of where *that* realm is studied, which reads
    as a global statement and is not one.
    """
    realms = {entry["realm"] for entry in document["coverage"]}
    assert len(realms) > 1, f"only {realms} on the map"


def test_the_grey_majority_is_stated_rather_than_left_to_be_noticed(
    document: dict[str, Any],
) -> None:
    """The finding, asserted. If detectable ever became the majority, the caveat would be wrong."""
    detectable = document["summary"]["detectable"]
    total = sum(document["summary"].values())
    assert detectable < total / 2, "most of the map is detectable now; rewrite the caveat"
    assert detectable > 0, "nothing is detectable, so something upstream is broken"


def test_every_source_that_measures_effort_rather_than_fixing_it_says_so(
    document: dict[str, Any],
) -> None:
    """Citizen science can clear the bar, and a claim built on it still has to carry the caveat."""
    notes = {entry["source_id"]: entry["effort_note"] for entry in document["coverage"]}
    for source_id in ("sabap1", "sabap2", "bbs"):
        if source_id in notes:
            assert notes[source_id], f"{source_id} clears the bar with no qualification attached"


def test_the_caveat_separates_could_be_measured_from_was_measured(document: dict[str, Any]) -> None:
    caveat = document["caveat"].lower()
    assert "not that a change has been detected" in caveat
    assert document["method"]
    assert document["supporting"]
