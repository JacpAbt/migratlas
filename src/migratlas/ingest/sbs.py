"""The Swedish Bird Survey, as SURVEY_INDEX: the lake's first European time series.

Two schemes from one programme at Lund University, both CC0, both published as Darwin Core
*sampling event* archives — which is the whole reason they are here. An event archive separates
"a survey happened" from "a species was seen", so effort is a table rather than an inference, and a
species not listed against an event that did happen is an absence you can derive. That is the same
property that made SABAP's cards usable and OBIS's occurrences not.

The summer point counts run **1975-2024, fifty distinct years**, the longest unbroken series in this
lake by twenty. The fixed routes run 1996-2025 on a *systematic* national grid — one route per
25 x 25 km square, walked the same way at the same time of year — so unlike BBS they carry no
roadside bias, and holding both is how that bias becomes testable rather than assumed.

**Sixteen taxa are missing by policy and the ingest has to say so.** The publisher withholds every
species at Swedish security class 4 or higher: eleven birds in both schemes, and in the fixed
routes also lynx, wolf, brown bear, wolverine and Arctic fox. This is a redaction we agree with, and
it is the same judgement `redact.py` makes — but it interacts badly with the one thing an event
archive is good for. Derived absence means "surveyed, and not recorded", and for a withheld species
that is true at *every* event in the scheme, so a detection model left alone would read a national
redaction as a national extinction. They are dropped by name here, before anything can count them,
and the number dropped is logged.

Two more things the archive states that the schema cannot:

**A coordinate is a 25 km square, not a route.** `coordinateUncertaintyInMeters` is 17,700 on every
event, and `locationRemarks` says the point given is the centre of the survey square. Nothing finer
than that square is supported.

**A count is a route total.** The point counts sum twenty points and the fixed routes sum eight 1 km
lines, so a row is one species at one route-visit. Effort is therefore the survey *window* — the
archive gives `eventTime` as a start/end pair — rather than a number of stops.
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import polars as pl

from migratlas.catalog import loader as catalog
from migratlas.evidence import EvidenceType, Realm, TaxonScope, spec_for
from migratlas.ingest.http import RemoteFile
from migratlas.lake.writer import WriteResult, write_evidence
from migratlas.redact import admit_taxon_for_ingest
from migratlas.taxonomy import gbif

if TYPE_CHECKING:
    from pathlib import Path

    import pyarrow as pa

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Scheme:
    """One of the programme's two surveys, and where its archive lives."""

    source_id: str
    archive: RemoteFile
    protocol: str
    """Expected `samplingProtocol`, checked against what arrives rather than trusted."""


SCHEMES: Final[tuple[Scheme, ...]] = (
    Scheme(
        "sbs_point_counts",
        RemoteFile(
            url="https://www.gbif.se/ipt/archive.do?r=lu_sft_spkt", name="sbs-spkt-dwca.zip"
        ),
        "point transect survey",
    ),
    Scheme(
        "sbs_fixed_routes",
        RemoteFile(url="https://www.gbif.se/ipt/archive.do?r=lu_sft_std", name="sbs-std-dwca.zip"),
        "line transect survey",
    ),
)

BY_SOURCE: Final[dict[str, Scheme]] = {scheme.source_id: scheme for scheme in SCHEMES}

WITHHELD: Final[frozenset[str]] = frozenset(
    {
        # Birds at Swedish security class 4 or higher, withheld from both schemes.
        "Ciconia nigra",
        "Anser erythropus",
        "Aquila chrysaetos",
        "Clanga clanga",
        "Haliaeetus albicilla",
        "Circus macrourus",
        "Circus pygargus",
        "Falco peregrinus",
        "Falco rusticolus",
        "Bubo bubo",
        "Dendrocopos leucotos",
        # Mammals, withheld from the fixed routes, which record them.
        "Lynx lynx",
        "Canis lupus",
        "Ursus arctos",
        "Gulo gulo",
        "Vulpes lagopus",
    }
)
"""Taxa the publisher removed before publishing, listed so the ingest can drop them by name.

Not a filter of ours and not a disagreement with theirs. The point is that these species are absent
from every event in the archive, so any absence derived for them is manufactured -- see the module
docstring. Named rather than inferred, because a species that is simply rare in Sweden would look
identical to a withheld one from the data alone.
"""


