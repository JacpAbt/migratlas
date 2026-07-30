"""SABAP2: the second Southern African Bird Atlas, via the GBIF download API.

25,687,526 records over 2007-2026, and the late half of the atlas-against-atlas comparison
`sabap1.py` provides the early half of. Two routes were tested on 2026-07-30 and only this one
works, which is recorded in docs/methods/geographic-coverage.md:

- The publisher's own IPT at `aduipt.uct.ac.za:8080` times out, on the archive and on its small EML
  alike. Treat the advertised DwC-A as unavailable.
- The atlas's API (`api.birdmap.africa`) serves per-pentad card counts and reporting rates, already
  split by protocol, but **pooled over 2007-present** with no per-year endpoint. Good for a map,
  useless for a series.
- The GBIF download API works, needs a free account, and issues a **DOI per download** -- which is
  better provenance than either archive, because it pins the exact records a result was computed on.

Downloads are asynchronous: a request is queued, GBIF prepares an archive over minutes to hours, and
the key it returns is the handle. So this module submits and polls rather than blocking.

**The Darwin Core archive, after SIMPLE_CSV turned out to be insufficient.** SIMPLE_CSV was asked
for first, on the belief that `catalogNumber` carried the card id. It does not: in the download it
repeats `occurrenceID` (`urn:fiao:sabap2:fullprot:rid10002350`). Reading the search API's own fields
back in order shows where the card id actually lives:

| field | content | in SIMPLE_CSV? |
| --- | --- | --- |
| `occurrenceID` | `urn:fiao:sabap2:fullprot:rid...` — carries the **protocol** | yes |
| `fieldNotes` | `2215_1730_004876_20201115` — the **card**: pentad, observer, date | **no** |
| `eventRemarks` | `TotalHour observing:3 ...` — hours per card | **no** |
| `verbatimLocality` | `2215_1730` — the **pentad** | **no** |

The card is the effort denominator, so a download without it cannot produce a reporting rate. The
pentad *is* recoverable from the coordinates -- they are pentad centroids on a 1/12 degree grid,
with a sub-arcsecond offset from `COORDINATE_ROUNDED` -- but the card is not recoverable from
anything. A proxy of (pentad, observer, date) would split a card that spans several days, and a
full-protocol card may cover its pentad over up to five, so the proxy would inflate effort by an
unknown factor and do it unevenly between observers.

What SIMPLE_CSV does get right, and what is worth keeping: GBIF's `taxonKey` and `speciesKey` are
*accepted* backbone keys, so this source needs no name resolution and cannot inherit the synonym
problem `sabap1.py` ran into. The DwC-A carries those too, beside the verbatim fields.
"""

import logging
from typing import TYPE_CHECKING, Any, Final

import polars as pl

from migratlas.catalog import loader as catalog
from migratlas.config import get_settings
from migratlas.evidence import EvidenceType, Realm, TaxonScope, spec_for
from migratlas.lake.writer import WriteResult, write_evidence

if TYPE_CHECKING:
    from pathlib import Path

    import httpx
    import pyarrow as pa

log = logging.getLogger(__name__)

SOURCE_ID: Final = "sabap2"
API: Final = "https://api.gbif.org/v1"

DATASET_KEY: Final = "906e6978-e292-4a8b-9c39-adf6bb0f3323"
"""SABAP2 on GBIF. Not 282d0ccb-..., which is SABAP1 -- the docs named the wrong one until
2026-07-30, and the two atlases are twenty years apart."""

FORMAT: Final = "DWCA"
"""The archive format. See the module docstring: SIMPLE_CSV omits the card id and so cannot produce
an effort denominator."""

DOWNLOAD_KEY: Final = "0018243-260721160103020"
"""The download this project's results are computed on, requested 2026-07-30.

25,687,526 records as a Darwin Core archive, 7.36 GiB, **doi 10.15468/dl.wb5t54** -- which is what a
result cites, because it pins the exact records rather than "SABAP2 as of whenever". GBIF keeps a
prepared download for six months, so a re-run after that needs a fresh request and a new DOI."""

