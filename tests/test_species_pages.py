"""The per-species pages, and the one thing they must never do.

The shape tests run always. The `PUBLISHED` ones read what was actually built, so CI enforces them
whenever the shards are committed -- which they are.
"""

import json
import re
from pathlib import Path
from typing import Any

import pytest

from migratlas.reports import species
from migratlas.reports.species import Row, SpeciesCard, Study
from migratlas.tiles.species import SHARDS

REPO = Path(__file__).resolve().parents[1]
PUBLIC = REPO / "web" / "public"
SHARD_FILES = sorted(PUBLIC.glob("species-study-*.json"))


def _study(**overrides: object) -> Study:
    fields: dict[str, object] = {
        "kind": "shift",
        "headline": "Something moved.",
        "value": "+0.100 °latitude per decade",
        "detail": "Across two surveys.",
        "caveat": "Or it did not.",
        "method": "docs/methods/phase1b-marine.md",
        "source_id": "fishglob",
    }
    fields.update(overrides)
    return Study(**fields)  # type: ignore[arg-type]


def _cards() -> list[Any]:
    # `Any`, because these are documents read off disk and every field is reached by name. A
    # TypedDict here would be a second declaration of the schema, in a test, drifting from the
    # dataclass that writes it -- which is the thing the dataclass exists to prevent.
    out: list[Any] = []
    for path in SHARD_FILES:
        out.extend(json.loads(path.read_text(encoding="utf-8"))["species"])
    return out


# --- Shape --------------------------------------------------------------------
def test_a_card_lands_in_the_shard_its_key_says(tmp_path: Path) -> None:
    """The surfaces shard on the same rule, so a mismatch fetches the wrong file for one of them."""
    cards = [
        SpeciesCard(taxon_key=key, scientific=f"T{key}", vernacular="", realm="marine", drawn=True)
        for key in (1, 65, 129, 2)
    ]
    species.write(cards, tmp_path)

    for key in (1, 65, 129, 2):
        shard = json.loads(
            (tmp_path / f"species-study-{key % SHARDS:02d}.json").read_text(encoding="utf-8")
        )
        assert key in [card["taxon_key"] for card in shard["species"]]


def test_every_shard_is_written_even_when_empty(tmp_path: Path) -> None:
    """A missing shard is a 404 in the browser."""
    species.write([], tmp_path)
    assert len(list(tmp_path.glob("species-study-*.json"))) == SHARDS


def test_a_shard_is_written_in_a_stable_order(tmp_path: Path) -> None:
    """As the surfaces are: an unordered rebuild touches all 64 and hides the real change."""
    cards = [
        SpeciesCard(taxon_key=key, scientific="x", vernacular="", realm="marine", drawn=False)
        for key in (192, 64, 128)
    ]
    species.write(cards, tmp_path)
    shard = json.loads((tmp_path / "species-study-00.json").read_text(encoding="utf-8"))
    assert [card["taxon_key"] for card in shard["species"]] == [64, 128, 192]


@pytest.mark.parametrize(
    ("per_decade", "expected"),
    [(0.5, "north"), (-0.5, "south"), (0.0, "no clear movement"), (0.01, "no clear movement")],
)
def test_a_shift_smaller_than_the_floor_is_not_given_a_direction(
    per_decade: float, expected: str
) -> None:
    """Printing a sign on 0.01 degrees a decade invites a reader to read one."""
    assert species._direction(per_decade) == expected


