"""The counterfactual ribbon, and the two things about its shape that are decisions.

A ribbon is easy to draw dishonestly. Two of the tests here exist to stop that: the counterfactual
must keep advancing, because only the attributed share was removed, and the observed line must stay
equal to the number the ledger publishes. Both are things a later "make the chart clearer" change
would break silently, and both would turn a modest true result into an overclaim.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from migratlas.reports import counterfactual, sandbox
from migratlas.reports.phase2a_timing import CLAIM_BAND

REPO = Path(__file__).resolve().parents[1]

PUBLISHED = REPO / "web" / "public" / "counterfactual.json"
LEDGER = REPO / "web" / "public" / "findings.json"

TOLERANCE = 0.01
"""Days per decade. The ledger rounds to two places, so anything tighter tests the formatter."""


def test_the_document_declares_its_schema_version() -> None:
    assert counterfactual.SCHEMA_VERSION >= 1


def test_the_claim_band_is_the_one_the_attribution_publishes_in() -> None:
    """The ribbon takes the band from the sandbox; this pins that copy to the source of truth."""
    assert sandbox.CLAIM_BAND == CLAIM_BAND


# --- The published document ----------------------------------------------------
@pytest.fixture
def document() -> dict[str, Any]:
    if not PUBLISHED.is_file():
        pytest.skip("counterfactual.json not built")
    document: dict[str, Any] = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    return document


def test_the_counterfactual_still_advances(document: dict[str, Any]) -> None:
    """The decision the module argues for, asserted so a later edit cannot quietly reverse it.

    Only `f x S x W` was attributed. About half the observed advance never tracked temperature and
    was attributed to nothing, so it survives into the counterfactual. A flat counterfactual would
    claim that unexplained half is natural, which nothing in the analysis establishes.
    """
    lines = {line["key"]: line for line in document["lines"]}
    observed = lines["observed"]["per_decade"]
    removed = lines["counterfactual"]["per_decade"]

    assert observed < 0, "the observed trend is meant to be an advance"
    assert removed < 0, "the counterfactual was flattened; only the attributed share comes out"
    assert abs(removed) < abs(observed), "removing the human share has to reduce the advance"
    assert abs(removed) > abs(observed) * 0.25, (
        f"the counterfactual keeps only {abs(removed / observed):.0%} of the advance, so more than "
        "the attributed share was removed"
    )


def test_removing_only_the_human_share_leaves_more_advance_than_removing_all_warming(
    document: dict[str, Any],
) -> None:
    """Holds if and only if f <= 1, so it is a check on the arithmetic, not on the ecology.

    At f = 0.98 the two lines sit almost on top of each other. That near-coincidence is the visual
    statement that almost none of the warming was natural, and it is worth pinning: if the ordering
    ever inverted, the ribbon would be saying natural forcing warmed the world more than total.
    """
    lines = {line["key"]: line for line in document["lines"]}
    assert lines["counterfactual"]["per_decade"] <= lines["no-thermal"]["per_decade"] + TOLERANCE
    assert document["terms"]["human_share_of_warming"] <= 1.0


def test_the_observed_line_is_the_number_the_ledger_publishes(document: dict[str, Any]) -> None:
    """Two computations of one trend are two things that can drift apart in front of a reader."""
    if not LEDGER.is_file():
        pytest.skip("findings.json not built")
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    published = next(f for f in ledger["findings"] if f["key"] == "autumn-advance")

    observed = next(line for line in document["lines"] if line["key"] == "observed")
    assert f"{observed['per_decade']:.2f}" in published["value"], (
        f"the ribbon draws {observed['per_decade']:.3f} and the ledger states {published['value']}"
    )


def test_every_line_passes_through_the_anchor_at_the_midpoint(document: dict[str, Any]) -> None:
    """The attribution constrains slopes and says nothing about levels, so the level is shared.

    Anchoring anywhere else -- the first year, say -- would open a gap at one end that a reader
    would read as a difference between the scenarios rather than as a drawing choice.
    """
    start, end = document["window"]
    anchor = document["anchor"]
    for line in document["lines"]:
        midpoint = (line["start"] + line["end"]) / 2
        assert midpoint == pytest.approx(anchor, abs=1e-9), (
            f"{line['key']} crosses its midpoint at {midpoint:.3f}, not the anchor {anchor:.3f}"
        )
        assert (line["end"] - line["start"]) == pytest.approx(
            line["per_decade"] / 10 * (end - start), abs=1e-9
        )


def test_the_divergence_is_reported_and_is_smaller_than_a_single_year_of_scatter(
    document: dict[str, Any],
) -> None:
    """The uncomfortable number, stated rather than hidden by a stretched axis.

    If the lines ever parted by more than the year-to-year scatter, something upstream broke: the
    attributed share of a half-day-per-decade trend cannot outgrow the weather.
    """
    scatter = max(abs(point["observed"] - document["anchor"]) for point in document["years"])
    assert 0 < document["divergence"] < scatter, (
        f"divergence {document['divergence']:.2f} days against a scatter of {scatter:.2f}"
    )
    assert "under a day" in document["caveat"] or "days" in document["caveat"]


def test_the_year_series_is_one_point_per_year_in_order(document: dict[str, Any]) -> None:
    years = [point["year"] for point in document["years"]]
    assert years == sorted(years)
    assert len(years) == len(set(years))
    assert (years[0], years[-1]) == tuple(document["window"])
    assert all(point["stations"] > 0 for point in document["years"])


def test_the_terms_are_shipped_so_the_arithmetic_can_be_checked_by_hand(
    document: dict[str, Any],
) -> None:
    """f x S x W is three numbers and a multiplication, and a reader has to see all three."""
    terms = document["terms"]
    expected = terms["human_share_of_warming"] * terms["thermal_days_per_decade"]
    assert terms["human_days_per_decade"] == pytest.approx(expected, abs=1e-9)
    assert terms["thermal_days_per_decade"] == pytest.approx(
        terms["sensitivity_days_per_degree"] * terms["warming_degrees_per_decade"], rel=0.15
    ), "the thermal term is the per-station average, so it may differ from the product of the means"
    assert terms["models"] > 0
    assert terms["stations"] > 0


def test_the_caveat_refuses_the_reading_a_ribbon_invites(document: dict[str, Any]) -> None:
    """The obvious misreading is "this year would have been different". Say so on the artifact."""
    caveat = document["caveat"].lower()
    assert "trend" in caveat
    assert "single year" in caveat or "any year" in caveat
    assert document["method"], "no method note to follow"
    assert document["supporting"], "no supporting evidence listed"
