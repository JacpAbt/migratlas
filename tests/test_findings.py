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
        "realm": "aerial",
        "taxon_scope": "unattributed",
        "evidence_type": "flux",
    }
    fields.update(overrides)
    return Finding(**fields)  # type: ignore[arg-type]


def test_the_document_declares_its_schema_version() -> None:
    """The frontend refuses a version it does not know, so the version has to be there."""
    document = json.loads(findings.render([_finding()]))
    assert document["schema_version"] == findings.SCHEMA_VERSION


def test_a_finding_round_trips_every_field_the_frontend_reads() -> None:
    """Pinned as a set, so adding a field to the schema without teaching the frontend fails here.

    That is why it is exhaustive rather than a subset check: `panels/findings.ts` declares the same
    shape by hand, and the two drifting apart is otherwise silent.
    """
    document = json.loads(
        findings.render(
            [
                _finding(
                    supporting=["survived a thing"],
                    bias=[findings.BiasDomain("temporal", "open", "unexplained step")],
                )
            ]
        )
    )
    [item] = document["findings"]
    assert set(item) == {
        "key",
        "claim",
        "value",
        "scope",
        "caveat",
        "method",
        "realm",
        "taxon_scope",
        "evidence_type",
        "bias",
        "direction",
        "supporting",
    }
    assert item["supporting"] == ["survived a thing"]
    assert item["bias"] == [{"domain": "temporal", "status": "open", "finding": "unexplained step"}]


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


# --- The bias assessment ------------------------------------------------------
def test_a_bias_domain_is_one_of_the_robitt_domains() -> None:
    """The domains are ROBITT's, not ours, so a typo must not invent a sixth one."""
    assert set(findings.BIAS_DOMAINS) == {
        "geographic",
        "temporal",
        "taxonomic",
        "environmental",
        "detectability",
        "phenological",
    }


def test_a_status_says_what_was_done_not_that_it_was_considered() -> None:
    """Four honest answers. "considered" is not among them, deliberately."""
    assert set(findings.BIAS_STATUSES) == {"addressed", "bounded", "open", "not applicable"}


def test_the_assessment_keeps_robitt_s_domain_order() -> None:
    """So two claims are comparable by reading down, rather than by hunting."""
    built = findings._domains(
        detectability=("addressed", "checked"),
        geographic=("bounded", "narrowed"),
    )
    assert [entry.domain for entry in built] == ["geographic", "detectability"]


@pytest.mark.skipif(not PUBLISHED.is_file(), reason="findings.json not built")
def test_every_published_finding_carries_a_bias_assessment() -> None:
    """A number without its risk of bias is the failure mode this whole ledger is arranged against.

    The assessment is a re-expression of work already in docs/methods/, so a claim without one means
    either the work was not done or it was not written down. Both are worth failing for.
    """
    document = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    for item in document["findings"]:
        assert item["bias"], f"{item['key']} carries no bias assessment"
        for entry in item["bias"]:
            assert entry["domain"] in findings.BIAS_DOMAINS, entry["domain"]
            assert entry["status"] in findings.BIAS_STATUSES, entry["status"]
            assert entry["finding"].strip(), f"{item['key']}/{entry['domain']} says nothing"


@pytest.mark.skipif(not PUBLISHED.is_file(), reason="findings.json not built")
def test_every_published_finding_names_its_realm_taxon_scope_and_evidence_type() -> None:
    document = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    for item in document["findings"]:
        for required in ("realm", "taxon_scope", "evidence_type"):
            assert item[required].strip(), f"{item['key']} has no {required}"


@pytest.mark.skipif(not PUBLISHED.is_file(), reason="findings.json not built")
def test_the_published_ledger_spans_more_than_one_realm() -> None:
    """The structural guard against drifting back to one taxon and one medium.

    The core was built taxon-agnostic and then three consecutive sources were birds. A convention
    would drift again; this fails.

    What it deliberately does not yet assert: the terrestrial realm is entirely birds, so a test
    demanding more than one *class* on land would fail today. That is the honest reason the non-bird
    non-bird terrestrial sources are queued rather than optional. When one lands, tighten
    this from realm to class.
    """
    document = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    realms = {item["realm"] for item in document["findings"]} - {"all"}
    assert len(realms) > 1, f"every claim is {realms}"
