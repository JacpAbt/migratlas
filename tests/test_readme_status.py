"""The README's status line is typed prose over computed facts; this pins them together.

The counts drifted twice: fixed at "five findings, twenty sources" on 2026-08-01, false again by
2026-08-07 with seven and 24. Every number on the site is recomputed on every build precisely
because a figure typed once goes stale silently — and the README's status line was the one typed
figure left. It cannot be computed (a README is not a build artifact), so it is guarded instead:
the sentence must agree with `findings.json` and the registry, or the gate refuses the build.
"""

import json
import re
from pathlib import Path
from typing import Any

from migratlas.catalog import loader as catalog

ROOT = Path(__file__).resolve().parents[1]


def _readme_flat() -> str:
    """The README with hard wraps and blockquote prefixes undone, so sentences match whole."""
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    return re.sub(r"\s+", " ", re.sub(r"\n> ?", " ", text))


def _findings() -> list[dict[str, Any]]:
    payload = json.loads((ROOT / "web" / "public" / "findings.json").read_text(encoding="utf-8"))
    findings: list[dict[str, Any]] = payload["findings"]
    return findings


def test_status_line_counts_are_the_computed_ones() -> None:
    findings = _findings()
    realms = {str(finding["realm"]) for finding in findings} - {"all"}
    expected = (
        f"{len(findings)} findings published and recomputed from the lake on every build, "
        f"across {len(realms)} realms and {len(catalog.load())} registered sources"
    )
    assert expected in _readme_flat()


def test_coverage_shares_quote_the_published_finding() -> None:
    """The southern-share paragraph must carry the same percentages as `coverage-bias`.

    Its predecessor said "0.0% ... lie south of the equator" for six days after SABAP made it
    false (TASKS #33). If the finding's shares move again, this points at the paragraph.
    """
    coverage = next(f for f in _findings() if f["key"] == "coverage-bias")
    shares = re.findall(r"\((\d+(?:\.\d+)?)%\)", str(coverage["value"]))
    assert len(shares) == 2, "coverage-bias no longer states two shares; rewrite this test"
    readme = _readme_flat()
    for share in shares:
        assert f"{share}%" in readme
