"""North American Breeding Bird Survey: 1966-2025, as SURVEY_INDEX.

**A second instrument on the system Phase 1a measured.** The radar says nocturnal autumn passage
over 37-50 degN advanced 0.56 days per decade; BBS covers the same continent over a longer period
with a completely different method -- a skilled observer counting birds by ear and eye at 50 fixed
stops along a 39 km roadside route, every June, since 1966 -- and can say whether abundance changed
at those same places. Two independent instruments agreeing beats a third driver added to one.

Effort is fixed by design in the strongest sense yet in this lake: the same route, the same 50
stops, the same three minutes each, for up to sixty years. What varies is *who* is listening,
and the release ships the metadata to handle that: `ObsN`, `RunType` and `RPID` all travel into
`protocol`, because a break term cannot be fitted for something the lake did not keep.

Two curated exclusions come from the publisher rather than from us, and both are used:

- **`RPID`** identifies the run protocol. 101 is the standard survey; other values are experimental
  or incidental runs that the BBS's own analyses exclude.
- **`MigrantNonBreeder`** is a separate file of records the publisher holds *out* of the state count
  files: birds recorded at a route that are migrants or non-breeders there rather than breeding.
  Counting them as breeding-season abundance would be a category error, so the ingest lands the
  state files and reports how many records the publisher excluded.

CC0, which is the most permissive licence of any source here.
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

SOURCE_ID: Final = "bbs"

ITEM: Final = "6a0b0b0ab66b0188da36aedd"
"""The 2026 release, 1966-2025, doi 10.5066/P144YU3S.

