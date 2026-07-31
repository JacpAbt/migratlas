"""The two counterfactual ribbons, and the things about their shape that are decisions.

A ribbon is easy to draw dishonestly, and a *pair* of them adds a second way. Both are guarded here.

- Each counterfactual must keep advancing, because only the attributed share was removed, and each
  observed line must stay equal to the number the ledger publishes. A later "make the chart clearer"
  change would break either silently and turn a modest true result into an overclaim.
- No ribbon may restate another. Schema 1 drew a third line that was `observed - S x W` against
  `observed - f x S x W` with `f` at 0.98, so it sat 0.006 days away: one piece of evidence drawn
  twice, which reads as corroboration and is not. A ribbon has to disagree to earn its place.
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

DISTINCT = 0.05
"""How far apart two counterfactuals must sit, in days per decade, to be two pieces of evidence.

Set above the 0.006 that the dropped third line managed and well below the 0.17 the surviving pair
disagrees by, so it fails on a duplicate and passes on a disagreement.
"""


def test_the_document_declares_its_schema_version() -> None:
    assert counterfactual.SCHEMA_VERSION >= 2


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


@pytest.fixture
def ribbons(document: dict[str, Any]) -> list[dict[str, Any]]:
    published: list[dict[str, Any]] = document["ribbons"]
    assert published, "no ribbons published"
    return published


def _lines(ribbon: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {line["key"]: line for line in ribbon["lines"]}


def _anchor(ribbon: dict[str, Any]) -> float:
    """The level all of a ribbon's lines pass through, read back off the first of them."""
    first = ribbon["lines"][0]
    return float(first["start"] + first["end"]) / 2


def test_every_counterfactual_still_advances(ribbons: list[dict[str, Any]]) -> None:
    """The decision the module argues for, asserted so a later edit cannot quietly reverse it.

    Each ribbon removes only what its own method attributes. About half the observed advance never
    tracked temperature and was attributed to nothing, so it survives into both counterfactuals. A
    flat counterfactual would claim that unexplained half is natural, which nothing establishes.
    """
    for ribbon in ribbons:
        lines = _lines(ribbon)
        observed = lines["observed"]["per_decade"]
        removed = lines["counterfactual"]["per_decade"]

        assert observed < 0, f"{ribbon['key']}: the observed trend is meant to be an advance"
        assert removed < 0, f"{ribbon['key']}: flattened; only the attributed share comes out"
        assert abs(removed) < abs(observed), f"{ribbon['key']}: removal has to reduce the advance"
        assert abs(removed) > abs(observed) * 0.25, (
            f"{ribbon['key']}: the counterfactual keeps only {abs(removed / observed):.0%} of the "
            "advance, so more than the attributed share was removed"
        )


def test_no_ribbon_restates_another(ribbons: list[dict[str, Any]]) -> None:
    """Two ribbons that agree are one ribbon drawn twice, and read as corroboration they are not.

    This is why schema 1's third line was dropped rather than moved into a chart of its own. The
    check is on the *counterfactual* slopes: the observed line is deliberately the same in both.
    """
    slopes = [_lines(ribbon)["counterfactual"]["per_decade"] for ribbon in ribbons]
    for index, first in enumerate(slopes):
        for second in slopes[index + 1 :]:
            assert abs(first - second) > DISTINCT, (
                f"two counterfactuals sit {abs(first - second):.3f} days per decade apart, "
                "which is one piece of evidence drawn twice"
            )


def test_the_observed_line_is_the_same_in_every_ribbon(ribbons: list[dict[str, Any]]) -> None:
    """One record, one fit. Charts that disagree about what happened are a bug in the pair."""
    observed = {round(_lines(ribbon)["observed"]["per_decade"], 6) for ribbon in ribbons}
    assert len(observed) == 1, f"the ribbons draw different observed trends: {sorted(observed)}"