SYNONYMS: Final[dict[str, str]] = {
    # The European greenfinch, and a cross-kingdom homonym rather than a taxonomy problem: *Chloris*
    # is also a grass genus, so the Backbone answers `matchType: NONE` with the note "Multiple equal
    # matches for Chloris chloris" and the resolver rightly refuses it. Appending the authority
    # disambiguates to key 5845582, ACCEPTED, Aves, at confidence 100 -- checked against
    # /species/match before being written here, as SABAP1's table requires of its own entries.
    #
    # This is a weakness in `taxonomy/gbif.py` rather than in either source: `match_name` sends no
    # kingdom hint, so any animal sharing a binomial with a plant fails the same way. Recorded in
    # docs/TASKS.md rather than fixed here, because it is a shared resolver and every adapter's keys
    # would have to be re-checked.
    "Chloris chloris": "Chloris chloris (Linnaeus, 1758)",
}
"""Names the GBIF Backbone cannot resolve as written, and what to ask it instead.

Keyed by the *source's* name, so nothing downstream needs to know a replacement was made.
"""


def extract(scheme: Scheme) -> tuple[Path, Path]:
    """Fetch the archive once and unpack the event core and the occurrence extension beside it."""
    import zipfile  # noqa: PLC0415 -- only this function needs it

    from migratlas.ingest.http import fetch  # noqa: PLC0415 -- avoids a cycle at import time

    archive = fetch(scheme.archive, scheme.source_id)
    parts = []
    for member in ("event.txt", "occurrence.txt"):
        target = archive.parent / f"{scheme.source_id}-{member}"
        if not target.exists() or target.stat().st_size == 0:
            log.info("unpacking %s", member)
            with (
                zipfile.ZipFile(archive) as bundle,
                bundle.open(member) as source,
                target.open("wb") as sink,
            ):
                while chunk := source.read(1 << 22):
                    sink.write(chunk)
        parts.append(target)
    return parts[0], parts[1]


def _hours(column: str) -> pl.Expr:
    """Survey duration from the archive's `HH:MM/HH:MM` window, in hours.

    Null rather than zero when the window is missing or malformed: the schema allows an absent
    effort, and a zero would divide into infinity somewhere downstream.
    """
    start = pl.col(column).str.split("/").list.first().str.strptime(pl.Time, "%H:%M", strict=False)
    end = pl.col(column).str.split("/").list.last().str.strptime(pl.Time, "%H:%M", strict=False)
    span = (end.cast(pl.Duration("us")) - start.cast(pl.Duration("us"))).dt.total_minutes() / 60.0
    # A window crossing midnight would come out negative. None of these do -- dawn surveys, all of
    # them -- so a negative value means something else is wrong and is dropped rather than wrapped.
    return pl.when(span > 0).then(span).otherwise(None)


def read_visits(scheme: Scheme, event: Path, occurrence: Path) -> pl.DataFrame:
    """One row per species per route-visit, joined to its event and screened."""
    events = (
        pl.read_csv(
            event,
            separator="\t",
            quote_char=None,
            columns=[
                "eventID",
                "eventDate",
                "eventTime",
                "samplingProtocol",
                "locality",
                "decimalLatitude",
                "decimalLongitude",
            ],
            schema_overrides={"eventID": pl.String, "locality": pl.String},
            infer_schema_length=20000,
        )
        .with_columns(
            # `1996-05-23/1996-05-23` -- a range, and always a single day in both schemes.
            started=pl.col("eventDate")
            .str.split("/")
            .list.first()
            .str.to_datetime("%Y-%m-%d", time_zone="UTC", strict=False)
            .dt.cast_time_unit("ms"),
            ended=pl.col("eventDate")
            .str.split("/")
            .list.last()
            .str.to_datetime("%Y-%m-%d", time_zone="UTC", strict=False)
            .dt.cast_time_unit("ms"),
            hours=_hours("eventTime"),
        )
        .filter(
            pl.col("started").is_not_null(),
            pl.col("decimalLatitude").is_not_null(),
            pl.col("decimalLongitude").is_not_null(),
            pl.col("locality").is_not_null(),
        )
    )
    protocols = set(events["samplingProtocol"].drop_nulls().unique().to_list())
    if protocols != {scheme.protocol}:
        # Not fatal: a new protocol is news rather than a failure. But it changes what a count
        # means, so it cannot pass silently.
        log.warning(
            "%s carries protocols %s, registered for %r",
            scheme.source_id,
            sorted(protocols),
            scheme.protocol,
        )

    records = pl.read_csv(
        occurrence,
        separator="\t",
        quote_char=None,
        columns=["eventID", "scientificName", "individualCount", "recordedBy", "occurrenceStatus"],
        schema_overrides={
            "eventID": pl.String,
            "scientificName": pl.String,
            "recordedBy": pl.String,
        },
        infer_schema_length=20000,
    )
    total = records.height

    withheld = records.filter(pl.col("scientificName").is_in(WITHHELD)).height
    if withheld:
        # Reachable only if the publisher changes what they redact, which is worth hearing about.
        log.warning(
            "%s: %d rows for taxa listed as withheld -- the redaction has changed",
            scheme.source_id,
            withheld,
        )

    records = records.filter(
        pl.col("scientificName").is_not_null(),
        ~pl.col("scientificName").is_in(WITHHELD),
        pl.col("individualCount").is_not_null(),
        # Every row in both archives is `present`; a future `absent` is real information and must
        # not be silently counted as a sighting.
        pl.col("occurrenceStatus").str.to_lowercase() == "present",
    )
    if total != records.height:
        log.info("  %d of %d occurrence rows dropped", total - records.height, total)

    joined = records.join(events, on="eventID", how="inner")
    log.info(
        "  %d visits, %d species rows, %d routes, %s to %s",
        events.height,
        joined.height,
        joined["locality"].n_unique(),
        joined["started"].min(),
        joined["started"].max(),
    )
    return joined


