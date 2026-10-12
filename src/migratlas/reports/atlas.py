"""The atlas's words: titles, callouts, captions and the running readout, rendered verbatim.

ADR 0021 decision 10. The world chapter becomes a drawn atlas, and what it says about each mark --
what a pen stroke stands for, why a fox line has no date, why a herd's flick is not a path -- is the
part of it most likely to be wrong, so it is written here, once, beside the numbers it quotes.

**Every count in a caption is read from what is published**: the radars and the foxes from their
layers' metadata, a herd's cell from the spec that built it, a plate's credits from the registry.
Two figures are this file's own, and both say so where a reader meets them: the 50 km a radar's
profile reaches (the source's, recorded in `docs/PLAN.md`) and the eight hours a stroke is carried
-- an assumption, made so a stroke reads as a night's flight rather than a tuft round a radar.

What a caption does not repeat is the layer's own description and its generalisation, which the
manifest and the layer's metadata already carry and the atlas prints beside it. A caption is what
the *mark* means; the description is what the *data* is. The same holds for the still maps (decision
7), whose terms -- whose data, which licence, how generalised -- are read from each layer's metadata
and the registry, except the detectability map's, which is this project's own report and says so.

Plain text, as every published document here is: a caption's `lead` is the clause the atlas sets
in bold and runs into the rest, so no markup travels in the prose.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from migratlas.catalog import loader as catalog
from migratlas.tiles.plates import PLATES
from migratlas.tiles.presence import PRESENCE_LAYERS

SCHEMA_VERSION: Final = 1

PUBLIC: Final = Path("web/public")
LAYERS: Final = PUBLIC / "layers"
DOCUMENT: Final = PUBLIC / "atlas.json"

FOOTPRINT_KM: Final = 50
"""How far from a radar its profile describes the air: 100 m bins within 50 km (`docs/PLAN.md`)."""
NIGHT_HOURS: Final = 8
"""How long a stroke carries what a radar saw. An assumption, and the caption says so."""

COMPASS: Final = (
    "north",
    "north-east",
    "east",
    "south-east",
    "south",
    "south-west",
    "west",
    "north-west",
)


@dataclass(frozen=True, slots=True)
class PlateWords:
    """What one plate says: its name in the list, on the map, over it, and under it."""

    name: str
    layer: str
    button: str
    title: str
    callout: str
    under: str
    lead: str
    caption: str
    clock: str


def _meta(layer: str) -> dict[str, Any]:
    meta: dict[str, Any] = json.loads((LAYERS / f"{layer}.meta.json").read_text(encoding="utf-8"))
    return meta


def _cell(layer: str) -> str:
    """A herd's cell, as the spec that built it states it."""
    spec = next(spec for spec in PRESENCE_LAYERS if spec.name == layer)
    return f"{spec.cell_deg:g}"


def credit(source_ids: list[str]) -> str:
    """Whose map a plate is drawn on, from the registry: what CC BY and the OGL ask for."""
    parts = []
    for source_id in source_ids:
        source = catalog.get(source_id)
        parts.append(f"{source.title} ({source.licence})")
    return "Map: " + "; ".join(parts) + "."


