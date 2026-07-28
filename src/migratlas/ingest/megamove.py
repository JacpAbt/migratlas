"""MegaMove: global space use of marine megafauna on a 1-degree grid.

Derived products only -- counts of tracked individuals per cell, not raw tracks -- so the
aggregation the ethics gate would otherwise impose has already been applied upstream.

Dryad gates downloads behind a bearer token, so the archives are operator-placed. The
published SHA-256 is still verified, so provenance is no weaker than an automated fetch.

The grid's species columns are common names mangled into identifiers
(``Baraus_petrel_nind``), while GBIF matches scientific names. Supplementary Table 2 in the
same dataset carries the authors' own common-to-scientific crosswalk, which is the
authority used here rather than a fuzzy vernacular lookup.
"""

import csv
import io
import json
import logging
import re
import unicodedata
import zipfile
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Final

import polars as pl

from migratlas.catalog import loader as catalog
from migratlas.config import get_settings
from migratlas.evidence import EvidenceType, Realm, TaxonScope, spec_for
from migratlas.ingest.http import Checksum, require_local
from migratlas.lake.writer import write_evidence
from migratlas.taxonomy import gbif

if TYPE_CHECKING:
    from pathlib import Path

    import pyarrow as pa

    from migratlas.lake.writer import WriteResult

log = logging.getLogger(__name__)

SOURCE_ID: Final = "megamove"

GRID_ARCHIVE: Final = "1_Tracked_Individuals.zip"
TABLES_ARCHIVE: Final = "5_Supplementary_Tables.zip"

CHECKSUMS: Final[dict[str, Checksum]] = {
    GRID_ARCHIVE: Checksum(
        "sha-256", "5bc20daddd126e2083536af395926a89c6ea1152fd78905dd50f8e6b9af368aa"
    ),
    TABLES_ARCHIVE: Checksum(
        "sha-256", "16b6a5064a86bce93f1b6e8acec6cde4fce5e64a3ea7a62cb9107c51f730e3ab"
    ),
}

INSTRUCTIONS: Final = (
    "Dryad requires an authenticated session, so this file cannot be fetched "
    "automatically. Download it from https://datadryad.org/dataset/doi:10.5061/"
    "dryad.x95x69ptv and place it anywhere under the directory above -- the loader "
    "searches recursively, so Dryad's own folder name is fine."
)

SPECIES_GRID: Final = "numberindivs_total_perspecies_1deg.csv"
TAXA_GRID: Final = "numberindivs_pertaxa_1deg.csv"
CELL_SIZE_DEG: Final = 1.0

# The study pools tracks from 1985-2018 into one static surface, so every row shares this
# period. It is not a time series and must not be read as one.
PERIOD_START: Final = datetime(1985, 1, 1, tzinfo=UTC)
PERIOD_END: Final = datetime(2018, 12, 31, tzinfo=UTC)

# Grid column names that the crosswalk spells differently. Each was confirmed by a 1:1
# residual pairing: after normalisation, exactly these 11 columns and exactly these 11
# crosswalk entries were left over, so every entry is consumed once.
#
# Two are worth flagging. "Northern right whale" is used here for the North Atlantic
# species rather than the North Pacific one, and "Sandtiger shark" maps to the smalltooth
# sand tiger rather than the more commonly meant Carcharias taurus. Both follow the
# paper's own species list, which is the authority for its own grid.
ALIASES: Final[dict[str, str]] = {
    "adelie penguin": "ad lie penguin",
    "beluga whale": "beluga",
    "common thresher shark": "common thresher",
    "harbour seal": "harbor seal",
    "long nosed fur seal": "long nosed new zealand fur seal",
    "northern right whale": "north atlantic right whale",
    "pelagic thresher shark": "pelagic thresher",
    "red tailed tropic bird": "red tailed tropicbird",
    "ross gull": "rosss gull",
    "sandtiger shark": "smalltooth sand tiger shark",
    "white tailed tropic bird": "white tailed tropicbird",
}


# Straight quote, right single quotation mark, modifier letter apostrophe. Matched by
# codepoint so the source carries no visually ambiguous glyphs.
APOSTROPHES: Final[frozenset[int]] = frozenset({0x27, 0x2019, 0x02BC})


class CrosswalkError(RuntimeError):
    """The grid's species columns could not be reconciled with the crosswalk."""


