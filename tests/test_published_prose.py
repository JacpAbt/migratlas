"""One check across every published artifact: the prose is finished.

Written after shipping the string `{primary.ensemble:.0%}` to a reader. An f-string prefix was lost
in an edit, so a claim about human attribution went into `counterfactual.json` with the format spec
still in it. Nothing failed -- every other test read the *numbers*, and the numbers were right.

The class of bug is broader than the one instance. Everything a reader is told on this site is a
Python string assembled from computed terms, and the ways that goes wrong leave their signature in
the text rather than in the data: a brace that never got substituted, a doubled space where a clause
was cut, a sentence ending in a comma. So the check is over the text of every artifact at once,
rather than per report, because the next one will be somewhere else.
"""

import json
import re
from pathlib import Path
from typing import Any

import pytest

PUBLIC = Path(__file__).resolve().parents[1] / "web" / "public"

MIN_PROSE = 25
"""Characters. Below this a string is a label or a key, not a sentence, and none of this applies."""

# A brace holding anything that could be a Python expression: an attribute path, a format spec, an
# index. Matched loosely on purpose -- a false positive costs one rephrasing and a miss ships.
UNSUBSTITUTED = re.compile(r"\{[^{}]*[.:\[][^{}]*\}|\{[a-z_][a-z_0-9]*\}")


def _strings(value: Any, path: str = "") -> list[tuple[str, str]]:
    """Every string in a document, with the path it sits at, so a failure names its own location."""
    if isinstance(value, str):
        return [(path, value)]
    if isinstance(value, dict):
        return [found for key, item in value.items() for found in _strings(item, f"{path}.{key}")]
    if isinstance(value, list):
        return [
            found
            for index, item in enumerate(value)
            for found in _strings(item, f"{path}[{index}]")
        ]
    return []


@pytest.fixture(params=sorted(PUBLIC.glob("*.json")), ids=lambda path: path.name)
def published(request: pytest.FixtureRequest) -> list[tuple[str, str]]:
    path: Path = request.param
    return _strings(json.loads(path.read_text(encoding="utf-8")), path.name)


def test_no_string_carries_an_unsubstituted_placeholder(published: list[tuple[str, str]]) -> None:
    """The bug that prompted this file. A format spec in shipped prose is a reader-facing error."""
    leaked = [f"{path}: {text}" for path, text in published if UNSUBSTITUTED.search(text)]
    assert not leaked, "unsubstituted placeholders in published prose:\n" + "\n".join(leaked)


def test_no_sentence_ends_mid_clause(published: list[tuple[str, str]]) -> None:
    """A trailing comma or conjunction means a clause was cut and the join was not re-read."""
    truncated = [
        f"{path}: ...{text[-60:]}"
        for path, text in published
        if len(text) >= MIN_PROSE
        and re.search(r"[,;]$|\b(and|or|but|the|of|a|to|is)$", text.strip())
    ]
    assert not truncated, "prose ending mid-clause:\n" + "\n".join(truncated)


def test_no_string_carries_a_doubled_space_or_a_space_before_punctuation(
    published: list[tuple[str, str]],
) -> None:
    """The signature of two concatenated fragments that each thought they owned the separator."""
    seams = [
        f"{path}: {text}"
        for path, text in published
        if "  " in text or re.search(r"\s[,.;:]", text) or " ." in text
    ]
    assert not seams, "bad seams in published prose:\n" + "\n".join(seams)
