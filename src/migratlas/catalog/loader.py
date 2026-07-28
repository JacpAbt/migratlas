"""Load the registry and gate ingest on it."""

from functools import lru_cache
from importlib import resources
from typing import Any

import yaml
from pydantic import TypeAdapter

from migratlas.catalog.models import Source
from migratlas.redact import admit_for_ingest

REGISTRY_FILE = "registry.yaml"

_ADAPTER = TypeAdapter(tuple[Source, ...])


class UnregisteredSourceError(KeyError):
    """A source was requested that the registry does not describe."""


@lru_cache(maxsize=1)
def load() -> dict[str, Source]:
    """Parse the registry, keyed by source id."""
    text = resources.files("migratlas.catalog").joinpath(REGISTRY_FILE).read_text(encoding="utf-8")
    raw: Any = yaml.safe_load(text)
    sources = _ADAPTER.validate_python(tuple(raw.get("sources", ())))

    by_id: dict[str, Source] = {}
    for source in sources:
        if source.id in by_id:
            msg = f"Duplicate source id in {REGISTRY_FILE}: {source.id!r}"
            raise ValueError(msg)
        by_id[source.id] = source
    return by_id


def get(source_id: str) -> Source:
    """Return a registered source, or explain that it must be registered first."""
    try:
        return load()[source_id]
    except KeyError as exc:
        known = ", ".join(sorted(load()))
        msg = (
            f"Source {source_id!r} is not in the registry. Add an entry to "
            f"catalog/{REGISTRY_FILE} first. Known sources: {known}"
        )
        raise UnregisteredSourceError(msg) from exc


def admit(source_id: str) -> Source:
    """Resolve a source and run the ingest gate over it.

    Every ingest adapter starts here. Being unable to name your source in the registry
    is the earliest and cheapest point at which to stop.
    """
    source = get(source_id)
    admit_for_ingest(
        source.id,
        sensitivity=source.default_sensitivity,
        licence=source.licence,
    )
    return source