def plates() -> list[PlateWords]:
    """The four plates' words, in the order the atlas lists them."""
    radar = _meta("aerial-passage")
    foxes = _meta("bylot-journeys")
    herd = (
        "were recorded that week, the dashed ones the weeks before. Each stroke joins a place "
        "reached this week to the nearest place held the week before: the shift between two weekly "
        "maps, not an animal's path. One {cell}° cell is the unit, so an animal crossing three "
        "cells is in all three."
    )
    return [
        PlateWords(
            name="north-america",
            layer="aerial-passage",
            button="all that flies by night",
            title="The night sky over North America",
            callout="all that flies by night",
            under=f"{radar['stations']} weather radars · not one species",
            lead="Each stroke is one night's flight",
            caption=(
                "of what a weather radar saw above it that week: it starts in the air the radar "
                f"sampled, within {FOOTPRINT_KM} km of it, and runs on at the heading and ground "
                f"speed the radar measured, carried for {NIGHT_HOURS} hours — an assumption, so a "
                "stroke reads as a flight. More strokes, more of it. Not one night and not one "
                "kind of animal: the radar cannot tell birds from bats from insects."
            ),
            clock="year",
        ),
        PlateWords(
            name="bylot",
            layer="bylot-journeys",
            button="Arctic fox",
            title="Arctic foxes from Bylot Island",
            callout="Arctic foxes",
            under=f"{foxes['animals']} animals, a position a day",
            lead=f"Each line is one of {foxes['segments']} journeys",
            caption=(
                f"by {foxes['animals']} foxes, drawn a day at a time from its daily median "
                "position, the red nib where it has got to in its own journey. All of them start "
                "together on day one: the published tracks carry no dates, so this is no one "
                "season. A few journeys run off the plate."
            ),
            clock="journey",
        ),
        PlateWords(
            name="svalbard",
            layer="svalbard-herd",
            button="Svalbard reindeer",
            title="Svalbard reindeer",
            callout="Svalbard reindeer",
            under="the herd's year, week by week",
            lead="The inked outline is where collared reindeer",
            caption=herd.format(cell=_cell("svalbard-herd")),
            clock="year",
        ),
        PlateWords(
            name="ya-ha-tinda",
            layer="yahatinda-herd",
            button="elk",
            title="The Ya Ha Tinda elk, Alberta",
            callout="elk, the Ya Ha Tinda herd",
            under="the herd's year, week by week",
            lead="The inked outline is where collared elk",
            caption=herd.format(cell=_cell("yahatinda-herd")),
            clock="year",
        ),
    ]


@dataclass(frozen=True, slots=True)
class StillWords:
    """What one still map says: its name in the list, its title over the map, and what a mark is."""

    name: str
    button: str
    title: str
    lead: str
    caption: str
    unit: str
    """What a dot counts, beside the key's sample dots. Empty where the key is categories."""
    key: tuple[tuple[str, str], ...]
    """Each kind of mark and what it means, in the order the key lists them."""


DETECTABILITY: Final = "detectability"
"""The one still map that is a report about the lake rather than a published layer."""

DETECTABILITY_CREDIT: Final = (
    "Worked out by this project from every source it holds, so no upstream licence applies; the "
    "finest thing it states about anywhere is a one-degree cell."
)


def stills() -> list[StillWords]:
    """The four maps with no time in them (ADR 0021 decision 7), in the order the atlas lists them.

    The detectability key is in `STATUSES`' order reversed, best first, because the share a reader
    looks for is how much of the world a change could be measured in at all.
    """
    return [
        StillWords(
            name="marine-space-use",
            button="where tracked sea animals went",
            title="Where tracked sea animals went",
            lead="Each dot is a one-degree cell where tracked animals were.",
            caption=(
                "The more of them, the larger the dot, over the whole period at once and on a "
                "logarithmic scale, so a cell with a thousand is not drawn a thousand times the "
                "size of one. It shows where animals were tagged and followed, which is where "
                "researchers worked, as much as where animals go."
            ),
            unit="tracked animals",
            key=(),
        ),
        StillWords(
            name="marine-taxa-recorded",
            button="kinds of sea animal recorded",
            title="How many kinds of sea animal have been recorded",
            lead=(
                "Each dot is a one-degree cell, larger where more kinds of moving sea animal have "
                "at least one record."
            ),
            caption=(
                "It counts what people have seen and reported, so the busiest cells are the best "
                "surveyed, and a blank cell is one with no record of these animals, not one with "
                "nothing in it."
            ),
            unit="kinds recorded",
            key=(),
        ),
        StillWords(
            name="atlas-taxa-change",
            button="southern Africa's two atlases",
            title="Southern Africa's two atlases: more kinds recorded, or fewer",
            lead=(
                "A solid dot is a quarter-degree cell where the second atlas recorded more kinds "
                "than the first, a ring one where it recorded fewer."
            ),
            caption=(
                "The larger the mark, the larger the change. Drawn enlarged in the box, because "
                "the whole region is a few pixels wide on the world. A before and an after, not a "
                "trend, and a hole is a place nobody atlassed twice."
            ),
            unit="",
            key=(("gain", "more kinds recorded"), ("loss", "fewer kinds recorded")),
        ),
        StillWords(
            name=DETECTABILITY,
            button="where a change can be measured",
            title="Where a change could be measured at all",
            lead=(
                "Inked where some source has a long enough series with its effort measured, "
                "pencilled where something stops it."
            ),
            caption=(
                "Inked does not mean a change was found, only that one could be, and a blank place "
                "is one the records say nothing about."
            ),
            unit="",
            key=(
                ("detectable", "a long enough series, with effort accounted for"),
                ("too-short", "a repeated protocol, not yet long enough"),
                ("effort-not-measured", "records, but no measure of how hard anyone looked"),
                ("no-time-axis", "one pooled period, nothing to trend"),
            ),
        ),
    ]