def test_the_observed_line_is_the_number_the_ledger_publishes(
    ribbons: list[dict[str, Any]],
) -> None:
    """Two computations of one trend are two things that can drift apart in front of a reader."""
    if not LEDGER.is_file():
        pytest.skip("findings.json not built")
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    published = next(f for f in ledger["findings"] if f["key"] == "autumn-advance")

    observed = _lines(ribbons[0])["observed"]["per_decade"]
    assert f"{observed:.2f}" in published["value"], (
        f"the ribbon draws {observed:.3f} and the ledger states {published['value']}"
    )


def test_a_ribbons_lines_all_pass_through_one_level(ribbons: list[dict[str, Any]]) -> None:
    """The attribution constrains slopes and says nothing about levels, so the level is shared.

    Anchoring anywhere else -- the first year, say -- would open a gap at one end that a reader
    would read as a difference between the scenarios rather than as a drawing choice.
    """
    for ribbon in ribbons:
        start, end = ribbon["window"]
        anchor = _anchor(ribbon)
        for line in ribbon["lines"]:
            midpoint = (line["start"] + line["end"]) / 2
            assert midpoint == pytest.approx(anchor, abs=1e-9), (
                f"{ribbon['key']}/{line['key']} crosses its midpoint at {midpoint:.3f}, "
                f"not {anchor:.3f}"
            )
            assert (line["end"] - line["start"]) == pytest.approx(
                line["per_decade"] / 10 * (end - start), abs=1e-9
            )


def test_each_divergence_is_reported_and_smaller_than_a_single_year_of_scatter(
    ribbons: list[dict[str, Any]],
) -> None:
    """The uncomfortable number, stated rather than hidden by a stretched axis.

    If lines ever parted by more than the year-to-year scatter, something upstream broke: the
    attributed share of a half-day-per-decade trend cannot outgrow the weather.
    """
    for ribbon in ribbons:
        anchor = _anchor(ribbon)
        scatter = max(abs(point["observed"] - anchor) for point in ribbon["years"])
        assert 0 < ribbon["divergence"] < scatter, (
            f"{ribbon['key']}: divergence {ribbon['divergence']:.2f} days against a scatter of "
            f"{scatter:.2f}"
        )


def test_each_year_series_is_one_point_per_year_in_order(ribbons: list[dict[str, Any]]) -> None:
    for ribbon in ribbons:
        years = [point["year"] for point in ribbon["years"]]
        assert years == sorted(years)
        assert len(years) == len(set(years))
        assert (years[0], years[-1]) == tuple(ribbon["window"])
        assert all(point["stations"] > 0 for point in ribbon["years"])


def test_no_ribbon_is_drawn_over_years_its_counterfactual_does_not_cover(
    ribbons: list[dict[str, Any]],
) -> None:
    """A window is a limit, so it has to bound the drawing and not only the caveat.

    ATTRICI's counterfactual ends in 2019 while the radar record runs to 2025. Extending its line to
    2025 would be an extrapolation dressed as a measurement.
    """
    for ribbon in ribbons:
        assert ribbon["window"][0] <= ribbon["years"][0]["year"]
        assert ribbon["years"][-1]["year"] <= ribbon["window"][1]
        assert str(ribbon["window"][1]) in ribbon["caveat"] or ribbon["window"][1] >= 2025, (
            f"{ribbon['key']} stops in {ribbon['window'][1]} without saying so in its caveat"
        )


def test_every_ribbon_says_where_its_attribution_stops(ribbons: list[dict[str, Any]]) -> None:
    """The asymmetry this field exists to close, kept closed.

    Shading only ATTRICI's chart was the first version, and it read as though DAMIP carried evidence
    to 2025. It does not: `f` is a scalar fitted to 2014 and then applied to the whole observed
    trend, so its line runs on through years that never constrained it. Both limits are real, they
    are not the same limit, and neither may be left to the caveat.
    """
    for ribbon in ribbons:
        through = ribbon["attributed_through"]
        window = ribbon["window"]
        assert window[0] < through <= window[1], (
            f"{ribbon['key']} is attributed through {through}, outside its window {window}"
        )
        assert str(through) in ribbon["caveat"], (
            f"{ribbon['key']} is attributed through {through} and its caveat does not say so"
        )

    reach = {ribbon["attributed_through"] for ribbon in ribbons}
    if len(ribbons) > 1:
        assert len(reach) > 1, (
            "both ribbons are attributed through the same year, so one of them is being credited "
            f"with the other's reach: {sorted(reach)}"
        )


