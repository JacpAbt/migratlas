"""SABAP1: the first Southern African Bird Atlas, as SURVEY_INDEX.

The first source in the lake that is neither northern nor marine, and the first to fill the
terrestrial realm. 5,053,399 records over 98,878 atlas cards, 1,568 quarter-degree cells and 757
species, with the atlas core in 1987-1991.

**A card is the effort unit and the reason this source is usable at all.** An atlas card is one
observer covering one quarter-degree cell over one month and listing the species they found, so
"how many cards" is a measured denominator rather than an effort proxy inferred after the fact --
the same property that made FISHGLOB usable where OBIS was not (docs/methods/phase1b-marine.md).
Reporting rate is cards-with-the-species over cards, and it is stored as those two numbers rather
than as the ratio, so the footprint rule can be applied by the metric where it can also be reported.

**Two things about the grain, both of which will bite a metric that ignores them.**

A cell-month usually holds one or two cards -- 39% hold exactly one, the median is two -- so at this
grain the rate is *degenerate*: a species present on the only card scores 1.0. The rate becomes
meaningful when months are pooled, and over the 1987-1991 core it behaves as an occupancy measure
should: 0.02 at the tenth percentile, 0.18 at the median, 0.67 at the ninetieth, and never above 1.

And ``effort`` is a property of the *cell-month*, repeated across every species row belonging to it,
so summing it over rows multiplies it by the number of species recorded. One real cell has 13 cards
over the core and sums to 980. Pool by taking effort once per distinct (site, period) and summing
counts separately. `metrics/range.py` is safe because it divides per row rather than summing, but
anything computing an aggregate rate has to do this deliberately.

Read from the archive GBIF hosts itself. The publisher's IPT is gone, which is why this dataset
is served from `orphans.gbif.org`; SABAP2's IPT is still advertised and does not answer at all,
which is recorded in docs/methods/geographic-coverage.md.
"""

import logging
from typing import TYPE_CHECKING, Final

import polars as pl

from migratlas.catalog import loader as catalog
from migratlas.evidence import EvidenceType, Realm, TaxonScope, spec_for
from migratlas.ingest.http import RemoteFile
from migratlas.lake.writer import WriteResult, write_evidence

if TYPE_CHECKING:
    from pathlib import Path

    import pyarrow as pa

log = logging.getLogger(__name__)

SOURCE_ID: Final = "sabap1"

ARCHIVE: Final = RemoteFile(
    url="https://orphans.gbif.org/ZA/282d0ccb-4fa0-40f9-8593-105c77e88417.zip",
    name="sabap1-dwca.zip",
)
CORE: Final = "occurrence.txt"

# Quarter-degree grid cells, which is what SABAP1 surveyed. The published coordinates are already
# cell centres -- every latitude ends in .125 or .375 -- so the snapping below removes float noise
# rather than changing the geometry.
CELL_DEG: Final = 0.25

# Only the impossible is excluded, and exactly one row qualifies: a year of 2975. The archive's
# oldest years -- 1901, 1904, 1919, 1934 -- are 529 rows that are merely *old*, and an early draft
# of this bound started at 1950 and threw them away while calling them implausible. A record of 1934
# is perfectly possible for a bird; whether it belongs to the atlas is a different question, and it
# is the metric's to answer through ATLAS_CORE rather than the ingest's to answer by deletion.
PLAUSIBLE_YEARS: Final[tuple[int, int]] = (1900, 2000)

# The five years the atlas itself covers, for reference by anything comparing it with SABAP2.
ATLAS_CORE: Final[tuple[int, int]] = (1987, 1991)

EFFORT_UNIT: Final = "atlas_cards"

# Six of the 757 names the GBIF Backbone matcher will not take at species rank, each replaced by a
# name that resolves exactly. Together they are 27,921 rows and six species -- including an eagle, a
# buzzard and two owls -- so dropping them was not an option, and loosening the matcher's
# confidence floor would have bought them at the price of bad matches everywhere else.
#
# Each replacement was checked against /species/match before being written here:
SYNONYMS: Final[dict[str, str]] = {
    # Ayres's hawk-eagle moved genus; the Backbone has no Aquila synonym for it and matches the
    # bare genus instead.
    "Aquila ayresii": "Hieraaetus ayresii",
    # Cape eagle-owl. "Bubo capensis" alone matches *Animalia* at confidence 99 -- a homonym
    # collision somewhere in the Backbone -- and appending the authority resolves it exactly.
    "Bubo capensis": "Bubo capensis Smith, 1834",
    # The steppe buzzard is a subspecies of the common buzzard now, and the subspecies key is the
    # faithful record of what an atlaser wrote down. The spine can roll it up; it cannot split it
    # back apart.
    "Buteo vulpinus": "Buteo buteo vulpinus",
    # Rockrunner's warbler relatives were moved out of Parisoma, which is itself now a synonym.
    # The Backbone still files this bird under Sylvia rather than Curruca.
    "Parisoma subcaeruleum": "Sylvia subcaerulea",
    # Black saw-wing, sunk into Psalidoprocne pristoptera as a subspecies. Resolving the name gives
    # a synonym whose accepted usage is that subspecies, which is what lands.
    "Psalidoprocne holomelaena": "Psalidoprocne holomelas",
    # A spelling error in the source: the genus is Ptilopsis, not Ptilopsus.
    "Ptilopsus granti": "Ptilopsis granti",
}