SIMPLE_CSV_KEY: Final = "0018183-260721160103020"
"""The first download, kept for the record rather than used.

25,687,526 records, 2.35 GiB, doi 10.15468/dl.8zjvpv. Requested in SIMPLE_CSV on the mistaken belief
that `catalogNumber` held the card id; it holds a copy of `occurrenceID`. Left here because a
superseded download is part of the provenance, and because re-requesting it would be the obvious
mistake to make twice."""

# GBIF asks that a client identify itself, and a download is attributable to an account.
USER_AGENT: Final = "migratlas (+https://github.com/JacpAbt/migratlas)"

TIMEOUT_S: Final = 60.0


class DownloadError(RuntimeError):
    """GBIF refused a request or a download."""


def predicate() -> dict[str, Any]:
    """Every record in the SABAP2 dataset, and nothing else.

    Deliberately not filtered further. Restricting to the full protocol here would bake an analysis
    decision into the archive the DOI refers to, and the ad-hoc records are needed anyway -- to be
    excluded knowingly, and to be counted when saying how many were excluded.
    """
    return {"type": "equals", "key": "DATASET_KEY", "value": DATASET_KEY}


def _client() -> httpx.Client:
    import httpx  # noqa: PLC0415 -- a runtime dependency of this module only

    settings = get_settings()
    return httpx.Client(
        base_url=API,
        timeout=TIMEOUT_S,
        headers={"User-Agent": USER_AGENT},
        # The password, never a field on anything and never logged. GBIF's download API has no
        # separate key, which is why config.py's hint says to put it in .env and nowhere else.
        auth=(settings.credential("gbif_user"), settings.credential("gbif_password")),
        follow_redirects=True,
    )


def request_download(*, notify: bool = False) -> str:
    """Queue the download and return its key.

    The key is the only thing worth keeping from this call: it is how the archive is polled, fetched
    and cited, and GBIF keeps a prepared download for six months.
    """
    body = {
        "creator": get_settings().credential("gbif_user"),
        "sendNotification": notify,
        "format": FORMAT,
        "predicate": predicate(),
    }
    with _client() as http:
        response = http.post("/occurrence/download/request", json=body)
        if response.status_code >= 400:  # noqa: PLR2004 -- httpx has no constant for this
            msg = (
                f"GBIF refused the download request ({response.status_code}): {response.text[:200]}"
            )
            raise DownloadError(msg)
        key = response.text.strip()
    log.info("queued GBIF download %s for dataset %s", key, DATASET_KEY)
    return key


def status(key: str) -> dict[str, Any]:
    """What GBIF says about a queued download: its status, size, record count and DOI."""
    with _client() as http:
        response = http.get(f"/occurrence/download/{key}")
        if response.status_code >= 400:  # noqa: PLR2004 -- httpx has no constant for this
            msg = f"GBIF would not describe download {key} ({response.status_code})"
            raise DownloadError(msg)
        payload: dict[str, Any] = response.json()
    return payload


def describe(key: str) -> str:
    """One line about a download, for a CLI or a log."""
    found = status(key)
    size = found.get("size") or 0
    return (
        f"{key}: {found.get('status')} | {found.get('totalRecords', 0):,} records | "
        f"{size / 1024**2:.0f} MiB | doi {found.get('doi', '-')}"
    )


CORE: Final = "occurrence.txt"

PROJECTION: Final = "sabap2-core.parquet"
"""Where the projected columns are cached, beside the archive in the raw store."""

