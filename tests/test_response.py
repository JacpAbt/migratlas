"""The response dial, and the two things that would make it dishonest.

A dial is a sensitivity read forwards. It becomes dishonest in exactly two ways, and both are
tested here rather than trusted. If the baseline position does not reproduce the published
sensitivity, the dial and the ledger are free to disagree and the panel is a toy. And if the
envelope were computed *across* stations rather than within them, it would be far wider than the
fit's own range and would license dial positions the response has never been tested at — which is
the failure mode `DATASETS.md` calls the novelty mask, arriving through the back door.
"""

import json
from pathlib import Path

import polars as pl
import pytest

from migratlas.constants import CLAIM_BAND
from migratlas.reports import response

REPO = Path(__file__).resolve().parents[1]
PUBLISHED = REPO / "web" / "public" / "response.json"


def test_the_document_declares_its_schema_version() -> None:
    empty = response.Response(response.SCHEMA_VERSION, [], [])
    assert json.loads(response.render(empty))["schema_version"] == response.SCHEMA_VERSION


def test_the_baseline_position_is_one_of_the_settings() -> None:
    """A default naming no setting would leave the panel nothing to anchor to."""
    assert response.BASELINE_KEY in {response._key(s) for s in response.TEMPERATURE_SETTINGS}
    assert response.BASELINE_KEY in {response._key(s) for s in response.WIND_SETTINGS}


def test_the_settings_reach_outside_a_plausible_envelope() -> None:
    """The positions are fixed rather than drawn from the envelope, on purpose.

    A set of positions chosen to all fit inside the observed range would make the withholding
    unreachable and the bound invisible, which is the opposite of the point.
    """
    assert max(response.TEMPERATURE_SETTINGS) < response.BEYOND_TEMPERATURE
    # And the band that bounds the dial must sit strictly inside the extremes it is measured
    # against, or "the band rather than the extreme" is a distinction with no consequence.
    assert response.ENVELOPE_BAND == (0.05, 0.95)


def test_the_envelope_is_measured_within_station_not_across_stations() -> None:
    """The discriminating case, and the one that would silently widen the dial.

    Two stations sitting twenty degrees apart, each varying by one degree around its own usual.
    Within station the record contains departures of ±1; across stations it spans twenty. The
    response was fitted on the former, so the envelope has to be the former.
    """
    series = pl.DataFrame(
        {
            "station_id": ["cold"] * 3 + ["warm"] * 3,
            "temperature": [-1.0, 0.0, 1.0, 19.0, 20.0, 21.0],
        }
    )
    envelope = response.anomaly_envelope(series, "temperature")
    assert envelope[0.0] == pytest.approx(-1.0)
    assert envelope[1.0] == pytest.approx(1.0)


def test_a_setting_outside_the_envelope_gets_no_number() -> None:
    """Withheld by omission from the dial, and answered by the refusal instead."""
    envelope = dict.fromkeys(response.ENVELOPE_QUANTILES, 0.0)
    envelope[response.ENVELOPE_BAND[0]], envelope[response.ENVELOPE_BAND[1]] = -1.0, 1.0
    # Deliberately generous extremes: if the dial were bounded by these instead of by the band,
    # every position below would pass and this test would not be testing anything.
    envelope[0.0], envelope[1.0] = -9.0, 9.0
    dial = response._dial(
        key="probe",
        question="?",
        why="why",
        plain_why="plain",
        source="src",
        settings=(-2.0, -1.0, 0.0, 1.0, 2.0),
        sensitivity=-0.5,
        ci95=0.1,
        stations=78,
        envelope=envelope,
        unit="°C",
        warmer="warmer",
        cooler="cooler",
    )
    keys = {variant.key for variant in dial.variants}
    assert keys == {"minus-1", "unchanged", "plus-1"}, "positions outside ±1 must be dropped"
    assert "plus-2" not in keys, "the extremes must not license a position the band excludes"


def test_the_baseline_variant_reproduces_the_sensitivity_exactly() -> None:
    """The invariant the whole panel rests on, and the one the sandbox pins for its own knobs."""
    envelope = dict.fromkeys(response.ENVELOPE_QUANTILES, 0.0)
    envelope[response.ENVELOPE_BAND[0]], envelope[response.ENVELOPE_BAND[1]] = -3.0, 3.0
    dial = response._dial(
        key="probe",
        question="?",
        why="why",
        plain_why="plain",
        source="src",
        settings=response.TEMPERATURE_SETTINGS,
        sensitivity=-0.659,
        ci95=0.165,
        stations=78,
        envelope=envelope,
        unit="°C",
        warmer="warmer",
        cooler="cooler",
    )
    baseline = next(v for v in dial.variants if v.key == response.BASELINE_KEY)
    assert baseline.value == pytest.approx(-0.659)
    assert baseline.ci95 == pytest.approx(0.165)

    # And asking for nothing must imply nothing, or the dial has an offset it cannot justify.
    unchanged = next(v for v in dial.variants if v.key == "unchanged")
    assert unchanged.value == 0.0


def test_the_dial_is_scoped_to_the_band_the_claim_is_published_in() -> None:
    """Scope is load-bearing: `transfer-fails` put hold-one-out error at 0.68 across realms."""
    assert CLAIM_BAND == (37, 50)


# --- The published document ---------------------------------------------------
@pytest.mark.skipif(not PUBLISHED.is_file(), reason="response.json not built")
def test_every_dial_carries_both_registers_and_names_its_source() -> None:
    document = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    assert document["knobs"], "the response panel has no dials"
    for knob in document["knobs"]:
        assert knob["plain_why"].strip(), f"{knob['key']} has no plain line"
        assert knob["why"].strip(), f"{knob['key']} does not say what it is for"
        assert "phase2a_timing" in knob["source"], (
            f"{knob['key']} must name the published fit it reads, not a new estimate"
        )
        keys = {variant["key"] for variant in knob["variants"]}
        assert knob["default"] in keys, f"{knob['key']} defaults outside its own settings"


@pytest.mark.skipif(not PUBLISHED.is_file(), reason="response.json not built")
def test_the_panel_refuses_the_two_questions_it_must_refuse() -> None:
    """Extrapolation past the fitted range, and being read as a forecast.

    Both refusals are the point of publishing the dial at all. Losing either would leave a panel
    that invites precisely the two readings this project has spent two phases earning the right to
    reject.
    """
    document = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    keys = {refusal["key"] for refusal in document["refusals"]}
    assert {"beyond-the-envelope", "not-a-forecast"} <= keys

    by_key = {refusal["key"]: refusal for refusal in document["refusals"]}
    assert "Withheld" in by_key["beyond-the-envelope"]["verdict"]
    assert by_key["beyond-the-envelope"]["evidence"], "a withholding needs its measurement"
    assert "chance" in by_key["not-a-forecast"]["verdict"]