def screen_taxa(source_id: str, frame: pl.DataFrame) -> list[str]:
    """Every taxon past the never-ingested floor before anything is written."""
    names = sorted(frame["scientificName"].drop_nulls().unique().to_list())
    for name in names:
        admit_taxon_for_ingest(source_id, scientific_name=name)
    return names


def to_evidence(scheme: Scheme, frame: pl.DataFrame, keys: dict[str, int]) -> pa.Table:
    """Adapt to the canonical `survey_index` schema."""
    shaped = frame.select(
        source_id=pl.lit(scheme.source_id),
        realm=pl.lit(str(Realm.TERRESTRIAL)),
        taxon_scope=pl.lit(str(TaxonScope.EXACT)),
        taxon_key=pl.col("scientificName").replace_strict(
            keys, default=None, return_dtype=pl.Int64
        ),
        taxon_label=pl.col("scientificName"),
        site_id=pl.col("locality"),
        period_start=pl.col("started"),
        period_end=pl.col("ended"),
        site_longitude=pl.col("decimalLongitude").cast(pl.Float64),
        site_latitude=pl.col("decimalLatitude").cast(pl.Float64),
        site_depth_m=pl.lit(None, dtype=pl.Float64),
        count=pl.col("individualCount").cast(pl.Float64),
        effort=pl.col("hours"),
        effort_unit=pl.lit("survey hours"),
        # The observer travels with the protocol, as it does for BBS: observer skill is the best
        # documented bias in a scheme like this, and a trend fit needs it as a break term.
        protocol=pl.col("samplingProtocol")
        + pl.lit("; ")
        + pl.col("recordedBy").fill_null("unknown"),
    )
    schema = spec_for(EvidenceType.SURVEY_INDEX).schema
    return shaped.select(schema.names).to_arrow().cast(schema)


def taxon_keys(source_id: str, names: list[str]) -> dict[str, int]:
    """Resolve scientific names to GBIF Backbone keys, cached between runs.

    Cached per source under the same convention SABAP1 uses: these are a few hundred names and the
    Backbone is a remote service, so a re-run should not re-ask it.
    """
    import json  # noqa: PLC0415 -- only this function needs it

    from migratlas.config import get_settings  # noqa: PLC0415 -- avoids a cycle

    cache = get_settings().cache_dir / f"{source_id}_taxon_keys.json"
    known: dict[str, int] = {}
    if cache.exists():
        known = {str(k): int(v) for k, v in json.loads(cache.read_text(encoding="utf-8")).items()}

    missing = sorted({name for name in names if name and name not in known})
    if missing:
        log.info("resolving %d names against the GBIF Backbone", len(missing))
        with gbif.client() as http:
            for name in missing:
                try:
                    known[name] = gbif.match_name(http, SYNONYMS.get(name, name)).usage_key
                except (gbif.TaxonomyError, OSError) as error:
                    log.debug("unresolved %r: %s", name, error)
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(known, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return known


def ingest_scheme(source_id: str, root: Path | None = None) -> WriteResult:
    """Land one scheme. Idempotent: the download is cached and the write replaces its partitions."""
    scheme = BY_SOURCE[source_id]
    source = catalog.admit(source_id)
    log.info("ingesting %s (%s)", source.title, source.licence)

    event, occurrence = extract(scheme)
    frame = read_visits(scheme, event, occurrence)

    names = screen_taxa(source_id, frame)
    keys = taxon_keys(source_id, names)
    unresolved = [name for name in names if name not in keys]
    if unresolved:
        log.warning(
            "%s: %d names unresolved, landing as null keys: %s",
            source_id,
            len(unresolved),
            unresolved[:8],
        )

    shaped = to_evidence(scheme, frame, keys)
    log.info("  %d rows, %d taxa", shaped.num_rows, len(names))
    return write_evidence(
        shaped, spec_for(EvidenceType.SURVEY_INDEX), source_id=source_id, root=root
    )


def ingest(root: Path | None = None) -> list[WriteResult]:
    """Both schemes."""
    return [ingest_scheme(scheme.source_id, root=root) for scheme in SCHEMES]