NEEDED: Final[tuple[str, ...]] = (
    # Carries the protocol: "fullprot" or "adhocprot". Only full-protocol cards are effort-
    # standardised, and the ad-hoc ones have to be excluded knowingly and counted.
    "occurrenceID",
    # The card: pentad, observer, date. The effort denominator, and the field SIMPLE_CSV omits.
    "fieldNotes",
    # The pentad code as the atlas writes it, so the grid never has to be inferred from coordinates.
    "verbatimLocality",
    "eventDate",
    "year",
    "month",
    "day",
    # Hours observed, whether nights were included, whether all habitats were covered. Effort
    # covariates finer than the card, kept because they are free once the row is being read.
    "eventRemarks",
    # GBIF's *accepted* backbone key, so this source needs no name resolution at all.
    "speciesKey",
    "species",
    "decimalLatitude",
    "decimalLongitude",
    "countryCode",
)

BATCH: Final = 500_000


def project(archive: Path) -> Path:
    """Stream the core file and keep only the columns the design needs.

    The core is 33.5 GB uncompressed and the verbatim file another 19.5, so neither is extracted.
    Instead the entry is read as a stream straight out of the zip and written out as Parquet holding
    thirteen columns of twenty-five million rows, which is a few hundred megabytes rather than fifty
    gigabytes. Cached, because the pass takes minutes.
    """
    import csv  # noqa: PLC0415 -- only this function needs these
    import io  # noqa: PLC0415
    import zipfile  # noqa: PLC0415

    import pyarrow as pa  # noqa: PLC0415
    import pyarrow.parquet as pq  # noqa: PLC0415

    # GBIF writes its archives tab-delimited with no quote character, stripping tabs from values
    # rather than quoting them. The reader has to be told: with the default, one apostrophe in an
    # observer's name swallows every following line until the next one.

    out = archive.parent / PROJECTION
    if out.exists() and out.stat().st_size:
        log.info("%s already projected (%.0f MiB)", out.name, out.stat().st_size / 1024**2)
        return out

    schema = pa.schema([pa.field(name, pa.string()) for name in NEEDED])
    written = malformed = 0
    partial = out.with_suffix(".part")

    with zipfile.ZipFile(archive) as bundle, bundle.open(CORE) as raw:
        stream = io.TextIOWrapper(raw, encoding="utf-8", errors="replace", newline="")
        reader = csv.reader(stream, delimiter="\t", quoting=csv.QUOTE_NONE)
        header = next(reader)
        index = {name: header.index(name) for name in NEEDED}
        width = len(header)

        with pq.ParquetWriter(partial, schema, compression="zstd") as writer:
            batch: list[list[str]] = []
            for row in reader:
                # A row of the wrong width means the delimiter appeared inside a value. Counted
                # rather than guessed at: a silently shifted row would put a date in a taxon column.
                if len(row) != width:
                    malformed += 1
                    continue
                batch.append([row[index[name]] for name in NEEDED])
                if len(batch) >= BATCH:
                    writer.write_table(_as_table(batch, schema))
                    written += len(batch)
                    batch = []
                    log.info("  %s rows projected", f"{written:,}")
            if batch:
                writer.write_table(_as_table(batch, schema))
                written += len(batch)

    partial.replace(out)
    log.info("%s rows projected, %s malformed", f"{written:,}", f"{malformed:,}")
    return out


def _as_table(batch: list[list[str]], schema: pa.Schema) -> pa.Table:
    import pyarrow as pa  # noqa: PLC0415 -- an optional extra everywhere else in this module

    columns = list(zip(*batch, strict=True))
    return pa.table(
        {
            name: pa.array(values, pa.string())
            for name, values in zip(schema.names, columns, strict=True)
        },
        schema=schema,
    )


PENTAD_DEG: Final = 1 / 12
"""Five arcminutes. A quarter-degree SABAP1 cell holds exactly nine of these, which is what makes
the two atlases comparable at all -- see `metrics` and the method note."""

EFFORT_UNIT: Final = "atlas_cards"
"""The same unit `sabap1.py` uses, deliberately. The whole point of this source is a comparison
against that one, and two similar-but-different denominators would make it meaningless."""

FULL_PROTOCOL: Final = "fullprot"
"""The effort-standardised protocol: a pentad covered for a minimum period with a species list.
`adhocprot` is a casual list -- 9.5 species per card against 52 -- and is landed separately rather
than mixed in, so it can be excluded knowingly and counted."""

