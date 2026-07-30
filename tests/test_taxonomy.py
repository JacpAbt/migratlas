"""Taxonomy helpers. The name-cleaning cases are all real GBIF responses."""

import httpx
import pytest

from migratlas.evidence import Realm
from migratlas.taxonomy.gbif import (
    TaxonomyError,
    clean_vernacular,
    match_name,
    titlecase,
)
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


# --- Name resolution --------------------------------------------------------
# Real /species/match payloads, trimmed to the fields match_name reads.
def _stub(payload: dict[str, object]) -> httpx.Client:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    return httpx.Client(transport=httpx.MockTransport(handler), base_url="https://example.invalid")


def test_a_synonym_resolves_to_the_accepted_usage() -> None:
    """The Backbone is a spine, so it has to answer with the taxon and not with the name.

    SABAP1 calls the black saw-wing `Psalidoprocne holomelas`, which GBIF holds as a synonym of the
    subspecies `Psalidoprocne pristoptera holomelas`. Returning the synonym's own key would give a
    second source that used the current name a different key for the same bird, and a join across
    the two would lose the species without failing.
    """
    with _stub(
        {
            "usageKey": 2489155,
            "acceptedUsageKey": 5846393,
            "status": "SYNONYM",
            "rank": "SPECIES",
            "matchType": "EXACT",
            "confidence": 98,
            "scientificName": "Psalidoprocne holomelas (Sundevall, 1850)",
            "canonicalName": "Psalidoprocne holomelas",
        }
    ) as http:
        match = match_name(http, "Psalidoprocne holomelas")

    assert match.usage_key == 5846393
    # The status still reports what was asked about, so the substitution stays auditable.
    assert match.status == "SYNONYM"
    assert match.is_synonym


def test_an_accepted_name_keeps_its_own_key() -> None:
    with _stub(
        {
            "usageKey": 2480689,
            "status": "ACCEPTED",
            "rank": "SPECIES",
            "matchType": "EXACT",
            "confidence": 99,
            "scientificName": "Hieraaetus ayresii (Gurney, 1862)",
            "canonicalName": "Hieraaetus ayresii",
        }
    ) as http:
        match = match_name(http, "Hieraaetus ayresii")

    assert match.usage_key == 2480689
    assert not match.is_synonym


def test_a_genus_match_is_refused_rather_than_returned_as_a_species() -> None:
    """What SABAP1's six unresolved names ran into: GBIF answers with the genus, confidently."""
    with (
        _stub(
            {
                "usageKey": 2480498,
                "status": "ACCEPTED",
                "rank": "GENUS",
                "matchType": "HIGHERRANK",
                "confidence": 95,
                "scientificName": "Aquila Brisson, 1760",
                "canonicalName": "Aquila",
            }
        ) as http,
        pytest.raises(TaxonomyError, match="HIGHERRANK"),
    ):
        match_name(http, "Aquila ayresii")