# Columns the evidence rows need, named so an upstream schema change fails here rather than
# producing a column of nulls. `collectionCode` is the card: it varies row to row within a cell and
# a month, and `catalogNumber` embeds it as its first component.
NEEDED: Final[tuple[str, ...]] = (
    "collectionCode",
    "year",
    "month",
    "verbatimLatitude",
    "verbatimLongitude",
    "scientificName",
)


def extract() -> Path:
    """Fetch the archive and unpack the core file beside it, once.

    Two gigabytes unpacked, so it is written next to the archive in the raw store rather than to a
    temporary directory that a second run would have to pay for again.
    """
    import zipfile  # noqa: PLC0415 -- only this function needs it

    from migratlas.ingest.http import fetch  # noqa: PLC0415 -- avoids a cycle at import time

    archive = fetch(ARCHIVE, SOURCE_ID)
    core = archive.parent / CORE
    if not core.exists() or core.stat().st_size == 0:
        log.info("unpacking %s", CORE)
        with (
            zipfile.ZipFile(archive) as bundle,
            bundle.open(CORE) as source,
            core.open("wb") as target,
        ):
            while chunk := source.read(1 << 22):
                target.write(chunk)
    log.info("%s: %.1f GiB", core.name, core.stat().st_size / 1024**3)
    return core


def _cell_centre(column: str) -> pl.Expr:
    """Snap a coordinate to the centre of its quarter-degree cell."""
    return ((pl.col(column) / CELL_DEG).floor() + 0.5) * CELL_DEG


def read_cards(core: Path) -> pl.DataFrame:
    """One row per card-cell-month-species, with the cell snapped and bad years dropped.

    Streamed, because the core file is two gigabytes of tab-separated text with 235 columns and
    only six of them matter.
    """
    frame = (
        pl.scan_csv(
            core,
            separator="\t",
            quote_char=None,
            infer_schema_length=0,
            truncate_ragged_lines=True,
            ignore_errors=True,
        )
        .select(NEEDED)
        .with_columns(
            card=pl.col("collectionCode"),
            year=pl.col("year").cast(pl.Int32, strict=False),
            month=pl.col("month").cast(pl.Int32, strict=False),
            latitude=pl.col("verbatimLatitude").cast(pl.Float64, strict=False),
            longitude=pl.col("verbatimLongitude").cast(pl.Float64, strict=False),
            name=pl.col("scientificName"),
        )
        .drop_nulls(["card", "year", "latitude", "longitude", "name"])
        .with_columns(
            cell_latitude=_cell_centre("latitude"),
            cell_longitude=_cell_centre("longitude"),
            # Month resolution is what the source has: `day` holds 1, 28, 30 or 31 -- the ends of
            # a month, not an observation date -- so a day would be invented rather than recorded.
            month=pl.col("month").fill_null(1).clip(1, 12),
        )
        .collect(engine="streaming")
    )

    plausible = frame.filter(pl.col("year").is_between(*PLAUSIBLE_YEARS))
    dropped = frame.height - plausible.height
    if dropped:
        outside = frame.filter(~pl.col("year").is_between(*PLAUSIBLE_YEARS))["year"]
        log.warning(
            "dropping %d rows whose year is outside %d-%d (%s)",
            dropped,
            *PLAUSIBLE_YEARS,
            sorted(outside.unique().to_list())[:6],
        )
    return plausible


def reporting_rates(cards: pl.DataFrame) -> pl.DataFrame:
    """Cards-with-the-species and cards-surveyed, per cell per month per species.

    The card is counted per *cell*, not globally: 830 of the 98,878 cards carry records in two
    cells, and a card that touches two cells contributed effort to both. Counting it once per cell
    keeps the denominator equal to the effort that actually landed there.

    No zero rows. The atlas is presence-only, and a card lists 42 species at the median, so every
    surveyed cell-month appears in this table through some species and the denominator stays
    recoverable without storing 1,568 x 757 x months mostly-empty combinations.
    """
    keys = ("cell_latitude", "cell_longitude", "year", "month")
    effort = cards.group_by(keys).agg(effort=pl.col("card").n_unique())
    present = cards.group_by([*keys, "name"]).agg(count=pl.col("card").n_unique())
    return present.join(effort, on=keys, how="inner")


