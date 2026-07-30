"""The confound sandbox, and the one invariant that makes it worth trusting.

The sandbox's whole claim is that switching a safeguard off shows what the published number owes to
that safeguard. That claim collapses if the "on" setting does not reproduce the published number, so
the important test here is not that the variants exist — it is that the default agrees with the
ledger, computed independently from the lake.
"""

import json
import re
from pathlib import Path

import pytest

from migratlas.reports import sandbox
from migratlas.reports.phase2a_timing import CLAIM_BAND

REPO = Path(__file__).resolve().parents[1]

PUBLISHED = REPO / "web" / "public" / "sandbox.json"
LEDGER = REPO / "web" / "public" / "findings.json"


def test_the_document_declares_its_schema_version() -> None:
    document = json.loads(sandbox.render(sandbox.Sandbox(sandbox.SCHEMA_VERSION, [], [])))
    assert document["schema_version"] == sandbox.SCHEMA_VERSION


def test_the_effort_thresholds_include_no_correction_at_all() -> None:
    """0.8 is what Phase 1b published and 0.6/0.95 are its sensitivity checks.

    Zero is the one the sandbox adds, and the only one that answers the reader's actual question:
    what does this look like if nobody corrects for effort?
    """
    assert 0.0 in sandbox.FOOTPRINTS
    assert 0.8 in sandbox.FOOTPRINTS
    assert tuple(sorted(sandbox.FOOTPRINTS)) == sandbox.FOOTPRINTS


def test_the_claim_band_matches_the_one_the_ledger_publishes_in() -> None:
    """Two copies of a filter are two things that can drift, so this pins them together."""
    assert sandbox.CLAIM_BAND == CLAIM_BAND


# --- The published document ---------------------------------------------------
@pytest.mark.skipif(not PUBLISHED.is_file(), reason="sandbox.json not built")
def test_every_knob_names_a_default_that_exists_among_its_variants() -> None:
    """A default naming nothing would leave the frontend no published number to anchor to."""
    document = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    assert document["knobs"], "the sandbox has no knobs"
    for knob in document["knobs"]:
        keys = {variant["key"] for variant in knob["variants"]}
        assert knob["default"] in keys, (
            f"{knob['key']} defaults to {knob['default']!r}, not in {keys}"
        )
        assert len(keys) > 1, f"{knob['key']} has nothing to compare its default against"


@pytest.mark.skipif(not PUBLISHED.is_file(), reason="sandbox.json not built")
def test_every_knob_says_why_the_safeguard_exists_and_where_it_lives() -> None:
    """A slider with no lesson attached is a toy, and one with no source is unfalsifiable."""
    document = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    for knob in document["knobs"]:
        assert knob["question"].strip().endswith("?"), knob["key"]
        assert knob["why"].strip(), f"{knob['key']} does not say why the safeguard exists"
        assert knob["source"].strip(), f"{knob['key']} does not say what it varies"
        assert knob["claim"].strip(), f"{knob['key']} bears on no claim"


@pytest.mark.skipif(not PUBLISHED.is_file(), reason="sandbox.json not built")
def test_every_variant_carries_the_count_it_was_averaged_over() -> None:
    """A variant that quietly analyses fewer units is not comparable with the default.

    Dropping the effort rule changes how many species-survey pairs survive, so the number moving is
    only half the story — the reader needs to see whether the sample moved with it.
    """
    document = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    for knob in document["knobs"]:
        for variant in knob["variants"]:
            assert variant["n"] > 0, f"{knob['key']}/{variant['key']} analysed nothing"
            assert variant["unit"].strip(), f"{knob['key']}/{variant['key']} has no unit"


@pytest.mark.skipif(
    not (PUBLISHED.is_file() and LEDGER.is_file()), reason="sandbox.json or findings.json not built"
)
def test_each_default_reproduces_the_number_the_ledger_publishes() -> None:
    """The invariant the sandbox lives or dies on.

    Both documents are computed from the lake by the same functions, so their agreement is not a
    coincidence to be asserted loosely — the default variant and the published claim should be the
    same number to two decimals. A mismatch means the sandbox is demonstrating a different analysis
    from the one the ledger reports, which would make every "look what happens when you turn this
    off" misleading rather than instructive.
    """
    document = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    ledger = {
        item["key"]: item for item in json.loads(LEDGER.read_text(encoding="utf-8"))["findings"]
    }

    checked = 0
    for knob in document["knobs"]:
        finding = ledger.get(knob["claim"])
        assert finding is not None, (
            f"{knob['key']} names claim {knob['claim']!r}, which is not published"
        )
        default = next(v for v in knob["variants"] if v["key"] == knob["default"])

        # The ledger formats its value for display, so the comparison is on the number inside it.
        published = _leading_number(finding["value"])
        if published is None:
            continue
        assert abs(default["value"] - published) < 0.005, (
            f"{knob['key']} default {default['value']:+.3f} != published {published:+.3f} "
            f"for {knob['claim']}"
        )
        checked += 1

    assert checked > 0, "no knob was checked against the ledger, so the invariant is untested"


def _leading_number(text: str) -> float | None:
    """The first signed decimal in a display string, or None if it holds no number."""
    match = re.search(r"[-+−]?\d+\.\d+", text.replace("−", "-"))
    return float(match.group()) if match else None


@pytest.mark.skipif(not PUBLISHED.is_file(), reason="sandbox.json not built")
def test_the_refusal_names_the_analysis_it_declined_and_the_evidence() -> None:
    """A refusal is not a knob, and the difference is the lesson.

    A knob says the correction changes the answer; a refusal says no correction exists, so the
    question cannot be answered with this data at all. The second is the more common situation and
    the one a sandbox of sliders would quietly deny.
    """
    document = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    assert document["refusals"], (
        "no refusal is published, which implies every confound has a switch"
    )
    for refusal in document["refusals"]:
        assert refusal["question"].strip().endswith("?")
        assert refusal["naive"].strip(), (
            f"{refusal['key']} does not say what it would appear to show"
        )
        assert refusal["evidence"], f"{refusal['key']} refuses without evidence"
        assert refusal["verdict"].strip()
        assert (REPO / refusal["method"]).is_file(), refusal["method"]


@pytest.mark.skipif(not PUBLISHED.is_file(), reason="sandbox.json not built")
def test_the_obis_refusal_reproduces_the_percentiles_the_method_note_recorded() -> None:
    """The teaching example has to be the audited one, not a fresh unaudited analysis.

    `docs/methods/phase1b-marine.md` recorded start-year percentiles of 1985 / 2012 / 2022 when
    the decision not to run this metric was made. Different numbers here mean either the lake
    changed underneath the decision or the sandbox is computing something else, and both mean the
    demonstration no longer supports the refusal it is attached to.
    """
    document = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    refusal = next(item for item in document["refusals"] if item["key"] == "obis-poleward")
    percentiles = {
        entry["key"]: entry["value"]
        for entry in refusal["evidence"]
        if entry["key"].startswith("start-p")
    }
    assert percentiles["start-p10"] == pytest.approx(1985, abs=1)
    assert percentiles["start-p50"] == pytest.approx(2012, abs=1)
    assert percentiles["start-p90"] == pytest.approx(2022, abs=1)
