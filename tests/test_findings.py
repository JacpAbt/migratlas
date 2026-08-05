"""The findings document, and the invariants that keep it honest.

The numbers are computed from the lake, so they are not asserted here -- a test that hardcoded
them would be the drifting copy this module exists to avoid. What is asserted is the shape: that
nothing can be published without its scope, its caveat and a method note that exists.
"""

import ast
import json
import re
from pathlib import Path
from unittest import mock

import pytest

from migratlas.evidence import EvidenceType
from migratlas.lake.reader import sources as lake_sources
from migratlas.reports import findings
from migratlas.reports.findings import Finding

REPO = Path(__file__).resolve().parents[1]

PUBLISHED = REPO / "web" / "public" / "findings.json"


def _finding(**overrides: object) -> Finding:
    fields: dict[str, object] = {
        "key": "test",
        "plain": "A thing is different now.",
        "matters": "Because it is.",
        "plain_caveat": "It might not be.",
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


def test_no_published_value_is_a_number_someone_typed() -> None:
    """The module's own rule, enforced against its syntax tree rather than trusted.

    `findings.py` says every published number is recomputed from the lake on every build, and for
    one finding it was not: `composition-stable`'s airspeed was a string with the figure written
    into it, so `phase1c` could have moved and the site would have gone on publishing the old one.
    That was fixed by hand and nothing stopped it coming back.

    Checked on `value` alone, and deliberately not on `scope` or `claim`. Those carry numbers that
    are properties of a source rather than results -- "29 harmonised surveys", "1995" -- and a rule
    broad enough to catch those would be turned off within a month.

    A name or a call passes: the requirement is that the figure came from somewhere, not that it
    arrived through an f-string.
    """
    tree = ast.parse((REPO / "src" / "migratlas" / "reports" / "findings.py").read_text("utf-8"))
    typed: list[str] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
            continue
        if node.func.id != "Finding":
            continue
        for keyword in node.keywords:
            if keyword.arg != "value":
                continue
            given = keyword.value
            literal = isinstance(given, ast.Constant) and isinstance(given.value, str)
            # An f-string with nothing interpolated into it is a literal wearing a prefix.
            empty = isinstance(given, ast.JoinedStr) and not any(
                isinstance(part, ast.FormattedValue) for part in given.values
            )
            if literal or empty:
                typed.append(f"line {given.lineno}")
    assert not typed, f"a published value is written out rather than computed: {typed}"


def test_the_coverage_claim_enumerates_its_sources_rather_than_naming_them() -> None:
    """The bug this file did not catch, and the exact one its target predicted.

    `_southern_share` computed each share from the lake and hardcoded *which two sources* to
    compute it over. Its docstring said why that mattered -- "the day a southern source lands, a
    hardcoded 0% would be a lie on the site" -- and then SABAP1 and SABAP2 landed, 19.7 million
    rows at 22 to 35 degrees south, and the site went on publishing 0.0% southern for months.

    Recomputing the number was never the weak point. Deciding what to recompute it over was. So
    this asserts the *set*: every evidence type holding data is either declared to carry a time
    axis or declared pooled, with no third option that means "quietly skipped".
    """
    live = [kind for kind in EvidenceType if lake_sources(kind)]
    assert live, "no evidence in the lake, so this test proves nothing"
    for kind in live:
        assert kind in findings.TIME_AXIS or kind in findings.POOLED, (
            f"{kind} holds data and the coverage claim does not account for it"
        )


def test_a_new_evidence_type_stops_the_build_rather_than_being_skipped() -> None:
    """And the enforcement, not only the declaration.

    Asserting the maps are exhaustive is worth little if `_coverage` would shrug at a gap. Patched
    rather than waited for: the point is that the omission is loud.
    """
    live = [kind for kind in EvidenceType if lake_sources(kind)]
    orphan = next(iter(live))
    with (
        mock.patch.object(findings, "TIME_AXIS", {}),
        mock.patch.object(findings, "POOLED", frozenset()),
        pytest.raises(ValueError, match="0% southern"),
    ):
        findings._coverage()
    assert orphan is not None


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
        "plain",
        "matters",
        "claim",
        "plain_caveat",
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
def test_every_published_finding_says_it_plainly_and_says_why_it_matters() -> None:
    """The second register is required, exactly as the caveat is.

    A precise sentence nobody outside the field can read is not a published finding, it is a
    published artefact of one. Both registers or neither.
    """
    document = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    for item in document["findings"]:
        for required in ("plain", "matters", "plain_caveat"):
            assert item[required].strip(), f"{item['key']} has no {required}"


@pytest.mark.skipif(not PUBLISHED.is_file(), reason="findings.json not built")
def test_a_plain_sentence_stays_plain() -> None:
    """Two ways it stops being the thing it was added to be.

    Length, because a plain register that grows into a second dense paragraph has lost the reader
    it exists for -- twice. And interval notation, because a sentence carrying `±` is not the plain
    one: the measurement has its own field, set in a face with tabular figures, and duplicating it
    here would be a second copy of a number that can drift.
    """
    document = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    for item in document["findings"]:
        plain = item["plain"]
        assert len(plain) <= findings.PLAIN_MAX_CHARS, (
            f"{item['key']}'s plain sentence is {len(plain)} characters, "
            f"over {findings.PLAIN_MAX_CHARS}"
        )
        assert "±" not in plain, f"{item['key']} puts an interval in its plain sentence"
        assert "+/-" not in plain, f"{item['key']} puts an interval in its plain sentence"


@pytest.mark.skipif(not PUBLISHED.is_file(), reason="findings.json not built")
def test_the_precise_claim_is_still_published_in_full() -> None:
    """The plain register is a second one, not a replacement.

    ADR 0007 refuses to let the layout decide what the science says. Adding a shorter sentence
    above the claim is fine; the failure this guards is the next change, where someone notices the
    claim is now redundant and deletes it.
    """
    document = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    for item in document["findings"]:
        assert item["claim"].strip(), f"{item['key']} has no claim"
        assert item["claim"] != item["plain"], f"{item['key']} publishes one sentence twice"
        assert item["caveat"] != item["plain_caveat"], f"{item['key']} publishes one caveat twice"


@pytest.mark.skipif(not PUBLISHED.is_file(), reason="findings.json not built")
def test_no_plain_sentence_claims_a_taxon_its_claim_does_not() -> None:
    """The one way a plain rewrite can be dishonest rather than merely loose.

    A plain sentence may drop precision. It may not add reach. `autumn-advance` is the live
    temptation: "birds are migrating earlier" is what everyone wants it to say, the radar cannot
    see a bird, and the whole of Phase 1c exists to bound exactly that.
    """
    creatures = re.compile(r"\bbird|\bbat\b|\bbats\b|\binsect|\bswallow|\bwarbler", re.IGNORECASE)
    document = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    for item in document["findings"]:
        if item["taxon_scope"] != "unattributed":
            continue
        named = creatures.search(item["plain"])
        assert not named, (
            f"{item['key']} is taxon_scope=unattributed but its plain sentence says "
            f"{named.group(0)!r}"
        )


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


def test_the_coverage_block_counts_evidence_types_rather_than_naming_a_number() -> None:
    """The bug this pins shipped for a while and nothing could have caught it.

    The taxonomic line read "`track` is the fifth evidence type in use" while four were in use --
    written when a fifth looked imminent, and then true of nothing. It is a count of the lake, so
    it is substituted rather than typed, and asserting it twice with different counts is what makes
    "substituted" mean something.
    """
    for count in (4, 6):
        taxonomic = next(
            entry for entry in findings._coverage_bias(count) if entry.domain == "taxonomic"
        )
        assert f"{count} of 7" in taxonomic.finding


@pytest.mark.skipif(not PUBLISHED.is_file(), reason="findings.json not built")
def test_a_published_interval_agrees_with_the_word_beside_it() -> None:
    """A value that calls itself flat must have an interval that covers zero.

    The composition claim asserts the mixture did not drift, and `collect` withholds it when the
    fit says otherwise. This is the same check from the other end: a value that says "(flat)" while
    its own interval excludes zero is a sentence contradicting its own number, and that is exactly
    what a typed value drifting away from a recomputed one looks like.
    """
    pattern = re.compile(r"([+-]?\d+\.\d+)\s*±\s*(\d+\.\d+)")
    document = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    for item in document["findings"]:
        if "(flat)" not in item["value"]:
            continue
        match = pattern.search(item["value"])
        assert match, f"{item['key']} calls itself flat with no interval to check: {item['value']}"
        estimate, interval = float(match.group(1)), float(match.group(2))
        assert abs(estimate) < interval, (
            f"{item['key']} is published as flat at {estimate:+} ± {interval}, which excludes zero"
        )


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