def to_evidence(rates: pl.DataFrame, keys: dict[str, int]) -> pa.Table:
    """Reshape into SURVEY_INDEX rows.

    Realm is terrestrial, which is a judgement worth stating: an atlas card records which birds
    occupy a patch of land, where the radar in Phase 1a records birds in flight. The same species
    can appear under both realms for that reason, and it is not a contradiction.
    """
    resolved = rates.with_columns(
        taxon_key=pl.col("name").replace_strict(keys, default=None, return_dtype=pl.Int64)
    )
    unresolved = resolved.filter(pl.col("taxon_key").is_null())
    if unresolved.height:
        names = unresolved["name"].unique()
        log.warning(
            "dropping %d rows for %d taxa with no GBIF key (e.g. %s)",
            unresolved.height,
            names.len(),
            names.head(3).to_list(),
        )
        resolved = resolved.filter(pl.col("taxon_key").is_not_null())

    out = resolved.select(
        source_id=pl.lit(SOURCE_ID),
        realm=pl.lit(Realm.TERRESTRIAL.value),
        taxon_scope=pl.lit(TaxonScope.EXACT.value),
        taxon_key=pl.col("taxon_key"),
        taxon_label=pl.col("name"),
        # The cell is the site, and its id is derived from its own centre rather than from the
        # atlas's quarter-degree letter codes. Deriving it keeps the id checkable against the
        # coordinates in the same row; re-implementing someone else's grid notation does not.
        site_id=pl.format(
            "qdgc:{}:{}",
            pl.col("cell_latitude").round(3).cast(pl.String),
            pl.col("cell_longitude").round(3).cast(pl.String),
        ),
        period_start=pl.date(pl.col("year"), pl.col("month"), 1).cast(
            pl.Datetime("ms", time_zone="UTC")
        ),
        # End of the month the card covers, so the row's own precision is legible without knowing
        # that SABAP1 cards are monthly.
        period_end=pl.date(pl.col("year"), pl.col("month"), 1)
        .dt.month_end()
        .cast(pl.Datetime("ms", time_zone="UTC")),
        site_longitude=pl.col("cell_longitude"),
        site_latitude=pl.col("cell_latitude"),
        site_depth_m=pl.lit(None, dtype=pl.Float64),
        count=pl.col("count").cast(pl.Float64),
        effort=pl.col("effort").cast(pl.Float64),
        effort_unit=pl.lit(EFFORT_UNIT),
        protocol=pl.lit(f"SABAP1 atlas card, {CELL_DEG} deg cell, month resolution"),
    )
    schema = spec_for(EvidenceType.SURVEY_INDEX).schema
    return out.select(schema.names).to_arrow().cast(schema)


def taxon_keys(names: list[str]) -> dict[str, int]:
    """Resolve scientific names to GBIF Backbone keys, cached between runs.

    Keyed by the *source's* name throughout, so a caller never needs to know a replacement was
    made -- the SYNONYMS table is an implementation detail of resolution, not of the data.
    """
    import json  # noqa: PLC0415 -- only this function needs it

    from migratlas.config import get_settings  # noqa: PLC0415 -- avoids a cycle
    from migratlas.taxonomy import gbif  # noqa: PLC0415 -- avoids a cycle

    cache = get_settings().cache_dir / f"{SOURCE_ID}_taxon_keys.json"
    known: dict[str, int] = {}
    if cache.exists():
        known = {str(k): int(v) for k, v in json.loads(cache.read_text(encoding="utf-8")).items()}

    missing = sorted({name for name in names if name and name not in known})
    if missing:
        log.info("resolving %d names against the GBIF Backbone", len(missing))
        with gbif.client() as http:
            for index, name in enumerate(missing, start=1):
                try:
                    known[name] = gbif.match_name(http, SYNONYMS.get(name, name)).usage_key
                except (gbif.TaxonomyError, OSError) as error:
                    log.debug("unresolved %r: %s", name, error)
                if index % 100 == 0:
                    log.info("  %d/%d", index, len(missing))
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(known, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return known


def ingest(root: Path | None = None) -> WriteResult:
    """Fetch, aggregate to cell-month reporting rates and land as SURVEY_INDEX."""
    catalog.admit(SOURCE_ID)
    cards = read_cards(extract())
    log.info(
        "%d rows | %d cards | %d cells | %d species | %d-%d",
        cards.height,
        cards["card"].n_unique(),
        cards.select(pl.struct("cell_latitude", "cell_longitude").n_unique()).item(),
        cards["name"].n_unique(),
        cards["year"].min(),
        cards["year"].max(),
    )

    rates = reporting_rates(cards)
    log.info("%d cell-month-species rows", rates.height)
    table = to_evidence(rates, taxon_keys(cards["name"].unique().to_list()))
    log.info("%d evidence rows", table.num_rows)
    return write_evidence(
        table, spec_for(EvidenceType.SURVEY_INDEX), source_id=SOURCE_ID, root=root
    )
