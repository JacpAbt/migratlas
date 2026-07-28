"""Build the static species index the frontend searches."""

import json
from dataclasses import asdict, dataclass
from importlib import resources
from typing import TYPE_CHECKING, Any

import yaml

from migratlas.evidence import Realm
from migratlas.taxonomy import gbif

if TYPE_CHECKING:
    from pathlib import Path

SEED_FILE = "seed_taxa.yaml"


@dataclass(frozen=True, slots=True)
class IndexEntry:
    """One searchable row. Mirrors the TaxonEntry interface in web/src/search."""

    key: int
    scientific: str
    vernacular: str
    group: str
    realm: str


@dataclass(frozen=True, slots=True)
class BuildReport:
    entries: list[IndexEntry]
    unresolved: list[tuple[str, str]]
    """(name, reason) for each seed entry that could not be resolved."""


def load_seed() -> list[dict[str, str]]:
    """Read the seed list shipped inside the package."""
    text = resources.files("migratlas.taxonomy").joinpath(SEED_FILE).read_text(encoding="utf-8")
    raw: Any = yaml.safe_load(text)
    if not isinstance(raw, list):
        msg = f"{SEED_FILE} must contain a list of taxa"
        raise TypeError(msg)
    return raw


def build(*, limit: int | None = None) -> BuildReport:
    """Resolve every seed taxon against the GBIF Backbone.

    Unresolved names are reported rather than skipped silently: a species missing from
    the search box because a lookup failed months ago is hard to notice.
    """
    seed = load_seed()[:limit]
    entries: list[IndexEntry] = []
    unresolved: list[tuple[str, str]] = []

    with gbif.client() as http:
        for item in seed:
            name = item["name"]
            realm = Realm(item["realm"])
            try:
                match = gbif.match_name(http, name)
            except (gbif.TaxonomyError, OSError) as exc:
                unresolved.append((name, str(exc)))
                continue

            # A curated override wins. GBIF's vernacular field is occasionally just
            # wrong -- it gives "Blue-back" for sockeye salmon -- and a hand-checked
            # name in the seed file is more honest than a heuristic that guesses right
            # most of the time.
            vernacular = (
                item.get("common")
                or gbif.vernacular_name(http, match.usage_key)
                or match.canonical_name
            )
            entries.append(
                IndexEntry(
                    key=match.usage_key,
                    scientific=match.canonical_name,
                    vernacular=vernacular,
                    group=item["group"],
                    realm=realm.value,
                )
            )

    entries.sort(key=lambda e: (e.group, e.vernacular))
    return BuildReport(entries=entries, unresolved=unresolved)


def write(report: BuildReport, destination: Path) -> int:
    """Write the index as JSON. Returns bytes written."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps([asdict(e) for e in report.entries], ensure_ascii=False, indent=1)
    destination.write_text(payload + "\n", encoding="utf-8")
    return len(payload)
