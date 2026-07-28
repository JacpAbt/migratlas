"""Taxonomy helpers. The name-cleaning cases are all real GBIF responses."""

import pytest

from migratlas.evidence import Realm
from migratlas.taxonomy.gbif import clean_vernacular, titlecase
from migratlas.taxonomy.index import load_seed


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Great White Shark", "Great White Shark"),
        # GBIF returns several alternatives in one field.
        ("Atlantic Bluefin Tuna, Northern Bluefin Tuna, Blue-fin Tunny", "Atlantic Bluefin Tuna"),
        # And sometimes a bracketed qualifier.
        ("Milkweed [butterfly]", "Milkweed"),
        ("Salmon (Atlantic)", "Salmon"),
        ("  spaced   out  ", "spaced out"),
        ("", ""),
    ],
)
def test_clean_vernacular(raw: str, expected: str) -> None:
    assert clean_vernacular(raw) == expected


def test_titlecase_does_not_mangle_apostrophes() -> None:
    """str.title() would give "Swainson'S Hawk"."""
    assert titlecase("swainson's hawk") == "Swainson's Hawk"
    assert titlecase("great white shark") == "Great White Shark"


def test_titlecase_leaves_existing_capitals_alone() -> None:
    assert titlecase("Mexican Free-tailed Bat") == "Mexican Free-tailed Bat"


# --- Seed list ---------------------------------------------------------------
def test_seed_realms_are_valid() -> None:
    for item in load_seed():
        Realm(item["realm"])


def test_seed_spans_every_realm() -> None:
    """The seed exists to break a bird-shaped design, which needs all four realms."""
    assert {item["realm"] for item in load_seed()} == {r.value for r in Realm}


def test_seed_spans_several_groups() -> None:
    groups = {item["group"] for item in load_seed()}
    assert len(groups) >= 5, f"only {groups} -- too narrow to catch taxon coupling"


def test_seed_names_are_unique() -> None:
    names = [item["name"] for item in load_seed()]
    assert len(names) == len(set(names))


def test_seed_entries_have_required_keys() -> None:
    for item in load_seed():
        assert {"name", "group", "realm"} <= set(item), item
