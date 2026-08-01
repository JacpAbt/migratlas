"""Movebank tracks: the lake's first individual-granularity evidence.

Seven studies registered as seven sources, each with its own licence and its own per-taxon
sensitivity. Pre-registered in ``docs/methods/phase1d-tracks.md``; the source assessment and the
enumeration that found them are in ``docs/methods/tracks-and-sensitivity.md``.

Three things about this API cost a run each to discover, and all three are load-bearing here.

**Events are served only after a licence handshake.** The first request returns the study's terms as
HTML; the same request carrying ``license-md5`` set to the md5 of *exactly those bytes* returns the
CSV. That digest is the acceptance, so it is stored beside the data rather than thrown away --
accepting a licence is an act, and provenance should record which text was accepted. A study whose
terms change produces a different digest, and this refuses it until someone reads the new ones.

**There is no cheap sample.** ``max_events_per_individual`` is silently ignored: a request for two
events per animal returned the whole 1.8-million-row study. A study is all-or-nothing, so responses
are cached to the raw archive and never re-fetched.

**A study name is not an identifier.** Studies are addressed by numeric id throughout. Resolving
``"Ya Ha Tinda elk"`` by name returns a ``CUSTOM``-licensed duplicate before the CC0 study, and
``Canis lupus`` matches stray dogs and livestock guardians alongside wolves.
"""

import hashlib
import io
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import httpx
import polars as pl

from migratlas.catalog import loader as catalog
from migratlas.config import get_settings
from migratlas.evidence import EvidenceType, spec_for
from migratlas.ingest.http import USER_AGENT
from migratlas.lake.writer import write_evidence
from migratlas.redact import admit_taxon_for_ingest
from migratlas.taxonomy import gbif

if TYPE_CHECKING:
    from pathlib import Path

    import pyarrow as pa

    from migratlas.lake.writer import WriteResult

log = logging.getLogger(__name__)

API: Final = "https://www.movebank.org/movebank/service/direct-read"

ATTRIBUTES: Final = (
    "individual_local_identifier,timestamp,location_lat,location_long,"
    "individual_taxon_canonical_name,sensor_type_id,deployment_id,visible"
)
"""`deployment_id` and `visible` are not optional, and leaving them out is a silent disaster.

The event endpoint returns every fix a tag ever transmitted. For the Bylot Argos study that is
696,640 rows against the 64,489 the study metadata calls *deployed locations* -- and the difference
is not padding. **618,915 of the 694,103 positioned rows are `visible = false`**, Movebank's own
outlier flag, and a further 87,000 carry no `deployment_id` at all: fixes from before a collar was
fitted, after it came off, or while it sat in a lab.

Filtering on both reproduces the published count exactly. Without them the first ingest landed
607,135 rows, 89% of them positions the data owners had already marked as wrong.
"""

SENSOR_NAMES: Final[dict[str, str]] = {
    "397": "Bird Ring",
    "653": "GPS",
    "673": "Radio Transmitter",
    "2365682": "Natural Mark",
    "3886361": "Solar Geolocator",
    "82798": "Argos Doppler Shift",
    "1239574236": "Acoustic Telemetry",
    "2299894820": "Sigfox Geolocation",
    "3090218812": "Geolocation API",
    "3090218818": "GNSS",
    "4342918458": "ATLAS Geolocation",
}
"""Movebank's location-sensor ids, from ``entity_type=tag_type``, resolved rather than guessed.

The event API returns ``sensor_type_id`` as a bare number: the caribou study's two instruments come
back as 653 and 673. Stored as names, because this column exists so a reader can see an instrument
change -- and "GPS against Radio Transmitter, 46.8 days apart" is a warning where "653 against 673"
is a puzzle.

Only the location sensors. Accelerometers and barometers appear in these studies too but never carry
a position, so they cannot reach a row that survived the position filter.
"""

MIN_STUDY_YEARS: Final = 2
"""A study spanning less than this contributes nothing and is refused.

Not a tuning knob. ``Dolphin_Union_Caribou_UAV`` is three days long and holds 450,042 locations --
more than the 29-year caribou study -- because it is an aerial survey rather than tracking. Pooled,
it would dominate a cell with a single instant, which is the MegaMove failure exactly. A study
shorter than the annual cycle cannot inform an annual date, so the rule is stated in those terms
rather than as a threshold that happened to exclude one file.
"""


@dataclass(frozen=True, slots=True)
class Study:
    """One Movebank study, and the source it lands under."""

    source_id: str
    study_id: int
    species: str
    """Expected canonical name. Checked against what arrives, not trusted."""


STUDIES: Final[tuple[Study, ...]] = (
    Study("movebank_yahatinda_elk", 897981076, "Cervus elaphus"),
    Study("movebank_mountain_caribou_bc", 216040785, "Rangifer tarandus"),
    Study("movebank_missouri_bison", 8019591, "Bison bison"),
    Study("movebank_bylot_fox_gps", 1241071371, "Vulpes lagopus"),
    Study("movebank_bylot_fox_argos", 942774711, "Vulpes lagopus"),
    Study("movebank_svalbard_reindeer", 2608802883, "Rangifer tarandus"),
    Study("movebank_hebblewhite_wolves", 209824313, "Canis lupus"),
)