# --- The published pages ------------------------------------------------------
@pytest.mark.skipif(not SHARD_FILES, reason="species pages not built")
def test_no_species_page_can_locate_an_animal() -> None:
    """The invariant this whole file exists for.

    A study page is prose about a result, and a result is not a position. Nothing here may carry a
    coordinate -- not for a withheld animal, and not for one the gate is happy to draw either,
    because the drawn surface is gridded and delayed and a page beside it that quoted a raw fix
    would undo that in the one place nobody would look for it.

    Latitude *per decade* is a rate, not a place, so the `shift` value is exempt by kind rather
    than by pattern -- the pattern would have to be loose enough to let it through and would then
    let a real coordinate through with it.
    """
    coordinate = re.compile(r"-?\d{1,3}\.\d{3,}")
    for card in _cards():
        for study in card["studies"]:
            if study["kind"] == "shift":
                continue
            prose = " ".join([study["headline"], study["value"], study["detail"], study["caveat"]])
            if study["kind"] == "occupancy":
                # Exempt by kind, like `shift`, and then checked harder rather than waved through.
                # Every number on an occupancy card is a probability or a difference of two, so it
                # lives in [-1, 1]; the atlas footprint is 22 to 35 degrees south, so any leaked
                # coordinate is far outside that. The bound is therefore *stronger* here than the
                # bare pattern, not weaker -- and the builder never reads a coordinate column.
                outside = [value for value in coordinate.findall(prose) if abs(float(value)) > 1]
                assert not outside, f"{card['scientific']} (occupancy) carries {outside!r}"
                continue
            found = coordinate.search(prose)
            assert not found, f"{card['scientific']} ({study['kind']}) carries {found.group(0)!r}"


@pytest.mark.skipif(not SHARD_FILES, reason="species pages not built")
def test_a_withheld_animal_has_a_page_that_says_so() -> None:
    """An absence explains nothing.

    The lake holds 174,443 wolf fixes and draws none. A page that skipped the wolf would read as a
    project with no wolves in it, which is the opposite of true.
    """
    withheld = [
        card for card in _cards() if any(study["kind"] == "withheld" for study in card["studies"])
    ]
    assert withheld, "nothing is published as withheld"
    names = {card["scientific"] for card in withheld}
    assert "Canis lupus" in names, names
    for card in withheld:
        [study] = [s for s in card["studies"] if s["kind"] == "withheld"]
        # Named, counted, and reasoned. A refusal with no rationale cannot be reviewed.
        assert "held back" in study["value"]
        assert len(study["caveat"]) > 80, study["caveat"]


@pytest.mark.skipif(not SHARD_FILES, reason="species pages not built")
def test_the_marine_pages_show_the_disagreement_the_null_claims() -> None:
    """`marine-null` says surveys disagree in direction. This is where a reader can see it.

    Until these rows were published the only number on the site was the median that averages them
    out, so the most interesting half of the finding had to be taken on trust.
    """
    shifts = [study for card in _cards() for study in card["studies"] if study["kind"] == "shift"]
    assert len(shifts) > 100, f"only {len(shifts)} species carry a shift"

    both_ways = [study for study in shifts if "and south in" in study["headline"]]
    assert both_ways, "no species is published as moving both ways"
    for study in both_ways[:20]:
        directions = {row["detail"].rsplit(", ", maxsplit=1)[-1] for row in study["rows"]}
        assert {"north", "south"} <= directions, directions


@pytest.mark.skipif(not SHARD_FILES, reason="species pages not built")
def test_every_page_carries_a_caveat_and_a_method_note_that_exists() -> None:
    """The same rule the claim ledger keeps, for the same reason."""
    for card in _cards():
        assert card["studies"], f"{card['scientific']} has no studies at all"
        for study in card["studies"]:
            assert study["caveat"].strip(), f"{card['scientific']}/{study['kind']} has no caveat"
            assert (REPO / study["method"]).is_file(), study["method"]


@pytest.mark.skipif(not SHARD_FILES, reason="species pages not built")
def test_a_species_with_no_result_says_so_rather_than_being_blank() -> None:
    """Most of the index is this: recorded somewhere, measured by nothing."""
    extent = [study for card in _cards() for study in card["studies"] if study["kind"] == "extent"]
    assert extent, "no extent-only pages, which cannot be right for 3,000 OBIS taxa"
    assert all("nothing here measures" in study["headline"] for study in extent[:50])


def test_a_row_is_a_survey_not_a_species() -> None:
    """A fallback that read a row label as a species name put a bottom-trawl programme on the
    Atlantic mackerel's page, so the name now travels on the study rather than being inferred."""
    card = SpeciesCard(
        taxon_key=7,
        scientific="",
        vernacular="",
        realm="marine",
        drawn=False,
        studies=[_study(taxon="Scomber scombrus", rows=[Row("NEUS-Fall", "+0.1", "57 years")])],
    )
    assert card.studies[0].taxon == "Scomber scombrus"
    assert card.studies[0].rows[0].label == "NEUS-Fall"
