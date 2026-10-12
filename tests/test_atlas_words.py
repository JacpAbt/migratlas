"""The atlas's words: every plate has them, every count is the published one, nothing is markup.

ADR 0021 decision 10. A caption that types a count is the figure nobody checks, so the digits a
caption may carry are exactly the ones `reports/atlas.py` reads or states as its own.
"""

import json
import re
from pathlib import Path

import pytest

from migratlas.reports import atlas
from migratlas.reports.detectability import STATUSES
from migratlas.tiles.plates import PLATES

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "web" / "public" / "layers" / "manifest.json"


def _meta(layer: str) -> dict[str, object]:
    path = ROOT / "web" / "public" / "layers" / f"{layer}.meta.json"
    meta: dict[str, object] = json.loads(path.read_text(encoding="utf-8"))
    return meta


@pytest.fixture(autouse=True)
def _from_the_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(ROOT)


def test_every_plate_has_words_and_a_published_layer() -> None:
    document = atlas.build()
    named = [plate["name"] for plate in document["plates"]]
    assert named == [plate.name for plate in PLATES]
    layers = {layer["name"] for layer in json.loads(MANIFEST.read_text(encoding="utf-8"))}
    for plate in document["plates"]:
        assert plate["layer"] in layers, plate["name"]
        assert (ROOT / "web" / "public" / plate["map"]).exists(), plate["map"]


def test_a_caption_carries_only_the_counts_it_reads() -> None:
    radar, foxes = _meta("aerial-passage"), _meta("bylot-journeys")
    allowed = {
        str(atlas.FOOTPRINT_KM),
        str(atlas.NIGHT_HOURS),
        str(radar["stations"]),
        str(foxes["animals"]),
        str(foxes["segments"]),
        "0.01",
    }
    for plate in atlas.build()["plates"]:
        for field in ("lead", "caption", "under"):
            for number in re.findall(r"\d+(?:\.\d+)?", plate[field]):
                assert number in allowed, f"{plate['name']} {field} types {number}"


def test_the_counts_follow_the_layers() -> None:
    words = {plate.name: plate for plate in atlas.plates()}
    assert f"{_meta('bylot-journeys')['animals']} animals" in words["bylot"].under
    assert f"{_meta('aerial-passage')['stations']} weather radars" in words["north-america"].under


def test_no_markup_travels_in_the_prose() -> None:
    text = json.dumps(atlas.build(), ensure_ascii=False)
    assert "<" not in text
    assert "&" not in text


def test_a_plate_credits_its_maps_by_their_licence() -> None:
    plates = {plate["name"]: plate for plate in atlas.build()["plates"]}
    assert "CC BY 4.0" in plates["svalbard"]["credit"]
    assert "Open Government Licence – Canada" in plates["ya-ha-tinda"]["credit"]


def test_every_still_map_has_words_and_published_data() -> None:
    manifest = {layer["name"]: layer for layer in json.loads(MANIFEST.read_text(encoding="utf-8"))}
    stills = atlas.build()["stills"]
    for still in stills:
        assert (ROOT / "web" / "public" / still["data"]).exists(), still["data"]
        if still["name"] != atlas.DETECTABILITY:
            assert manifest[still["name"]]["format"] == "grid", still["name"]
    # Every published layer with no time in it has a still map, and nothing else does.
    timeless = {name for name, layer in manifest.items() if layer["kind"] == "surface"}
    assert {still["name"] for still in stills} == timeless | {atlas.DETECTABILITY}


def test_a_still_map_types_no_count() -> None:
    for still in atlas.build()["stills"]:
        for field in ("lead", "caption", "title", "button"):
            assert not re.search(r"\d", still[field]), f"{still['name']} {field} types a number"


def test_a_still_map_keys_every_mark_it_draws() -> None:
    stills = {still["name"]: still for still in atlas.build()["stills"]}
    assessed = [row["value"] for row in stills[atlas.DETECTABILITY]["key"]]
    assert sorted(assessed) == sorted(STATUSES)
    assert assessed[0] == "detectable"
    assert [row["value"] for row in stills["atlas-taxa-change"]["key"]] == ["gain", "loss"]
    for still in stills.values():
        assert still["unit"] or still["key"], f"{still['name']} has neither a unit nor a key"


def test_a_still_map_states_the_terms_it_was_published_under() -> None:
    manifest = {layer["name"]: layer for layer in json.loads(MANIFEST.read_text(encoding="utf-8"))}
    for still in atlas.build()["stills"]:
        if still["name"] == atlas.DETECTABILITY:
            assert "no upstream licence" in still["credit"]
            continue
        assert manifest[still["name"]]["licence"] in still["credit"], still["name"]
        assert str(_meta(still["name"])["dwc:dataGeneralizations"]) in still["credit"]


def test_the_committed_document_is_current() -> None:
    committed = json.loads((ROOT / atlas.DOCUMENT).read_text(encoding="utf-8"))
    assert committed == json.loads(json.dumps(atlas.build()))