BY_SOURCE: Final[dict[str, Study]] = {study.source_id: study for study in STUDIES}


class LicenceChangedError(RuntimeError):
    """A study's terms differ from the ones recorded as accepted."""


def _auth() -> tuple[str, str]:
    settings = get_settings()
    return settings.credential("movebank_user"), settings.credential("movebank_password")


def _looks_like_data(body: str) -> bool:
    """Movebank answers with either a CSV header or an HTML licence page."""
    return body.lstrip().lower().startswith(("individual_local_identifier", '"individual'))


def fetch(study: Study, *, accepted_digest: str | None = None) -> tuple[str, str, str]:
    """Return ``(csv, licence_text, digest)`` for one study, accepting its terms.

    The digest is of the licence page exactly as served. Passing ``accepted_digest`` asserts the
    terms have not changed since they were last read, and refuses the study if they have -- a
    licence that changed under a cached acceptance is a licence nobody has agreed to.
    """
    params = {
        "entity_type": "event",
        "study_id": str(study.study_id),
        "attributes": ATTRIBUTES,
    }
    with httpx.Client(
        timeout=httpx.Timeout(60.0, read=1800.0),
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        first = client.get(API, params=params, auth=_auth())
        first.raise_for_status()
        if _looks_like_data(first.text):
            # No terms to accept: nothing was withheld, so nothing was agreed to.
            return first.text, "", ""

        licence = first.text
        digest = hashlib.md5(licence.encode(), usedforsecurity=False).hexdigest()
        if accepted_digest is not None and digest != accepted_digest:
            msg = (
                f"{study.source_id}: the study's licence text has changed "
                f"({accepted_digest} -> {digest}). Read the new terms before ingesting again."
            )
            raise LicenceChangedError(msg)

        second = client.get(API, params={**params, "license-md5": digest}, auth=_auth())
        second.raise_for_status()
        if not _looks_like_data(second.text):
            msg = f"{study.source_id}: handshake accepted but no data returned"
            raise RuntimeError(msg)
        return second.text, licence, digest


def _raw_dir(source_id: str) -> Path:
    path = get_settings().raw_dir / source_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def cached(study: Study) -> tuple[str, str]:
    """The study's events and the digest of the terms accepted for them, fetching once.

    Cached because a study is an all-or-nothing download of up to 127 MB, and because the licence
    acceptance is recorded alongside: re-fetching would re-accept, and the second acceptance would
    be of whatever the terms say then rather than of what was read.
    """
    directory = _raw_dir(study.source_id)
    # The cache key carries the attribute set, so changing what is requested invalidates it. Without
    # this, adding `deployment_id` and `visible` left a cached CSV that parsed into a
    # ColumnNotFoundError several runs later, and the obvious reading of that error is that the API
    # changed rather than that the file on disk predates the fix.
    shape = hashlib.sha256(ATTRIBUTES.encode()).hexdigest()[:8]
    stem = f"study{study.study_id}.{shape}"
    events, terms, digest_file = (
        directory / f"{stem}.csv",
        directory / f"{stem}.licence.html",
        directory / f"{stem}.licence.md5",
    )
    if events.is_file() and digest_file.is_file():
        log.info("%s cached (%.1f MiB)", study.source_id, events.stat().st_size / 1024**2)
        return events.read_text(encoding="utf-8"), digest_file.read_text(encoding="utf-8").strip()

    log.info("%s fetching study %d", study.source_id, study.study_id)
    body, licence, digest = fetch(study)
    events.write_text(body, encoding="utf-8")
    digest_file.write_text(digest, encoding="utf-8")
    if licence:
        terms.write_text(licence, encoding="utf-8")
    log.info("%s %.1f MiB, licence digest %s", study.source_id, len(body) / 1024**2, digest or "-")
    return body, digest


def parse(body: str) -> pl.DataFrame:
    """Movebank's event CSV, with unusable rows dropped and counted.

    Rows with no fix are normal in this feed -- a transmission can carry a sensor reading and no
    position -- so they are dropped rather than treated as an error, but the count is logged because
    a study that is mostly positionless is a study that does not measure movement.
    """
    frame = pl.read_csv(
        io.StringIO(body),
        schema_overrides={
            "individual_local_identifier": pl.String,
            "individual_taxon_canonical_name": pl.String,
            "sensor_type_id": pl.String,
        },
        infer_schema_length=10000,
    )
    total = frame.height
    frame = frame.with_columns(
        # Parsed here rather than in the adapter, so the span check and the written rows agree about
        # which timestamps are usable instead of each deciding separately.
        pl.col("timestamp")
        .str.to_datetime("%Y-%m-%d %H:%M:%S%.f", time_zone="UTC", strict=False)
        .dt.cast_time_unit("ms")
    ).filter(
        pl.col("location_lat").is_not_null(),
        pl.col("location_long").is_not_null(),
        pl.col("individual_local_identifier").is_not_null(),
        pl.col("timestamp").is_not_null(),
        # The two filters that make this the study's data rather than everything its tags ever sent.
        # `visible` is the owners' own outlier flag and `deployment_id` says a collar was on an
        # animal. Both are reported below, because the fraction they remove is a property of the
        # study worth seeing -- for Bylot Argos it is 91%.
        pl.col("deployment_id").is_not_null(),
        pl.col("visible"),
    )
    if total != frame.height:
        dropped = total - frame.height
        log.info("  %d of %d rows dropped (%.0f%%)", dropped, total, 100 * dropped / total)
    return frame


def screen_taxa(source_id: str, frame: pl.DataFrame) -> list[str]:
    """Run every taxon in the study past the never-ingested floor before anything is written.

    Every distinct name, not the one the study advertises. Movebank's *Homo sapiens* rows sit inside
    multi-taxon animal studies -- "Poultry network Thailand 2022" lists fourteen taxa including a
    turtle, six raptors, *Canis lupus* and *Homo sapiens* -- so checking the study's headline
    species would check the wrong thing.

    Refuses rather than filters. A human row in a mammal study means the taxon field is not what the
    ingest assumes, and everything downstream of that assumption needs re-checking by a person.
    """
    names = sorted(frame["individual_taxon_canonical_name"].drop_nulls().unique().to_list())
    for name in names:
        admit_taxon_for_ingest(source_id, scientific_name=name)
    return names


def to_evidence(study: Study, frame: pl.DataFrame, keys: dict[str, int]) -> pa.Table:
    """Adapt to the canonical `track` schema."""
    source = catalog.get(study.source_id)
    shaped = frame.select(
        source_id=pl.lit(study.source_id),
        realm=pl.lit(str(source.realm)),
        taxon_scope=pl.lit(str(source.taxon_scope)),
        taxon_key=pl.col("individual_taxon_canonical_name").replace_strict(
            keys, default=None, return_dtype=pl.Int64
        ),
        taxon_label=pl.col("individual_taxon_canonical_name"),
        # Prefixed with the study, because two studies at Bylot use the same collar numbering and
        # pooling them would silently merge two foxes into one animal.
        individual_id=pl.format(
            "{}:{}", pl.lit(str(study.study_id)), "individual_local_identifier"
        ),
        timestamp=pl.col("timestamp"),
        longitude=pl.col("location_long").cast(pl.Float64),
        latitude=pl.col("location_lat").cast(pl.Float64),
        altitude_m=pl.lit(None, dtype=pl.Float64),
        location_error_m=pl.lit(None, dtype=pl.Float64),
        # Mapped to names, with the raw id kept where it is unknown rather than nulled: an
        # unrecognised sensor is something to notice, not something to hide.
        sensor_type=pl.col("sensor_type_id")
        .cast(pl.String)
        .replace(SENSOR_NAMES)
        .alias("sensor_type"),
    )

    schema = spec_for(EvidenceType.TRACK).schema
    return shaped.select(schema.names).to_arrow().cast(schema)


def taxon_keys(names: list[str]) -> dict[str, int]:
    """Resolve canonical names to GBIF usage keys, one lookup per distinct name."""
    with gbif.client() as http:
        return {name: gbif.match_name(http, name).usage_key for name in names}


def span_years(frame: pl.DataFrame) -> int:
    """Calendar years the study touches, inclusive. Zero for an empty frame rather than a crash."""
    if frame.is_empty():
        return 0
    year = pl.col("timestamp").dt.year()
    return int(frame.select(year.max() - year.min() + 1).item() or 0)


def ingest_study(source_id: str) -> WriteResult:
    """Land one study. Idempotent: the download is cached and the write replaces its partitions."""
    study = BY_SOURCE[source_id]
    source = catalog.admit(source_id)
    log.info("ingesting %s (%s)", source.title, source.licence)

    body, digest = cached(study)
    frame = parse(body)

    span = span_years(frame)
    if span < MIN_STUDY_YEARS:
        msg = (
            f"{source_id} spans {span} year(s), under the {MIN_STUDY_YEARS}-year floor. A study "
            f"shorter than the annual cycle cannot inform an annual date."
        )
        raise ValueError(msg)

    names = screen_taxa(source_id, frame)
    keys = taxon_keys(names)
    if names != [study.species]:
        # Not fatal on its own -- a study may legitimately carry more than one taxon -- but it means
        # the registry's sensitivity entries may not cover everything present, which is the exact
        # gap the per-taxon rule exists to close.
        log.warning("%s carries %s, registered for %s", source_id, names, study.species)
    classified = {rule.taxon_key for rule in source.taxon_sensitivity}
    unclassified = [name for name in names if keys[name] not in classified]
    if unclassified:
        log.warning(
            "%s: no sensitivity entry for %s, falling back to the default",
            source_id,
            unclassified,
        )

    shaped = to_evidence(study, frame, keys)
    log.info("  %d rows, %d years, licence digest %s", shaped.num_rows, span, digest or "-")
    return write_evidence(shaped, spec_for(EvidenceType.TRACK), source_id=source_id)


def ingest() -> list[WriteResult]:
    """Land every registered study."""
    return [ingest_study(study.source_id) for study in STUDIES]