def normalise(name: str) -> str:
    """Fold a common name to a comparable key.

    Accents and apostrophes are removed rather than replaced, because the grid headers
    dropped both: "Audouin's gull" has to fold to the same key as ``Audouins_gull``.
    """
    decomposed = unicodedata.normalize("NFKD", name)
    ascii_only = "".join(c for c in decomposed if not unicodedata.combining(c))
    ascii_only = "".join(c for c in ascii_only if ord(c) not in APOSTROPHES)
    return re.sub(r"[^a-z0-9]+", " ", ascii_only.lower()).strip()


def _member(archive: Path, suffix: str) -> bytes:
    """Read the single archive member whose name ends with ``suffix``."""
    with zipfile.ZipFile(archive) as zf:
        names = [n for n in zf.namelist() if n.endswith(suffix)]
        if len(names) != 1:
            msg = f"Expected exactly one member ending {suffix!r} in {archive.name}, got {names}"
            raise CrosswalkError(msg)
        return zf.read(names[0])


def load_crosswalk(tables_archive: Path) -> dict[str, str]:
    """Common name -> scientific name, from the authors' Supplementary Table 2."""
    with zipfile.ZipFile(tables_archive) as zf:
        member = next((n for n in zf.namelist() if "Table 2" in n and n.endswith(".csv")), None)
        if member is None:
            msg = f"Supplementary Table 2 not found in {tables_archive.name}"
            raise CrosswalkError(msg)
        rows = list(csv.reader(io.StringIO(zf.read(member).decode("utf-8", "replace"))))

    start = next(
        (i for i, r in enumerate(rows) if r and r[0].strip().lower().startswith("scientific")),
        None,
    )
    if start is None:
        msg = "Supplementary Table 2 has no 'Scientific Names' header row"
        raise CrosswalkError(msg)

    crosswalk: dict[str, str] = {}
    scientific_and_common = 2
    for row in rows[start + 1 :]:
        if len(row) >= scientific_and_common and row[0].strip() and row[1].strip():
            crosswalk.setdefault(normalise(row[1]), row[0].strip())
    return crosswalk


def resolve_species_columns(columns: list[str], crosswalk: dict[str, str]) -> dict[str, str]:
    """Map each ``*_nind`` grid column to a scientific name.

    Refuses to proceed on any unresolved column. A silently dropped species would be very
    hard to notice later, and a guessed one would put counts under the wrong animal.
    """
    resolved: dict[str, str] = {}
    unresolved: list[str] = []
    for column in columns:
        key = normalise(column.removesuffix("_nind"))
        key = ALIASES.get(key, key)
        scientific = crosswalk.get(key)
        if scientific is None:
            unresolved.append(column)
        else:
            resolved[column] = scientific

    if unresolved:
        msg = (
            f"{len(unresolved)} grid columns could not be resolved to a scientific name: "
            f"{unresolved}. Add an entry to ALIASES rather than letting them drop."
        )
        raise CrosswalkError(msg)
    return resolved


