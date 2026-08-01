"""The starter taxon list, kept as a fixture rather than as a build input.

It used to be the frontend's search index. `tiles/species.py` now builds that from what was
actually published, so a search hit always has a surface behind it -- something a hand-written list
of thirty animals could not promise, and the reason this stopped being a build step.

What it is still worth having is what it was chosen to be: the smallest set of animals that would
break a bird-shaped design, spanning every realm and several very different body plans.
`tests/test_taxonomy.py` reads it for exactly that.
"""

from importlib import resources
from typing import Any

import yaml

SEED_FILE = "seed_taxa.yaml"


def load_seed() -> list[dict[str, str]]:
    """Read the seed list shipped inside the package."""
    text = resources.files("migratlas.taxonomy").joinpath(SEED_FILE).read_text(encoding="utf-8")
    raw: Any = yaml.safe_load(text)
    if not isinstance(raw, list):
        msg = f"{SEED_FILE} must contain a list of taxa"
        raise TypeError(msg)
    return raw