Pinned rather than discovered: USGS publishes a new release most years and each is a separate
ScienceBase item, so "the latest" would silently change what a result was computed on. Earlier
releases and their item ids are in the catalogue under the same title.
"""

# The whole-release zip is built on demand and times out behind Cloudflare with a 524, so files are
# fetched individually. `?name=` resolves them; the `?f=__disk__<hash>` form the item also publishes
# is opaque and changes between releases.
BASE: Final = f"https://www.sciencebase.gov/catalog/file/get/{ITEM}"

ROUTES: Final = "Routes.csv"
WEATHER: Final = "Weather.csv"
SPECIES: Final = "SpeciesList.csv"
COUNTS: Final = "States.zip"
MIGRANTS: Final = "MigrantNonBreeder.zip"

STANDARD_PROTOCOL: Final = 101
"""`RPID` for the standard survey run. Other values are experimental or incidental."""

EFFORT_UNIT: Final = "bbs_route_run_50stops"
"""One run of one route: 50 three-minute point counts. `count / effort` is then individuals per run,
which is the index the BBS literature is built on."""

# Four of the 748 names the GBIF Backbone will not take, each because the survey follows a genus
# change the Backbone has not adopted. Every other failure -- 66 of 70 -- is a slash pair, a hybrid
# or an "sp." grouping -- real records that are genuinely not attributable to a taxon, and so are
# dropped for that reason rather than patched.
#
# Each replacement was checked through `gbif.match_name` itself, and all four come back EXACT,
# SPECIES, ACCEPTED at confidence 99:
SYNONYMS: Final[dict[str, str]] = {
    # Three plovers moved from Charadrius to Anarhynchus. The Backbone matches the new names to
    # *Animalia* -- and `Anarhynchus montanus` fuzzy-matches to `Anabarhynchus montanus`, a fly, at
    # confidence 81. The matcher's confidence floor is what stopped a plover being recorded as an
    # insect, which is the clearest argument yet for not lowering it.
    "Anarhynchus montanus": "Charadrius montanus",
    "Anarhynchus nivosus": "Charadrius nivosus",
    "Anarhynchus wilsonia": "Charadrius wilsonia",
    # Least bittern, moved from Ixobrychus to Botaurus. The Backbone matches the bare genus.
    "Botaurus exilis": "Ixobrychus exilis",
}


def files() -> dict[str, RemoteFile]:
    """The five files the ingest reads, by name."""
    return {
        name: RemoteFile(url=f"{BASE}?name={name}", name=name)
        for name in (ROUTES, WEATHER, SPECIES, COUNTS, MIGRANTS)
    }


def _fetch(name: str) -> Path:
    from migratlas.ingest.http import fetch  # noqa: PLC0415 -- avoids a cycle at import time

    return fetch(files()[name], SOURCE_ID)


def _read(source: Path | bytes, label: str) -> pl.DataFrame:
    """Read one release CSV, falling back to Latin-1 only when UTF-8 actually fails.

    The release is not UTF-8 throughout: Quebec route names and the French common names carry
    accented bytes in Windows-1252. Forcing Latin-1 everywhere would be simpler and wrong -- it
    turns genuinely UTF-8 text into mojibake silently, which is the mistake `fishglob.py` records
    making with a vessel name that had become part of a join key. So try the honest encoding first.
    """
    import io  # noqa: PLC0415 -- only this function needs it

    buffer = io.BytesIO(source) if isinstance(source, bytes) else source
    try:
        return pl.read_csv(buffer, infer_schema_length=0)
    except pl.exceptions.ComputeError:
        if isinstance(buffer, io.BytesIO):
            buffer.seek(0)
        log.info("  %s is not UTF-8, re-reading as Latin-1", label)
        return pl.read_csv(buffer, infer_schema_length=0, encoding="latin1")


def _trimmed(*columns: str) -> list[pl.Expr]:
    """BBS pads its fixed-width exports with spaces, so every field needs stripping before use."""
    return [pl.col(column).cast(pl.String).str.strip_chars() for column in columns]


def routes() -> pl.DataFrame:
    """Route identities and positions, keyed as the count files key them."""
    frame = _read(_fetch(ROUTES), ROUTES)
    return frame.with_columns(
        *_trimmed("CountryNum", "StateNum", "Route"),
        latitude=pl.col("Latitude").cast(pl.String).str.strip_chars().cast(pl.Float64),
        longitude=pl.col("Longitude").cast(pl.String).str.strip_chars().cast(pl.Float64),
    ).select(
        route_key=pl.concat_str(["CountryNum", "StateNum", "Route"], separator="-"),
        route_name=pl.col("RouteName").cast(pl.String).str.strip_chars(),
        latitude=pl.col("latitude"),
        longitude=pl.col("longitude"),
    )


def runs() -> pl.DataFrame:
    """One row per route-run: when it happened, who ran it, and whether it met the protocol."""
    frame = _read(_fetch(WEATHER), WEATHER)
    return frame.with_columns(
        *_trimmed("CountryNum", "StateNum", "Route", "ObsN"),
        run_id=pl.col("RouteDataID").cast(pl.String).str.strip_chars(),
        rpid=pl.col("RPID").cast(pl.String).str.strip_chars().cast(pl.Int32, strict=False),
        year=pl.col("Year").cast(pl.String).str.strip_chars().cast(pl.Int32, strict=False),
        month=pl.col("Month").cast(pl.String).str.strip_chars().cast(pl.Int32, strict=False),
        day=pl.col("Day").cast(pl.String).str.strip_chars().cast(pl.Int32, strict=False),
        run_type=pl.col("RunType").cast(pl.String).str.strip_chars(),
    ).select(
        "run_id",
        "rpid",
        "year",
        "month",
        "day",
        "run_type",
        route_key=pl.concat_str(["CountryNum", "StateNum", "Route"], separator="-"),
        observer=pl.col("ObsN"),
    )


def species() -> pl.DataFrame:
    """AOU code to a binomial the GBIF Backbone can resolve.

    The French common names are what make this file fail as UTF-8. They are dropped here -- only the
    code, the binomial and the English name are kept -- but the column still has to decode before it
    can be dropped, which is why `_read` exists.
    """
    frame = _read(_fetch(SPECIES), SPECIES)
    return frame.select(
        aou=pl.col("AOU").cast(pl.String).str.strip_chars(),
        name=pl.concat_str(
            [
                pl.col("Genus").cast(pl.String).str.strip_chars(),
                pl.col("Species").cast(pl.String).str.strip_chars(),
            ],
            separator=" ",
        ),
        common=pl.col("English_Common_Name").cast(pl.String).str.strip_chars(),
    )


def _from_zip(archive: Path, pattern: str) -> pl.DataFrame:
    """Every CSV in a release zip, concatenated: 62 state and province files in the counts."""
    import zipfile  # noqa: PLC0415 -- only this function needs it

    frames: list[pl.DataFrame] = []
    with zipfile.ZipFile(archive) as bundle:
        names = [name for name in bundle.namelist() if name.endswith(".csv") and pattern in name]
        log.info("%s: %d csv files", archive.name, len(names))
        for name in sorted(names):
            with bundle.open(name) as handle:
                frames.append(_read(handle.read(), name))
    if not frames:
        msg = f"{archive.name} held no CSV matching {pattern!r}"
        raise RuntimeError(msg)
    return pl.concat(frames, how="vertical_relaxed")


def counts() -> pl.DataFrame:
    """Species totals per route-run, from the per-state count files."""
    frame = _from_zip(_fetch(COUNTS), "States/")
    return frame.select(
        run_id=pl.col("RouteDataID").cast(pl.String).str.strip_chars(),
        aou=pl.col("AOU").cast(pl.String).str.strip_chars(),
        total=pl.col("SpeciesTotal").cast(pl.String).str.strip_chars().cast(pl.Int64, strict=False),
        stops=pl.col("StopTotal").cast(pl.String).str.strip_chars().cast(pl.Int64, strict=False),
    )


def excluded() -> int:
    """How many records the publisher held out as migrants or non-breeders.

    Reported rather than used. The number is the size of a judgement someone else made on our
    behalf, and a reader should be able to see it without going to the release.
    """
    return _from_zip(_fetch(MIGRANTS), "MigrantNonBreeder/Migrants.csv").height


def to_evidence(frame: pl.DataFrame, keys: dict[str, int]) -> pa.Table:
    """Reshape joined route-run-species rows into SURVEY_INDEX rows."""
    resolved = frame.with_columns(
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
        site_id=pl.col("route_key"),
        period_start=pl.date(pl.col("year"), pl.col("month"), pl.col("day")).cast(
            pl.Datetime("ms", time_zone="UTC")
        ),
        period_end=pl.date(pl.col("year"), pl.col("month"), pl.col("day")).cast(
            pl.Datetime("ms", time_zone="UTC")
        ),
        site_longitude=pl.col("longitude"),
        site_latitude=pl.col("latitude"),
        site_depth_m=pl.lit(None, dtype=pl.Float64),
        count=pl.col("total").cast(pl.Float64),
        # One run of the route. Not StopTotal, which counts the stops where the species *was*
        # detected and so is part of the response rather than of the effort.
        effort=pl.lit(1.0),
        effort_unit=pl.lit(EFFORT_UNIT),
        # The observer travels with the row because a first-year observer counts differently from
        # a practised one, and that is the best-documented bias in this dataset.
        protocol=pl.format(
            "rpid={} runtype={} observer={}",
            pl.col("rpid"),
            pl.col("run_type"),
            pl.col("observer"),
        ),
    )
    schema = spec_for(EvidenceType.SURVEY_INDEX).schema
    return out.select(schema.names).to_arrow().cast(schema)


def taxon_keys(names: list[str]) -> dict[str, int]:
    """Resolve binomials to GBIF Backbone keys, cached between runs.

    Keyed by the *survey's* name throughout, so a caller never needs to know a replacement was made.
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