PLAUSIBLE_YEARS: Final[tuple[int, int]] = (1900, 2027)
"""Only the impossible is excluded, as in `sabap1.py`. The archive holds years back to 1930, which
is early for a project that began in 2007 but not impossible for a retrospective card. Which years
belong to the atlas is the metric's question, answered through ATLAS_YEARS."""

ATLAS_YEARS: Final[tuple[int, int]] = (2007, 2025)
"""The years the project has run at scale. 2000-2006 carry single-digit cards, and 2026 is a partial
year at the time of download -- 108,352 rows against 1.3 million for a full one."""


def core(archive: Path) -> pl.DataFrame:
    """The projected columns, typed, with the protocol and the pentad pulled out.

    The protocol comes out of `occurrenceID` because that is where the atlas puts it, and the pentad
    out of `verbatimLocality` rather than out of the card id. Those two disagree for 117,960 of
    21,279,299 full-protocol rows -- half a percent -- and the record's own locality is the better
    authority for where the record is than a string embedded in the identifier of the card it
    arrived on. The disagreement is reported rather than reconciled.
    """
    frame = (
        pl.scan_parquet(archive.parent / PROJECTION)
        .select(
            card=pl.col("fieldNotes"),
            pentad=pl.col("verbatimLocality"),
            protocol=pl.col("occurrenceID").str.extract(r"sabap2:(\w+?):", 1),
            year=pl.col("year").cast(pl.Int32, strict=False),
            month=pl.col("month").cast(pl.Int32, strict=False),
            taxon_key=pl.col("speciesKey").cast(pl.Int64, strict=False),
            taxon_label=pl.col("species"),
            latitude=pl.col("decimalLatitude").cast(pl.Float64, strict=False),
            longitude=pl.col("decimalLongitude").cast(pl.Float64, strict=False),
        )
        .collect()
    )
    log.info("%s projected rows", f"{frame.height:,}")

    disagree = frame.filter(
        pl.col("protocol") == FULL_PROTOCOL, pl.col("card").str.slice(0, 9) != pl.col("pentad")
    ).height
    log.info(
        "  %s full-protocol rows where the card id's pentad differs from verbatimLocality",
        f"{disagree:,}",
    )

    usable = frame.drop_nulls(
        ["card", "pentad", "protocol", "year", "latitude", "longitude"]
    ).filter(pl.col("year").is_between(*PLAUSIBLE_YEARS))
    untyped = frame.height - usable.height
    if untyped:
        log.warning(
            "dropping %s rows with no card, pentad, protocol, year or position", f"{untyped:,}"
        )

    unattributed = usable.filter(pl.col("taxon_key").is_null()).height
    log.info(
        "  %s rows carry no accepted species key (unidentified or coarser than species)",
        f"{unattributed:,}",
    )
    return usable.drop_nulls("taxon_key").with_columns(
        month=pl.col("month").fill_null(1).clip(1, 12)
    )


def reporting_rates(frame: pl.DataFrame) -> pl.DataFrame:
    """Cards-with-the-species and cards-submitted, per pentad per month per species per protocol.

    Aggregated **within** protocol rather than across it. A full-protocol card and an ad-hoc list
    are not the same unit of effort, and pooling them would put a nine-species casual list in the
    same denominator as a fifty-two-species survey.

    A card is counted once per pentad, as in `sabap1.py`: a card with records in two pentads
    contributed effort to both.
    """
    keys = ("pentad", "protocol", "year", "month")
    effort = frame.group_by(keys).agg(
        effort=pl.col("card").n_unique(),
        latitude=pl.col("latitude").first(),
        longitude=pl.col("longitude").first(),
    )
    present = frame.group_by([*keys, "taxon_key", "taxon_label"]).agg(
        count=pl.col("card").n_unique()
    )
    return present.join(effort, on=keys, how="inner")


