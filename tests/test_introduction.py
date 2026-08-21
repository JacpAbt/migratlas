"""The introduction's counts must come from the ledger, not from a keyboard.

This module publishes prose, so most of it cannot be tested — a sentence is not right or wrong. What
*can* go wrong is the part that looks like prose and is actually a measurement: "9 findings across 3
realms" and "3 of the findings report no change". Both were typed in the first draft, which is
precisely the defect `reports/findings.py` re-runs the whole analysis to avoid and the defect
`tests/test_readme_status.py` was written after twice.
"""

import json
from pathlib import Path

import pytest

from migratlas.catalog import loader as catalog
from migratlas.reports import introduction

ROOT = Path(__file__).resolve().parents[1]


def test_the_counts_are_the_published_ones() -> None:
    published, realms, sources = introduction.counts()
    ledger = json.loads((ROOT / "web" / "public" / "findings.json").read_text(encoding="utf-8"))
    findings = ledger["findings"]

    assert published == len(findings)
    assert sources == len(catalog.load())
    # `all` is the realm a cross-realm finding carries. It is not a place and must not be counted
    # as one: counting it would inflate the number in the most prominent sentence on the site.
    assert realms == len({f["realm"] for f in findings} - {"all"})
    assert "all" not in {f["realm"] for f in findings} or realms < len(
        {f["realm"] for f in findings}
    )


def test_every_finding_is_counted_in_exactly_one_direction() -> None:
    published, _, _ = introduction.counts()
    assert sum(introduction.directions().values()) == published


def test_no_count_in_the_prose_is_typed() -> None:
    """The published sentences must carry the computed figures, not a snapshot of them.

    Written as a check on the *rendered* document rather than on the builder, because the failure
    being guarded is a sentence and a number drifting apart — which only shows up once the sentence
    is assembled.
    """
    document = introduction.build()
    published, realms, sources = introduction.counts()
    pointing = introduction.directions()

    assert f"{published} findings" in document.counted
    assert f"{realms} realms" in document.counted
    assert f"{sources} registered sources" in document.counted

    nulls = pointing.get("null", 0)
    limits = pointing.get("limit", 0)
    body = next(p.body for p in document.passages if "no change" in p.body)
    assert body.startswith(f"{nulls} of the findings report no change")
    assert f"{limits} report a limit" in body


def test_the_counts_would_move_if_the_ledger_did(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The one test that proves the figures are read rather than remembered.

    Everything above would still pass if the numbers happened to match today's ledger by accident.
    This points the module at a ledger of two findings and one realm and asserts the sentences say
    so — the only way to tell a computed figure from a lucky one.
    """
    fake = tmp_path / "findings.json"
    fake.write_text(
        json.dumps(
            {
                "findings": [
                    {"key": "a", "realm": "aerial", "direction": "change"},
                    {"key": "b", "realm": "all", "direction": "limit"},
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(introduction, "LEDGER", fake)

    published, realms, _ = introduction.counts()
    assert (published, realms) == (2, 1)
    document = introduction.build()
    assert "2 findings across 1 realms" in document.counted
    body = next(p.body for p in document.passages if "no change" in p.body)
    assert body.startswith("0 of the findings report no change")
    assert "1 report a limit" in body


def test_publishing_twice_changes_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A rebuild that dirties the diff is a rebuild nobody runs before committing."""
    out = tmp_path / "introduction.json"
    monkeypatch.setattr(introduction, "DOCUMENT", out)
    introduction.write()
    first = out.read_bytes()
    introduction.write()
    assert out.read_bytes() == first
    assert first.endswith(b"\n"), "no trailing newline, so every rebuild shows a diff"
