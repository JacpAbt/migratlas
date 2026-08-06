"""The plain register on the three documents that are not the ledger.

`findings.json` got a second register in schema 3 and these three did not, so the site explained
itself plainly right up to the moment a reader clicked into the evidence. The same rules apply here
and are asserted here: a plain sentence may drop precision, may never add reach, and never replaces
the paragraph it heads.

Read from the built documents rather than the dataclasses, because what a reader gets is the JSON.
"""

import json
from pathlib import Path

import pytest

from migratlas.reports import counterfactual, detectability, findings, sandbox

REPO = Path(__file__).resolve().parents[1]
PUBLIC = REPO / "web" / "public"

RIBBON = PUBLIC / "counterfactual.json"
COVERAGE = PUBLIC / "detectability.json"
KNOBS = PUBLIC / "sandbox.json"

# Ceiling and interval markers borrowed from the ledger rather than restated: three documents with
# three ideas of what "plain" means would be no rule at all.
CEILING = findings.PLAIN_MAX_CHARS
INTERVALS = ("±", "+/-")


def _plain_lines() -> list[tuple[str, str]]:
    """Every plain sentence in the three documents, labelled by where it came from."""
    out: list[tuple[str, str]] = []
    if RIBBON.is_file():
        out.append(
            ("counterfactual", json.loads(RIBBON.read_text(encoding="utf-8"))["plain_disagreement"])
        )
    if COVERAGE.is_file():
        for held in json.loads(COVERAGE.read_text(encoding="utf-8"))["withheld"]:
            out.append((f"withheld {held['source_id']}", held["plain_reason"]))
    if KNOBS.is_file():
        for knob in json.loads(KNOBS.read_text(encoding="utf-8"))["knobs"]:
            out.append((f"knob {knob['key']}", knob["plain_why"]))
    return out


# --- Shape, always ------------------------------------------------------------
def test_every_document_declares_the_version_the_frontend_expects() -> None:
    """A register added without a version bump is a frontend rendering `undefined`."""
    assert counterfactual.SCHEMA_VERSION == 3
    assert detectability.SCHEMA_VERSION == 3
    assert sandbox.SCHEMA_VERSION == 2


def test_a_withheld_source_without_a_plain_reason_stops_the_build() -> None:
    """The one that will actually happen: a third source gets withheld and nobody writes the line.

    A lookup with a fallback would put a blank -- or worse, a technical rationale -- on the page
    that is this project's ethics in one screen.
    """
    with pytest.raises(ValueError, match="no plain-language reason"):
        detectability._plain_refusal("movebank_some_future_source")


def test_the_refusals_map_covers_exactly_what_is_withheld() -> None:
    """Neither a missing line nor one left behind by a source that stopped being withheld.

    Against `WITHHELD_SOURCES`, which is the list `_withheld` walks -- not `RULES`, which is the
    coverage grid and does not contain these two. A refusal is not a source that measures badly; it
    is one that is never drawn at all, and the two lists are different on purpose.
    """
    assert set(detectability.PLAIN_REFUSALS) == set(detectability.WITHHELD_SOURCES), (
        "PLAIN_REFUSALS and WITHHELD_SOURCES disagree about which sources are refused"
    )


# --- The published documents --------------------------------------------------
@pytest.mark.skipif(not RIBBON.is_file(), reason="documents not built")
def test_the_three_documents_carry_a_plain_line_everywhere_they_should() -> None:
    """Non-empty, and enough of them that a silently-empty section would show."""
    lines = _plain_lines()
    assert len(lines) >= 6, f"only {len(lines)} plain sentences across the three documents"
    for where, plain in lines:
        assert plain.strip(), f"{where} has an empty plain sentence"


@pytest.mark.skipif(not RIBBON.is_file(), reason="documents not built")
def test_a_plain_sentence_stays_plain_here_too() -> None:
    """The ledger's own two rules, applied to the documents that just got the register."""
    for where, plain in _plain_lines():
        assert len(plain) <= CEILING, f"{where} is {len(plain)} characters, over {CEILING}"
        for marker in INTERVALS:
            assert marker not in plain, f"{where} puts an interval in its plain sentence"


@pytest.mark.skipif(not RIBBON.is_file(), reason="documents not built")
def test_the_precise_text_is_still_published_in_full() -> None:
    """A second register, not a replacement.

    The failure this guards is the tempting one: someone decides the paragraph is redundant now
    that a sentence says it, and the audit quietly becomes a summary. Length is the proxy -- the
    precise text says more than the plain one by construction, so if it ever stops being longer,
    something has been cut.
    """
    ribbon = json.loads(RIBBON.read_text(encoding="utf-8"))
    assert len(ribbon["disagreement"]) > len(ribbon["plain_disagreement"])

    for held in json.loads(COVERAGE.read_text(encoding="utf-8"))["withheld"]:
        assert held["reason"].strip(), f"{held['source_id']} lost its full rationale"
        assert len(held["reason"]) > len(held["plain_reason"]), (
            f"{held['source_id']}'s full rationale is no longer longer than its plain line"
        )

    for knob in json.loads(KNOBS.read_text(encoding="utf-8"))["knobs"]:
        assert knob["why"].strip(), f"{knob['key']} lost its explanation"
        assert len(knob["why"]) > len(knob["plain_why"]), (
            f"{knob['key']}'s explanation is no longer longer than its plain line"
        )


@pytest.mark.skipif(not COVERAGE.is_file(), reason="documents not built")
def test_a_plain_refusal_does_not_soften_what_it_refuses() -> None:
    """ "May drop precision, may never add reach" has a specific meaning for a refusal.

    The plain line is allowed to omit the citation and the herd counts. It is not allowed to turn a
    refusal into a maybe, because the whole page exists to say these animals are drawn nowhere.
    """
    hedges = ("might", "may be", "could be", "possibly", "we think", "perhaps")
    for held in json.loads(COVERAGE.read_text(encoding="utf-8"))["withheld"]:
        lowered = held["plain_reason"].lower()
        found = [word for word in hedges if word in lowered]
        assert not found, f"{held['source_id']}'s plain refusal hedges: {found}"
