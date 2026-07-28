"""OBIS speciesgrids: gridded marine species distributions, fully automated.

Complements MegaMove, which needs a manual download. This source is public S3 with no
credentials, so it exercises the unattended path end to end.

Two things it is not. It is not a movement product -- each row is occurrence *records* in
an H3 cell across a year range, so it is distribution and sampling effort, not passage. And
it is not restricted to animals: the full product is 257k species across 43M cells,
dominated by gastropods, crustaceans and diatoms. Ingest is deliberately bounded to the
vertebrate and cephalopod classes a movement atlas can use, which is documented rather than
silent.

Species are keyed by WoRMS AphiaID upstream. The GBIF Backbone remains the project's
taxonomy spine, so names are resolved through it -- WoRMS is the crosswalk, per ADR and the
plan, not a second key space.
"""

import json
import logging
import re
import urllib.request
from typing import TYPE_CHECKING, Final

import duckdb
import polars as pl

from migratlas.catalog import loader as catalog
from migratlas.config import get_settings
from migratlas.evidence import EvidenceType, Realm, TaxonScope, spec_for
from migratlas.lake.writer import write_evidence
from migratlas.taxonomy import gbif

if TYPE_CHECKING:
    import pyarrow as pa

    from migratlas.lake.writer import WriteResult

log = logging.getLogger(__name__)

SOURCE_ID: Final = "obis_speciesgrids"

BUCKET: Final = "https://obis-products.s3.amazonaws.com"
PREFIX: Final = "speciesgrids/h3_7/"
CELL_SYSTEM: Final = "h3_7"

# Vertebrates and cephalopods only. Teleostei is deliberately excluded for now: it adds
# 27,000 species, and every one needs a Backbone lookup. It is the obvious next expansion,
# and the bound is stated in the registry caveats rather than hidden here.
MOVEMENT_CLASSES: Final[tuple[str, ...]] = (
    "Mammalia",
    "Aves",
    "Reptilia",
    "Testudines",
    "Elasmobranchii",
    "Holocephali",
    "Chondrichthyes",
    "Cephalopoda",
)


