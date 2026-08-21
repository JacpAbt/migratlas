"""The book's introduction: what this is, what kind of claim is in it, and how to read a caveat.

ADR 0013 decision 3 -- the book opens like a book, and an introduction is the first thing a
visitor sees. This is where its prose is authored, for the reason `CLAUDE.md` gives about all
frontend prose: it is written in Python and rendered verbatim, so changing a sentence means
editing this file, regenerating the JSON and updating the browser assertion that quotes it.
Prose written in a Svelte component is prose nothing holds to account.

**The counts are computed and the sentences are not.** Three numbers here come from the published
ledger and the registry rather than from a keyboard, because a figure typed once goes stale silently
-- which is the whole reason `reports/findings.py` re-runs the analysis on every build, and the
reason `tests/test_readme_status.py` exists at all. An introduction that said "nine findings" while
the ledger held eleven would be the same defect in a more prominent place.

**This needs no lake**, unlike every other module in this package. It measures nothing: it counts
what is already published and writes prose around it. So it can be rebuilt on a clone with no data,
which is worth stating because the rest of `reports/` cannot.
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final

from migratlas.catalog import loader as catalog

SCHEMA_VERSION: Final = 1

PUBLIC: Final = Path("web/public")
LEDGER: Final = PUBLIC / "findings.json"
DOCUMENT: Final = PUBLIC / "introduction.json"

# The realm every cross-realm finding carries, which is not a place and must not be counted as one.
EVERYWHERE: Final = "all"


@dataclass(frozen=True, slots=True)
class Passage:
    """One turn of the argument, headed so a reader can skip it and still know what it said."""

    heading: str
    body: str


@dataclass(frozen=True, slots=True)
class Introduction:
    """The whole document, as the book renders it."""

    schema_version: int
    title: str
    standfirst: str
    counted: str
    passages: tuple[Passage, ...]


def counts() -> tuple[int, int, int]:
    """Findings, realms and registered sources, from what is published rather than from memory.

    The same three the README's status line is held to, computed the same way, so the book and the
    README cannot disagree about the size of the project.
    """
    findings = _findings()
    realms = {str(finding["realm"]) for finding in findings} - {EVERYWHERE}
    return len(findings), len(realms), len(catalog.load())


def _findings() -> list[dict[str, object]]:
    payload = json.loads(LEDGER.read_text(encoding="utf-8"))
    published: list[dict[str, object]] = payload["findings"]
    return published


def directions() -> dict[str, int]:
    """How many findings point which way.

    Computed for the same reason the totals are: the paragraph about nulls and limits names them by
    number, and the first draft of it typed "three and three" -- which was true on the day and is
    exactly the figure this module's own docstring says goes stale silently. A sentence that counts
    the ledger has to count the ledger.
    """
    tally: dict[str, int] = {}
    for finding in _findings():
        tally[str(finding["direction"])] = tally.get(str(finding["direction"]), 0) + 1
    return tally


def build() -> Introduction:
    """The introduction, with its counts filled in."""
    published, realms, sources = counts()
    pointing = directions()
    nulls = pointing.get("null", 0)
    limits = pointing.get("limit", 0)
    return Introduction(
        schema_version=SCHEMA_VERSION,
        title="How to read this",
        standfirst=(
            "This is a notebook about where animals go and what is changing it. Not a summary of "
            "the field — a record of what this project has actually measured, including the parts "
            "that did not work."
        ),
        counted=(
            f"{published} findings across {realms} realms, from {sources} registered sources. "
            "Every number is recomputed from the data on every build, so none of them can quietly "
            "go stale."
        ),
        passages=(
            Passage(
                heading="Every claim carries its own scope",
                body=(
                    "A number here always arrives with what it covers and what it does not. The "
                    "autumn timing result is about 78 radar stations between 37 and 50 degrees "
                    "north, and it says so; it is not a statement about a continent, or about "
                    "birds, because the radar cannot tell a bird from a bat. Where the scope is "
                    "narrow the page says so rather than rounding it up."
                ),
            ),
            Passage(
                heading="The results that found nothing are here too",
                body=(
                    f"{nulls} of the findings report no change and {limits} report a limit on what "
                    "this work can see — a chapter of each. They are not filed as failures. A "
                    "ledger showing only the positive results would be lying by selection, and the "
                    "strongest thing in here is a marine record where the surveys disagree even "
                    "about which way fish are moving."
                ),
            ),
            Passage(
                heading="A caveat is not an apology",
                body=(
                    "Beside each number is a line saying what would have to be true for it to "
                    "mislead you. Read it as part of the result rather than as hedging: it is "
                    "there because the alternative is a reader who trusts the figure further than "
                    "the evidence goes. Where a prediction was made and graded, the grade stands "
                    "whichever way it went."
                ),
            ),
            Passage(
                heading="Three ways in",
                body=(
                    "The chapters are the argument, in order: what changed, what did not, what "
                    "cannot be seen, what can be predicted, and why. Or take the tabs in any "
                    "order — each chapter stands alone. Or go straight to the world in the back "
                    "pocket and look at the layers yourself, with nothing argued over the top."
                ),
            ),
        ),
    )


def write(document: Introduction | None = None) -> Path:
    """Publish it. Sorted keys and a trailing newline, so a rebuild is a no-op in the diff."""
    payload = asdict(document or build())
    DOCUMENT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return DOCUMENT
