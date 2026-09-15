"""The book's openers, and the three things that keep them from drifting.

The prose is authored and cannot be tested for being right. What can be tested is that it stays
tied to the chapter list in `story.ts`, that it quotes the ledger rather than itself, and that it
keeps to the rule the voice depends on: no digits in the narration.
"""

import json
import re
from pathlib import Path
from typing import Any

import pytest

from migratlas.reports import chapters

LEDGER: dict[str, dict[str, Any]] = {
    "autumn-advance": {"key": "autumn-advance", "value": "-0.56 days per decade"},
    "flight-advance": {"key": "flight-advance", "value": "-2.10 days per decade"},
    "composition-stable": {"key": "composition-stable", "value": "flat"},
    "anthropogenic-share": {"key": "anthropogenic-share", "value": "50%-53% of it"},
    "marine-null": {"key": "marine-null", "value": "median -0.011"},
    "atlas-no-net-change": {"key": "atlas-no-net-change", "value": "median -0.007"},
    "displacement-flat": {"key": "displacement-flat", "value": "-1.84 km per decade"},
    "seas-disagree": {"key": "seas-disagree", "value": "Q 235.7 against 27.6"},
    "transfer-fails": {"key": "transfer-fails", "value": "0.68 against 0.06"},
    "skill-sparse": {"key": "skill-sparse", "value": "20/143 stations"},
    "projection-mask": {"key": "projection-mask", "value": "49% sayable"},
    "coverage-bias": {"key": "coverage-bias", "value": "35.5% against 1.00%"},
    "protocol-disagreement": {"key": "protocol-disagreement", "value": "1.17x"},
}


def test_every_opener_names_a_chapter_the_book_actually_has() -> None:
    """The two lists live in two languages, and nothing but this stops them drifting."""
    declared = set(chapters.slugs_in_story())
    for opener in chapters.build(LEDGER):
        assert opener.slug in declared, opener.slug


def test_the_chapters_that_carry_claims_all_have_an_opener() -> None:
    """The way in and the way out have their own pages; everything between needs an account."""
    story = chapters.slugs_in_story()
    assert {opener.slug for opener in chapters.build(LEDGER)} == set(story[1:-1])


def test_the_openers_are_in_the_books_own_order() -> None:
    """The order is the argument: each chapter exists because of what the one before found."""
    story = chapters.slugs_in_story()
    built = [opener.slug for opener in chapters.build(LEDGER)]
    assert built == [slug for slug in story if slug in set(built)]


def test_no_opener_carries_a_digit() -> None:
    """The rule the voice rests on.

    A number typed into narration is the one figure nobody checks and the first to go stale, so
    the prose says "about half a day" and the figures line says -0.56. This is what makes the
    plain register safe to write in: there is nothing in it that can quietly become wrong.
    """
    for opener in chapters.build(LEDGER):
        for paragraph in opener.paragraphs:
            found = re.findall(r"\d", paragraph)
            assert not found, f"{opener.slug} has digits in its prose: {found}"
        assert not re.findall(r"\d", opener.question), opener.slug


def test_every_figure_comes_from_the_ledger() -> None:
    """And a claim the ledger stopped publishing shows as missing rather than as a stale figure."""
    built = chapters.build(LEDGER)
    joined = " ".join(figure for opener in built for figure in opener.figures)
    assert "-0.56 days per decade" in joined
    assert "Q 235.7 against 27.6" in joined

    without = {k: v for k, v in LEDGER.items() if k != "seas-disagree"}
    degraded = " ".join(figure for opener in chapters.build(without) for figure in opener.figures)
    assert "Q 235.7 against 27.6" not in degraded
    assert "not published on this build" in degraded


def test_every_claim_in_the_book_is_carried_by_exactly_one_chapters_figures() -> None:
    """A figures line that forgot a claim is a chapter resting on evidence it never shows."""
    counted: dict[str, int] = {}
    for opener in chapters.build(LEDGER):
        for figure in opener.figures:
            key = figure.split(" — ")[0]
            counted[key] = counted.get(key, 0) + 1
    assert set(counted) == set(LEDGER)
    assert set(counted.values()) == {1}


def test_an_opener_says_something_rather_than_naming_the_chapter_again() -> None:
    for opener in chapters.build(LEDGER):
        assert opener.question.endswith("?")
        assert len(" ".join(opener.paragraphs)) > 400, opener.slug
        assert len(opener.paragraphs) > 1, opener.slug
        assert opener.figures, opener.slug


def test_the_document_round_trips(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> None:
    built = chapters.build(LEDGER)
    monkeypatch.setattr(chapters, "DOCUMENT", Path(str(tmp_path)) / "chapters.json")
    path = chapters.write(built)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == chapters.SCHEMA_VERSION
    assert set(payload["chapters"]) == {opener.slug for opener in built}
    first = payload["chapters"][built[0].slug]
    assert first["question"] == built[0].question
    assert first["paragraphs"] == built[0].paragraphs
    assert first["figures"] == built[0].figures
