"""The atlas's words: every plate has them, every count is the published one, nothing is markup.

ADR 0021 decision 10. A caption that types a count is the figure nobody checks, so the digits a
caption may carry are exactly the ones `reports/atlas.py` reads or states as its own.
"""

import json
import re
from pathlib import Path

import pytest

from migratlas.reports import atlas
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


def test_the_committed_document_is_current() -> None:
    committed = json.loads((ROOT / atlas.DOCUMENT).read_text(encoding="utf-8"))
    assert committed == json.loads(json.dumps(atlas.build()))