def taxon_keys(scientific_names: list[str]) -> dict[str, int]:
    """Resolve scientific names to GBIF Backbone keys, cached between runs.

    Cached because this is ~111 lookups against a public API for data that changes on the
    order of years, and an ingest should not be rude to GBIF on every re-run.
    """
    cache = get_settings().cache_dir / f"{SOURCE_ID}_taxon_keys.json"
    known: dict[str, int] = {}
    if cache.exists():
        known = {str(k): int(v) for k, v in json.loads(cache.read_text(encoding="utf-8")).items()}

    missing = [name for name in scientific_names if name not in known]
    if missing:
        log.info("resolving %d scientific names against the GBIF Backbone", len(missing))
        with gbif.client() as http:
            for name in missing:
                try:
                    known[name] = gbif.match_name(http, name).usage_key
                except (gbif.TaxonomyError, OSError) as exc:
                    log.warning("unresolved taxon %r: %s", name, exc)
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(known, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    return known


def _grid(archive: Path, suffix: str) -> pl.DataFrame:
    return pl.read_csv(io.BytesIO(_member(archive, suffix)))


def to_evidence(
    species_grid: pl.DataFrame,
    taxa_grid: pl.DataFrame,
    resolved: dict[str, str],
    keys: dict[str, int],
) -> pa.Table:
    """Reshape both grids into ABUNDANCE_SURFACE rows.

    Per-species rows carry ``TaxonScope.EXACT`` with a GBIF key; per-taxon rows carry
    ``AGGREGATE`` with a group label and no key, because "Cetaceans" is not a taxon key.
    """
    species = (
        species_grid.unpivot(
            index=["Latitude", "Longitude"],
            on=list(resolved),
            variable_name="column",
            value_name="value",
        )
        .with_columns(scientific=pl.col("column").replace_strict(resolved))
        .with_columns(
            taxon_key=pl.col("scientific").replace_strict(keys, default=None, return_dtype=pl.Int64)
        )
        .with_columns(
            taxon_scope=pl.lit(TaxonScope.EXACT.value),
            taxon_label=pl.col("scientific"),
        )
        .drop("column", "scientific")
    )

    taxon_columns = [c for c in taxa_grid.columns if c.endswith("_nind")]
    taxa = (
        taxa_grid.unpivot(
            index=["Latitude", "Longitude"],
            on=taxon_columns,
            variable_name="column",
            value_name="value",
        )
        .with_columns(
            taxon_key=pl.lit(None, dtype=pl.Int64),
            taxon_scope=pl.lit(TaxonScope.AGGREGATE.value),
            taxon_label=pl.col("column").str.replace("_nind$", "").str.replace_all("_", " "),
        )
        .drop("column")
    )

    # Species rows whose taxon failed to resolve would violate the gate's rule that an
    # EXACT claim must carry a key, so they are dropped loudly rather than published.
    unresolved = species.filter(pl.col("taxon_key").is_null())["taxon_label"].unique().to_list()
    if unresolved:
        log.warning("dropping %d species with no GBIF key: %s", len(unresolved), unresolved)
        species = species.filter(pl.col("taxon_key").is_not_null())

    combined = pl.concat([species, taxa], how="vertical_relaxed").filter(
        pl.col("value").is_not_null()
    )

    frame = combined.select(
        source_id=pl.lit(SOURCE_ID),
        realm=pl.lit(Realm.MARINE.value),
        taxon_scope=pl.col("taxon_scope"),
        taxon_key=pl.col("taxon_key"),
        taxon_label=pl.col("taxon_label"),
        cell_longitude=pl.col("Longitude").cast(pl.Float64),
        cell_latitude=pl.col("Latitude").cast(pl.Float64),
        cell_size_deg=pl.lit(CELL_SIZE_DEG, dtype=pl.Float64),
        period_start=pl.lit(PERIOD_START).cast(pl.Datetime("ms", time_zone="UTC")),
        period_end=pl.lit(PERIOD_END).cast(pl.Datetime("ms", time_zone="UTC")),
        value=pl.col("value").cast(pl.Float64),
        # Counts of tracked individuals, so this measures research effort as much as
        # animal distribution. Never sum it against a relative-abundance surface.
        value_kind=pl.lit("tracked_individuals"),
        value_lower=pl.lit(None, dtype=pl.Float64),
        value_upper=pl.lit(None, dtype=pl.Float64),
    )
    schema = spec_for(EvidenceType.ABUNDANCE_SURFACE).schema
    return frame.select(schema.names).to_arrow().cast(schema)


def ingest() -> WriteResult:
    """Reshape the operator-placed archives and land them. Idempotent."""
    source = catalog.admit(SOURCE_ID)
    log.info("ingesting %s (%s)", source.title, source.licence)

    grid_archive = require_local(
        SOURCE_ID, GRID_ARCHIVE, checksum=CHECKSUMS[GRID_ARCHIVE], instructions=INSTRUCTIONS
    )
    tables_archive = require_local(
        SOURCE_ID, TABLES_ARCHIVE, checksum=CHECKSUMS[TABLES_ARCHIVE], instructions=INSTRUCTIONS
    )

    species_grid = _grid(grid_archive, SPECIES_GRID)
    taxa_grid = _grid(grid_archive, TAXA_GRID)
    crosswalk = load_crosswalk(tables_archive)

    species_columns = [c for c in species_grid.columns if c.endswith("_nind")]
    resolved = resolve_species_columns(species_columns, crosswalk)
    log.info("%d species columns resolved to scientific names", len(resolved))

    keys = taxon_keys(sorted(set(resolved.values())))
    table = to_evidence(species_grid, taxa_grid, resolved, keys)
    log.info("%d evidence rows", table.num_rows)

    return write_evidence(table, spec_for(EvidenceType.ABUNDANCE_SURFACE), source_id=SOURCE_ID)