def terms(layer: str) -> str:
    """What a still layer was published under: whose data, its licence and its generalisation."""
    meta = _meta(layer)
    source = catalog.get(str(meta["source_id"]))
    return f"Data: {source.title} ({source.licence}). {meta['dwc:dataGeneralizations']}"


def build() -> dict[str, Any]:
    """The whole document, in the shape `web/src/lib/atlas/words.ts` reads."""
    by_name = {plate.name: plate for plate in PLATES}
    return {
        "schema_version": SCHEMA_VERSION,
        "world": {
            "title": "Where things move, through a year",
            "lead": "Choose one to look closer.",
            "caption": (
                "The weather radars' night sky, three tracked animals, the sea ice's edge and the "
                "green wave, each through its own year."
            ),
            "still": (
                "A still map has one value for each place over its whole period, so it does not "
                "move with the clock."
            ),
            "readout": "choose one to look closer",
        },
        "plates": [
            {
                "name": words.name,
                "layer": words.layer,
                "button": words.button,
                "title": words.title,
                "callout": words.callout,
                "under": words.under,
                "lead": words.lead,
                "caption": words.caption,
                "clock": words.clock,
                "frame": list(by_name[words.name].frame),
                "centre": list(by_name[words.name].centre),
                "map": f"basemap/plates/{words.name}.geojson",
                "credit": credit(
                    sorted(
                        {
                            by_name[words.name].land,
                            *filter(None, [by_name[words.name].rivers]),
                        }
                    )
                ),
            }
            for words in plates()
        ],
        "stills": [
            {
                "name": words.name,
                "button": words.button,
                "title": words.title,
                "lead": words.lead,
                "caption": words.caption,
                "unit": words.unit,
                "key": [{"value": value, "means": means} for value, means in words.key],
                "data": (
                    "detectability.json"
                    if words.name == DETECTABILITY
                    else f"layers/{words.name}.grid.json"
                ),
                "credit": DETECTABILITY_CREDIT
                if words.name == DETECTABILITY
                else terms(words.name),
            }
            for words in stills()
        ],
        # Fragments the atlas puts its numbers between, rather than templates: a brace in shipped
        # prose is the bug `tests/test_published_prose.py` exists for, and it does not ask why.
        "readout": {
            "air": {
                "little": "little in the air",
                "fair": "a fair amount in the air",
                "great": "a great deal in the air",
                "heading": "most of it heading",
                "every_way": "heading every way",
                "compass": list(COMPASS),
            },
            "journey": {
                "day": "day",
                "each": "of each journey",
                "of": "of",
                "going": "still going",
            },
            "herd": {"in": "collared animals in", "cells": "cells", "reached": "newly reached"},
        },
        "controls": {
            "show": "show",
            "world": "the whole world",
            "pause": "pause",
            "play": "play",
            "slow": "slow",
            "normal": "normal",
            "fast": "fast",
            "clock": "time of year",
            "journey": "day of each journey",
            "stills": "still maps",
            "enlarged": "enlarged",
        },
    }


def write(document: dict[str, Any] | None = None) -> Path:
    """Render to `web/public/atlas.json`, sorted so a rebuild with no change is a no-op."""
    built = document if document is not None else build()
    DOCUMENT.write_text(json.dumps(built, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return DOCUMENT
