"""The findings document, and the invariants that keep it honest.

The numbers are computed from the lake, so they are not asserted here -- a test that hardcoded
them would be the drifting copy this module exists to avoid. What is asserted is the shape: that
nothing can be published without its scope, its caveat and a method note that exists.
"""

import json
from pathlib import Path

import pytest

from migratlas.reports import findings
from migratlas.reports.findings import Finding

REPO = Path(__file__).resolve().parents[1]

PUBLISHED = REPO / "web" / "public" / "findings.json"


def _finding(**overrides: object) -> Finding:
    fields: dict[str, object] = {
        "key": "test",
        "claim": "Something changed.",
        "value": "+1.0 units",
        "scope": "Somewhere, sometime.",
        "caveat": "It might not have.",
        "method": "docs/methods/phase1-phenology.md",
    }
    fields.update(overrides)
    return Finding(**fields)  # type: ignore[arg-type]


def test_the_document_declares_its_schema_version() -> None:
    """The frontend refuses a version it does not know, so the version has to be there."""
    document = json.loads(findings.render([_finding()]))
    assert document["schema_version"] == findings.SCHEMA_VERSION


def test_a_finding_round_trips_every_field_the_frontend_reads() -> None:
    document = json.loads(findings.render([_finding(supporting=["survived a thing"])]))
    [item] = document["findings"]
    assert set(item) == {
        "key",
        "claim",
        "value",
        "scope",
        "caveat",
        "method",
        "direction",
        "supporting",
    }
    assert item["supporting"] == ["survived a thing"]


def test_direction_defaults_to_neutral_rather_than_claiming_a_change() -> None:
    """An unlabelled finding must not be rendered as a detected change by default."""
    assert _finding().direction == "neutral"


# --- The published document --------------------------------------------------
@pytest.mark.skipif(not PUBLISHED.is_file(), reason="findings.json not built")
def test_every_published_finding_states_its_scope_and_caveat() -> None:
    """The invariant the whole module exists for.

    A number on a globe reads as settled fact. Publishing one without saying where it holds and
    what would make it wrong is the failure this project is arranged against, so it is a test
    rather than an intention.
    """
    document = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    assert document["findings"], "the document is empty"
    for item in document["findings"]:
        assert item["scope"].strip(), f"{item['key']} has no scope"
        assert item["caveat"].strip(), f"{item['key']} has no caveat"
        assert item["claim"].strip(), f"{item['key']} has no claim"
        assert item["value"].strip(), f"{item['key']} has no value"


@pytest.mark.skipif(not PUBLISHED.is_file(), reason="findings.json not built")
def test_every_published_finding_points_at_a_method_note_that_exists() -> None:
    """The method note is the pre-registration. A dead link there turns a tested claim back into
    an assertion, and the reader has no way to tell."""
    document = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    for item in document["findings"]:
        note = REPO / item["method"]
        assert note.is_file(), f"{item['key']} cites {item['method']}, which does not exist"


@pytest.mark.skipif(not PUBLISHED.is_file(), reason="findings.json not built")
def test_the_published_document_includes_a_null_and_a_limit() -> None:
    """A findings panel showing only changes would be lying by selection.

    Both are real results here -- no global marine shift, and the northern-hemisphere coverage
    bias -- and the point of publishing them is that a reader can see what did *not* happen and
    what this work cannot speak to.
    """
    document = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    directions = {item["direction"] for item in document["findings"]}
    assert "null" in directions, "no null result is published"
    assert "limit" in directions, "no limit of the work is published"


@pytest.mark.skipif(not PUBLISHED.is_file(), reason="findings.json not built")
def test_the_published_schema_version_matches_the_code() -> None:
    """A stale document rendered against new field names would show confident nonsense."""
    document = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    assert document["schema_version"] == findings.SCHEMA_VERSION
