"""Structural guard: no taxon-specific identifiers in the core.

The failure mode is nobody's decision — one bird-shaped helper that looks harmless,
then another, until the "generic" metric layer only works for things with feathers.
So the guarantee is mechanical rather than cultural.

Checks identifiers, not comments or docstrings: naming radar as an example of an
evidence type is documentation, not coupling. ``ingest/`` and ``models/`` are exempt
because an adapter is *supposed* to know what its source measures — that is precisely
why the core can stay clean.
"""

import ast
import re
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src" / "migratlas"

GUARDED_PACKAGES = (
    "catalog",
    "drivers",
    "evidence",
    "features",
    "lake",
    "metrics",
    "taxonomy",
    "tiles",
)
GUARDED_MODULES = ("redact.py", "config.py")

# Word-level, not substring: "bat" must not match "probability", and "fish" must
# not match "finish".
BANNED_WORDS = frozenset(
    {
        "avian",
        "bat",
        "bats",
        "bird",
        "birds",
        "seabird",
        "seabirds",
        "ebird",
        "flyway",
        "ornithology",
        "ornithological",
        "passerine",
        "passerines",
        "raptor",
        "raptors",
        "stork",
        "storks",
        "nexrad",
        "shark",
        "sharks",
        "whale",
        "whales",
        "turtle",
        "turtles",
        "mammal",
        "mammals",
        "insect",
        "insects",
        "fish",
        "ungulate",
        "ungulates",
    }
)

_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def _words(identifier: str) -> set[str]:
    """Split an identifier into lowercase words.

    ``station_longitude`` -> {station, longitude}; ``BirdFlowModel`` -> {bird, flow, model}.
    """
    parts: list[str] = []
    for chunk in identifier.split("_"):
        parts.extend(_CAMEL.split(chunk))
    return {p.lower() for p in parts if p}


def _guarded_files() -> list[Path]:
    files: list[Path] = []
    for package in GUARDED_PACKAGES:
        files.extend(sorted((SRC / package).rglob("*.py")))
    files.extend(SRC / module for module in GUARDED_MODULES)
    return [f for f in files if f.exists()]


def _identifiers(tree: ast.AST) -> set[str]:
    """Collect every identifier a module defines, references or imports.

    Excludes string constants, so ``quantity == "birds_per_km3"`` in an adapter is
    not flagged -- but a ``def count_birds()`` in the core is.
    """
    found: set[str] = set()
    for node in ast.walk(tree):
        match node:
            case ast.Name(id=name):
                found.add(name)
            case ast.Attribute(attr=attr):
                found.add(attr)
            case ast.FunctionDef(name=name) | ast.AsyncFunctionDef(name=name):
                found.add(name)
            case ast.ClassDef(name=name):
                found.add(name)
            case ast.arg(arg=name):
                found.add(name)
            case ast.keyword(arg=str() as name):
                found.add(name)
            case ast.alias(name=name, asname=asname):
                found.add(name)
                if asname:
                    found.add(asname)
            case ast.ImportFrom(module=str() as module):
                found.add(module)
            case _:
                continue
    return found


def test_there_is_something_to_guard() -> None:
    """A guard that silently scans nothing passes forever."""
    files = _guarded_files()
    assert files, f"no guarded modules found under {SRC}"


@pytest.mark.parametrize("path", _guarded_files(), ids=lambda p: str(p.name))
def test_core_module_has_no_taxon_specific_identifiers(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    offenders: dict[str, set[str]] = {}
    for identifier in _identifiers(tree):
        hits = _words(identifier) & BANNED_WORDS
        if hits:
            offenders[identifier] = hits
    assert not offenders, (
        f"{path.relative_to(SRC)} contains taxon-specific identifiers: {offenders}. "
        f"The core dispatches on EvidenceType and Realm, never on taxon -- "
        f"source-specific logic belongs in ingest/."
    )


def test_word_splitter_does_not_false_positive() -> None:
    """The guard is only useful if it is precise enough to be left switched on."""
    assert "bat" not in _words("probability")
    assert "fish" not in _words("finish_time")
    assert "bird" not in _words("third_party")
    # And still catches the real thing.
    assert "bird" in _words("bird_count")
    assert "bird" in _words("BirdFlowModel")
    assert "nexrad" in _words("nexrad_station")