def part_urls() -> list[str]:
    """Enumerate the product's parts.

    The files carry no extension (``000``, ``001``, ...), so a ``*.parquet`` glob finds
    nothing and the bucket has to be listed.
    """
    request = urllib.request.Request(  # noqa: S310 -- fixed https URL, not user input
        f"{BUCKET}/?list-type=2&prefix={PREFIX}&max-keys=1000",
        headers={"User-Agent": "migratlas/0.1"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
        body = response.read().decode("utf-8")
    keys = [k for k in re.findall(r"<Key>([^<]+)</Key>", body) if not k.endswith("/")]
    if not keys:
        msg = f"No parts found under {BUCKET}/{PREFIX}"
        raise ValueError(msg)
    return [f"{BUCKET}/{key}" for key in keys]


def _connection() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    # spatial gives ST_Centroid for the cell polygons; httpfs reads the bucket over HTTPS.
    con.execute("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial;")
    return con


def read_slice(urls: list[str]) -> pl.DataFrame:
    """Read the movement-relevant classes, one row per species and cell.

    The part URLs come from parsing the bucket's XML listing, so they are external input and
    are bound as parameters rather than interpolated. ``class`` is quoted because it is a
    reserved word -- the same trap that ``order`` in this product and ``window`` in the radar
    product both set.
    """
    for url in urls:
        if not url.startswith(f"{BUCKET}/{PREFIX}"):
            msg = f"Refusing to read {url!r}: outside the expected prefix."
            raise ValueError(msg)

    con = _connection()
    arrow = con.execute(
        """
        SELECT
            species,
            AphiaID          AS aphia_id,
            "class"          AS taxon_class,
            records,
            min_year,
            max_year,
            cell,
            ST_X(ST_Centroid(geometry)) AS cell_longitude,
            ST_Y(ST_Centroid(geometry)) AS cell_latitude
        FROM read_parquet(?)
        WHERE list_contains(?, "class")
          AND species IS NOT NULL
          AND records > 0
        """,
        [urls, list(MOVEMENT_CLASSES)],
    ).arrow()
    frame = pl.from_arrow(arrow)
    if not isinstance(frame, pl.DataFrame):  # pragma: no cover -- defensive
        msg = "expected a DataFrame from the OBIS query"
        raise TypeError(msg)
    log.info("%d rows across %d species", frame.height, frame["species"].n_unique())
    return frame


def taxon_keys(names: list[str]) -> dict[str, int]:
    """Resolve scientific names to GBIF Backbone keys, cached between runs."""
    cache = get_settings().cache_dir / f"{SOURCE_ID}_taxon_keys.json"
    known: dict[str, int] = {}
    if cache.exists():
        known = {str(k): int(v) for k, v in json.loads(cache.read_text(encoding="utf-8")).items()}

    missing = [name for name in names if name not in known]
    if missing:
        log.info("resolving %d names against the GBIF Backbone (cached thereafter)", len(missing))
        with gbif.client() as http:
            for index, name in enumerate(missing, 1):
                try:
                    known[name] = gbif.match_name(http, name).usage_key
                except (gbif.TaxonomyError, OSError) as exc:
                    log.debug("unresolved %r: %s", name, exc)
                if index % 250 == 0:
                    log.info("  resolved %d/%d", index, len(missing))
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(known, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return known


def to_evidence(frame: pl.DataFrame, keys: dict[str, int]) -> pa.Table:
    """Reshape into ABUNDANCE_SURFACE rows on the native H3 grid."""
    # A cell with no year range cannot be placed in time, and the schema requires a period.
    # Dropped with a logged count rather than coerced to an invented date.
    undated = frame.filter(pl.col("min_year").is_null() | pl.col("max_year").is_null())
    if undated.height:
        log.warning(
            "dropping %d of %d rows with no year range (%d species affected)",
            undated.height,
            frame.height,
            undated["species"].n_unique(),
        )
        frame = frame.filter(pl.col("min_year").is_not_null() & pl.col("max_year").is_not_null())

    resolved = frame.with_columns(
        taxon_key=pl.col("species").replace_strict(keys, default=None, return_dtype=pl.Int64)
    )
    unresolved = resolved.filter(pl.col("taxon_key").is_null())
    if unresolved.height:
        names = unresolved["species"].unique()
        log.warning(
            "dropping %d rows for %d species with no GBIF key (e.g. %s)",
            unresolved.height,
            names.len(),
            names.head(3).to_list(),
        )
        resolved = resolved.filter(pl.col("taxon_key").is_not_null())

    out = resolved.select(
        source_id=pl.lit(SOURCE_ID),
        realm=pl.lit(Realm.MARINE.value),
        taxon_scope=pl.lit(TaxonScope.EXACT.value),
        taxon_key=pl.col("taxon_key"),
        taxon_label=pl.col("species"),
        cell_longitude=pl.col("cell_longitude").cast(pl.Float64),
        cell_latitude=pl.col("cell_latitude").cast(pl.Float64),
        # Null: an H3 hexagon has no single degree size.
        cell_size_deg=pl.lit(None, dtype=pl.Float64),
        cell_id=pl.col("cell"),
        cell_system=pl.lit(CELL_SYSTEM),
        # Real per-row period, unlike a product pooled over one fixed span.
        period_start=pl.date(pl.col("min_year"), 1, 1).cast(pl.Datetime("ms", time_zone="UTC")),
        period_end=pl.date(pl.col("max_year"), 12, 31).cast(pl.Datetime("ms", time_zone="UTC")),
        value=pl.col("records").cast(pl.Float64),
        # Occurrence records, not individuals and not abundance. Never sum against either.
        value_kind=pl.lit("occurrence_records"),
        value_lower=pl.lit(None, dtype=pl.Float64),
        value_upper=pl.lit(None, dtype=pl.Float64),
    )
    schema = spec_for(EvidenceType.ABUNDANCE_SURFACE).schema
    return out.select(schema.names).to_arrow().cast(schema)


def ingest() -> WriteResult:
    """Fetch, reshape and land the movement-relevant slice. Idempotent."""
    source = catalog.admit(SOURCE_ID)
    log.info("ingesting %s (%s)", source.title, source.licence)

    urls = part_urls()
    log.info("%d parts under %s", len(urls), PREFIX)

    frame = read_slice(urls)
    keys = taxon_keys(sorted(set(frame["species"].to_list())))
    table = to_evidence(frame, keys)
    log.info("%d evidence rows", table.num_rows)

    return write_evidence(table, spec_for(EvidenceType.ABUNDANCE_SURFACE), source_id=SOURCE_ID)