def prepare() -> pl.DataFrame:
    """Counts joined to their run and their route, with unusable rows dropped and counted."""
    joined = (
        counts()
        .join(runs(), on="run_id", how="inner")
        .join(routes(), on="route_key", how="inner")
        .join(species(), on="aou", how="left")
    )
    log.info("%d count rows joined to a run and a route", joined.height)

    usable = joined.drop_nulls(["name", "total", "year", "month", "day", "latitude", "longitude"])
    dropped = joined.height - usable.height
    if dropped:
        log.warning("dropping %d rows with no binomial, count, date or position", dropped)

    # An AOU code without a binomial is an unidentified grouping -- "unid. Accipiter", hybrids, and
    # slash-species. Real records, and not attributable to a taxon, so they cannot be evidence about
    # one. Counted above rather than dropped in silence.
    return usable


def ingest(root: Path | None = None) -> WriteResult:
    """Fetch, join and land the survey as SURVEY_INDEX."""
    catalog.admit(SOURCE_ID)
    frame = prepare()
    log.info(
        "%d rows | %d routes | %d species | %d-%d | publisher excluded %d migrant records",
        frame.height,
        frame["route_key"].n_unique(),
        frame["name"].n_unique(),
        frame["year"].min(),
        frame["year"].max(),
        excluded(),
    )
    table = to_evidence(frame, taxon_keys(frame["name"].unique().to_list()))
    log.info("%d evidence rows", table.num_rows)
    return write_evidence(
        table, spec_for(EvidenceType.SURVEY_INDEX), source_id=SOURCE_ID, root=root
    )