def to_evidence(rates: pl.DataFrame) -> pa.Table:
    """Reshape into SURVEY_INDEX rows.

    No name resolution: `speciesKey` is already an accepted GBIF Backbone key, so this source cannot
    inherit the synonym problem `sabap1.py` had to patch with a table of six replacements.
    """
    out = rates.select(
        source_id=pl.lit(SOURCE_ID),
        realm=pl.lit(Realm.TERRESTRIAL.value),
        taxon_scope=pl.lit(TaxonScope.EXACT.value),
        taxon_key=pl.col("taxon_key"),
        taxon_label=pl.col("taxon_label"),
        # The atlas's own pentad code, prefixed so it cannot be mistaken for SABAP1's derived
        # quarter-degree id. Rolling pentads up to those cells is the metric's job.
        site_id=pl.lit("pentad:") + pl.col("pentad"),
        period_start=pl.date(pl.col("year"), pl.col("month"), 1).cast(
            pl.Datetime("ms", time_zone="UTC")
        ),
        period_end=pl.date(pl.col("year"), pl.col("month"), 1)
        .dt.month_end()
        .cast(pl.Datetime("ms", time_zone="UTC")),
        site_longitude=pl.col("longitude"),
        site_latitude=pl.col("latitude"),
        site_depth_m=pl.lit(None, dtype=pl.Float64),
        count=pl.col("count").cast(pl.Float64),
        effort=pl.col("effort").cast(pl.Float64),
        effort_unit=pl.lit(EFFORT_UNIT),
        protocol=pl.lit("BirdMAP ") + pl.col("protocol"),
    )
    schema = spec_for(EvidenceType.SURVEY_INDEX).schema
    return out.select(schema.names).to_arrow().cast(schema)


def ingest(root: Path | None = None) -> WriteResult:
    """Fetch, project, aggregate to pentad-month reporting rates and land as SURVEY_INDEX."""
    catalog.admit(SOURCE_ID)
    archive = fetch_archive(DOWNLOAD_KEY)
    project(archive)
    frame = core(archive)

    rates = reporting_rates(frame)
    full = rates.filter(pl.col("protocol") == FULL_PROTOCOL)
    log.info(
        "%s rows | %s pentads | %s cards | %s species | %d-%d",
        f"{rates.height:,}",
        f"{frame['pentad'].n_unique():,}",
        f"{frame['card'].n_unique():,}",
        f"{frame['taxon_key'].n_unique():,}",
        frame["year"].min(),
        frame["year"].max(),
    )
    log.info(
        "  full protocol: %s rows, %s pentads; ad-hoc landed separately",
        f"{full.height:,}",
        f"{full['pentad'].n_unique():,}",
    )
    table = to_evidence(rates)
    log.info("%s evidence rows", f"{table.num_rows:,}")
    return write_evidence(
        table, spec_for(EvidenceType.SURVEY_INDEX), source_id=SOURCE_ID, root=root
    )


def fetch_archive(key: str) -> Path:
    """Download a prepared archive, resuming if a previous attempt was cut short.

    The archive URL is public once the download has succeeded, so this needs no credential -- and
    the DOI is what a result should cite, not the key. Refuses a download that is not ready rather
    than saving GBIF's "not finished" response as a zip.
    """
    from migratlas.ingest.http import RemoteFile, fetch  # noqa: PLC0415 -- avoids a cycle

    found = status(key)
    state = found.get("status")
    if state != "SUCCEEDED":
        msg = f"download {key} is {state}, not SUCCEEDED -- nothing to fetch yet"
        raise DownloadError(msg)

    log.info(
        "fetching %s: %s records, %.2f GiB, doi %s",
        key,
        f"{found.get('totalRecords', 0):,}",
        (found.get("size") or 0) / 1024**3,
        found.get("doi", "-"),
    )
    remote = RemoteFile(
        url=f"{API}/occurrence/download/request/{key}.zip",
        name=f"{key}.zip",
    )
    return fetch(remote, SOURCE_ID)