def test_the_terms_are_shipped_so_the_arithmetic_can_be_checked_by_hand(
    ribbons: list[dict[str, Any]],
) -> None:
    """Every ribbon is a response function times a warming, and a reader has to see both."""
    for ribbon in ribbons:
        terms = ribbon["terms"]
        lines = _lines(ribbon)
        assert terms["stations"] > 0
        assert terms["sensitivity_days_per_degree"] < 0, (
            f"{ribbon['key']}: a positive response would mean warming delayed the passage"
        )

        drawn = lines["observed"]["per_decade"] - lines["counterfactual"]["per_decade"]
        assert terms["removed_days_per_decade"] == pytest.approx(drawn, abs=1e-9), (
            f"{ribbon['key']}: the terms say {terms['removed_days_per_decade']:.4f} days per "
            f"decade came out and the lines are drawn {drawn:.4f} apart"
        )
        assert terms["observed_days_per_decade"] == pytest.approx(
            lines["observed"]["per_decade"], abs=1e-9
        )


def test_each_removal_is_the_product_its_method_says_it_is(ribbons: list[dict[str, Any]]) -> None:
    """The multiplication behind each ribbon, checkable by hand from the shipped terms.

    Named per ribbon rather than looped generically: the two methods factor differently, and a check
    loose enough to cover both would not catch either going wrong.
    """
    terms = {ribbon["key"]: ribbon["terms"] for ribbon in ribbons}

    damip = terms["damip"]
    assert damip["removed_days_per_decade"] == pytest.approx(
        damip["human_share_of_warming"] * damip["thermal_days_per_decade"], abs=1e-9
    )
    assert damip["human_share_of_warming"] <= 1.0, "no more than all of the warming was human"
    assert damip["thermal_days_per_decade"] == pytest.approx(
        damip["sensitivity_days_per_degree"] * damip["warming_degrees_per_decade"], rel=0.15
    ), "the thermal term is the per-station average, so it may differ from the product of the means"
    assert damip["models"] > 0

    if "attrici" not in terms:
        return
    attrici = terms["attrici"]
    assert attrici["removed_days_per_decade"] == pytest.approx(
        attrici["sensitivity_days_per_degree"] * attrici["warming_removed_degrees_per_decade"],
        abs=1e-9,
    )
    assert 0 < attrici["share_of_factual_warming"] < 1, (
        "the detrending removed none or all of the factual warming, which it cannot do"
    )
    assert attrici["sensitivity_days_per_degree"] == pytest.approx(
        damip["sensitivity_days_per_degree"], abs=1e-9
    ), "the response function is meant to be shared, so only the warming term differs"


def test_the_disagreement_between_the_ribbons_is_explained_with_numbers(
    document: dict[str, Any],
) -> None:
    """The one thing that must not be left to the reader.

    Two attributions of the same advance that differ by a factor of two, shipped without an
    explanation, would be worse than shipping either alone -- a reader would average them, and an
    average of two different quantities answers no question. So the explanation has to be there, and
    it has to quote magnitudes rather than merely assert that a difference exists.
    """
    disagreement = document["disagreement"]
    assert any(character.isdigit() for character in disagreement), (
        "the disagreement is described without a single number, so it explains nothing"
    )
    assert len(disagreement) > 200, "too short to be an explanation of two different quantities"
    if len(document["ribbons"]) > 1:
        assert "averag" in disagreement.lower(), "the reading to refuse is averaging; refuse it"


def test_the_shared_caveat_refuses_the_reading_a_ribbon_invites(document: dict[str, Any]) -> None:
    """The obvious misreading is "this year would have been different". Say so on the artifact."""
    caveat = document["shared_caveat"].lower()
    assert "trend" in caveat
    assert "single year" in caveat or "any year" in caveat
    assert all(ribbon["method"] for ribbon in document["ribbons"]), "a ribbon with no method note"
    assert document["supporting"], "no supporting evidence listed"
