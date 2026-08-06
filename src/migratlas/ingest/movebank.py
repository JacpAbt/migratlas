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

# --- Fixes the animal cannot have reached ---------------------------------------
#
# Three things in this data are not the animal moving, and one filter removes all three because they
# are one fault: a run of fixes that cannot be reached from the rest of the track.
#
# **617 rows of the Missouri bison study sit at 52.43N, 13.52E, which is Berlin.** Five collars,
# ``Padme_PSP`` through ``Polly_PSP``, 116 to 132 fixes each between 2022-08-26 and 2022-08-31, then
# ~26,000 fixes each in Missouri from 2022-09-27. Collars bench-tested at the manufacturer, shipped,
# and fitted -- under the *same* ``individual_local_identifier``, carrying a ``deployment_id``,
# marked ``visible = true``, so nothing in the filters above rejects them.
#
# **The same collars were then driven west.** On 2022-10-17 ``Paige_PSP`` reports hourly from St
# Louis, then runs (38.44,-90.90), (37.95,-91.79), (37.51,-92.84), (37.25,-93.25), (37.39,-94.06),
# (37.53,-94.57) -- 90 km an hour in a straight line to the Kansas border. That is a truck. It was
# not in this comment before because nobody had looked at the middle of the study, only at Berlin.
#
# **Two Bylot fox fixes sit at 136E and 152E**, one per animal, with no approach or departure, which
# is what a bad Argos position looks like.
#
# Two earlier attempts and why each failed, kept because they bound the design:
#
# - *Drop rows far from the study median.* Removes Berlin, and deletes 112 fixes of Arctic fox
#   ``MMRV`` -- 1,502 fixes, five years at Bylot, then a connected westward path to the Mackenzie
#   Delta, roughly 3,000 km. Documented dispersal, and the most remarkable movement record in this
#   lake. It left the animal looking sedentary.
# - *Drop animals never seen near the study median.* Keeps MMRV, and keeps Berlin, because the
#   bench-test fixes share an animal id with that animal's real Missouri track.
#
# The discriminator both miss is implied speed between consecutive fixes. Measured on the seven
# cached studies before any threshold was chosen, two things about it are not obvious:
#
# **Raw implied speed is unusable.** Thousands of pairs sit under a minute apart, where a hundred
# metres of GPS scatter implies hundreds of km per day: an elk pair 18.2 km apart with a
# rounded-away gap reads as 82,694 km/day, and the bison study's 99th percentile is 1,028 km/day. So
# a break has to clear a *distance* as well as a speed -- ``MIN_JUMP_KM`` -- and every real artefact
# here is hundreds or thousands of km, while no scatter is fifty.
#
# **The decision is per segment, not per row.** Berlin is internally consistent; only the crossing
# into Missouri is fast. Dropping "the row after a fast pair" would delete the first Missouri fix
# and keep all 132 Berlin ones. So the track is cut at every break and whole stretches are judged.
#
# What decides a stretch is *where* it is, not how big it is -- ``MAX_STRAY_KM`` says why, and says
# which two versions of this deleted real data before landing there. MMRV survives whole because its
# 3,000 km dispersal is connected: its fastest step is 127.9 km/day against a ceiling of 160, so it
# is never cut in the first place.
#
# On the seven cached studies this removes 1,377 rows of 6,047,093 -- 0.023%. The bison study loses
# 1,362 of them: the 617 Berlin rows and 745 more from the drive west. The other 15 are bad
# positions, one to three per animal in the two fox studies, and four studies lose nothing at all.
# All 52 bison individuals remain, and so do all 1,502 of MMRV's fixes across its full range.

MIN_JUMP_KM: Final = 50.0
"""How far apart two fixes must be before their implied speed is allowed to mean anything.

Not a tuning knob, a floor on the measurement. Movebank timestamps here are minute-resolution and
some pairs share one, so the denominator can be zero or nearly so while the numerator is GPS
scatter. Every artefact this filter exists for is a displacement of hundreds to thousands of km.
"""

MAX_STRAY_KM: Final = 100.0
"""How far an unreachable stretch may sit from the animal's own main record and still be believed.

This is the whole discriminator, and it took two wrong versions to get to. Berlin is 7,150 km from
its collar's Missouri track and the transport leg some 380 km; Bylot fox ``OBBB``'s isolated four
days are in the same 200 m of tundra as the rest of its life.

Size is not a substitute and cannot be made into one. Judging a stretch by its *share* of the
animal's record deleted 1,176 real fixes of ``OBBB`` -- 107,229 in total, so a genuine four-day stay
with one bad position on each side came to 1.1% and lost. Judging it by an absolute *count* deletes
short segments near home and empties any track shorter than the count. Neither can tell a displaced
stay from a real one that was merely cut off; distance is the only thing that can.

It is the "distance from the median" idea that failed on its own, and it failed because MMRV's
3,000 km dispersal is *connected*. Measured against a segment rather than against a whole animal,
the connectivity has already been established by the step test before this is asked.
"""

MAX_KM_PER_DAY: Final[dict[str, float]] = {
    "Vulpes lagopus": 160.0,
    "Canis lupus": 200.0,
    "Rangifer tarandus": 120.0,
    "Cervus elaphus": 120.0,
    "Bison bison": 80.0,
}
"""Fastest sustained daily displacement each taxon is credited with.

Plausibility bounds, not published maxima, and deliberately generous: this filter can delete real
data, so it is set to catch a truck and a bench test rather than to police ecology. Each is well
above what the cached studies show for that taxon -- the Arctic fox figure is the one with a record
behind it, Fuglei and Tarroux's Svalbard-to-Ellesmere disperser at about 155 km/day on sea ice, and
the fox here tops out at 127.9.

A single global ceiling cannot work: set for a bison it would delete the fox's dispersal, and set
for the fox it would keep Berlin, whose crossing is 7,150 km in 27.0 days -- 265 km/day.
"""

DEFAULT_KM_PER_DAY: Final = 250.0
"""For a taxon with no entry above.

Higher than any terrestrial mammal sustains, so an unlisted taxon loses only the grossest artefacts
rather than silently losing real movement -- and `test_ingest_movebank.py` fails if a registered
study's species has no explicit ceiling.
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
    frame = (
        frame.with_columns(
            # Parsed here rather than in the adapter, so the span check and the written rows agree
            # about
            # which timestamps are usable instead of each deciding separately.
            pl.col("timestamp")
            .str.to_datetime("%Y-%m-%d %H:%M:%S%.f", time_zone="UTC", strict=False)
            .dt.cast_time_unit("ms")
        )
        .filter(
            pl.col("location_lat").is_not_null(),
            pl.col("location_long").is_not_null(),
            pl.col("individual_local_identifier").is_not_null(),
            pl.col("timestamp").is_not_null(),
            # The two filters that make this the study's data rather than everything its tags ever
            # sent.
            # `visible` is the owners' own outlier flag and `deployment_id` says a collar was on an
            # animal. Both are reported below, because the fraction they remove is a property of the
            # study worth seeing -- for Bylot Argos it is 91%.
            pl.col("deployment_id").is_not_null(),
            pl.col("visible"),
        )
        .with_columns(
            # Wrapped into range before anything measures a distance with it. Two Bylot fox fixes
            # arrive
            # at -207 and -223 degrees, which are not coordinates -- and they broke the
            # detectability
            # grid encoder, which decodes an index back to a longitude and got -223.5.
            # Cast first: an empty study infers the column as string and the arithmetic fails, which
            # is
            # reachable -- a study whose every fix is a flagged outlier parses to nothing.
            location_long=(pl.col("location_long").cast(pl.Float64) + 180) % 360 - 180
        )
    )
    if total != frame.height:
        dropped = total - frame.height
        log.info("  %d of %d rows dropped (%.0f%%)", dropped, total, 100 * dropped / total)
    return frame


EARTH_KM: Final = 6371.0088
"""Mean Earth radius. A sphere is right to well under the precision this filter needs."""


def _implied(frame: pl.DataFrame) -> pl.DataFrame:
    """Great-circle distance and implied speed from each fix to the previous one of the same animal.

    Haversine rather than a projected distance, because these tracks run to 83N where a planar
    approximation is wrong by more than the thing being measured.
    """
    over = "individual_local_identifier"
    return (
        frame.sort(over, "timestamp")
        .with_columns(
            _lat=pl.col("location_lat").cast(pl.Float64).radians(),
            _lon=pl.col("location_long").cast(pl.Float64).radians(),
        )
        .with_columns(
            _plat=pl.col("_lat").shift().over(over),
            _plon=pl.col("_lon").shift().over(over),
            _days=pl.col("timestamp").diff().over(over).dt.total_seconds() / 86_400,
        )
        .with_columns(
            _km=2
            * EARTH_KM
            * (
                (
                    ((pl.col("_lat") - pl.col("_plat")) / 2).sin() ** 2
                    + pl.col("_plat").cos()
                    * pl.col("_lat").cos()
                    * ((pl.col("_lon") - pl.col("_plon")) / 2).sin() ** 2
                )
                .sqrt()
                .arcsin()
            )
        )
    )


SCRATCH: Final = (
    "_lat",
    "_lon",
    "_plat",
    "_plon",
    "_days",
    "_km",
    "_ceiling",
    "_break",
    "_segment",
)


def _cut(frame: pl.DataFrame) -> pl.DataFrame:
    """Label each animal's track with the segment number an impossible step puts it in.

    A **break** is a step clearing both ``MIN_JUMP_KM`` and the taxon's ceiling: far enough to be a
    change of place rather than scatter, and faster than the animal travels. A shared or
    rounded-away timestamp with a real displacement is a break by definition, being infinitely fast.
    """
    over = "individual_local_identifier"
    return (
        _implied(frame)
        .with_columns(
            _ceiling=pl.col("individual_taxon_canonical_name").replace_strict(
                MAX_KM_PER_DAY, default=DEFAULT_KM_PER_DAY, return_dtype=pl.Float64
            )
        )
        .with_columns(
            _break=(
                (pl.col("_km") > MIN_JUMP_KM)
                & (
                    (pl.col("_days") <= 0)
                    | ((pl.col("_km") / pl.col("_days")) > pl.col("_ceiling"))
                )
            )
            # The first fix of an animal has no predecessor, so it cannot be a break.
            .fill_null(value=False)
        )
        .with_columns(_segment=pl.col("_break").cum_sum().over(over))
    )


def unreachable(frame: pl.DataFrame) -> pl.DataFrame:
    """Drop stretches of fixes the animal could not have reached from the rest of its own record.

    The track is cut at every impossible step and whole stretches are judged, because the fault is a
    run of fixes and not a row. Berlin is internally consistent and only its crossing into Missouri
    is fast, so any rule that dropped "the row after a fast step" would delete the first Missouri
    fix and keep all 132 Berlin ones.

    A stretch is dropped when it is **somewhere the animal was not** -- further than `MAX_STRAY_KM`
    from the centre of its own largest stretch -- or when it is a **lone fix**, unreachable from the
    neighbour on either side, which is a bad position wherever it landed.

    Then it runs again. Removing a bad position heals the two breaks it caused, so the stretches
    either side of it rejoin and are re-measured together; without the second pass, a stretch
    bracketed by two bad positions is judged on a length it only has because they were there. Three
    passes at most -- the loop stops when a pass removes nothing, which on the cached studies is the
    second or third.
    """
    if frame.is_empty():
        return frame

    over = "individual_local_identifier"
    total = frame.height
    working = frame
    for _ in range(3):
        cut = _cut(working)
        # Where the animal actually lived: the centre of its largest stretch, which is the only
        # reference point the step test has already established the animal can move within.
        home = (
            cut.group_by(over, "_segment")
            .agg(n=pl.len(), lat=pl.col("_lat").mean(), lon=pl.col("_lon").mean())
            .sort("n", descending=True)
            .group_by(over)
            .first()
            .select(over, _home_lat="lat", _home_lon="lon")
        )
        judged = (
            cut.join(home, on=over, how="left")
            .with_columns(
                _size=pl.len().over(over, "_segment"),
                _pieces=pl.col("_segment").n_unique().over(over),
            )
            .with_columns(
                _stray=2
                * EARTH_KM
                * (
                    (
                        (
                            (pl.col("_lat").mean().over(over, "_segment") - pl.col("_home_lat")) / 2
                        ).sin()
                        ** 2
                        + pl.col("_home_lat").cos()
                        * pl.col("_lat").mean().over(over, "_segment").cos()
                        * (
                            (pl.col("_lon").mean().over(over, "_segment") - pl.col("_home_lon")) / 2
                        ).sin()
                        ** 2
                    )
                    .sqrt()
                    .arcsin()
                )
            )
        )
        # Two ways to lose. Straying is the general one; a lone fix is the textbook one, a position
        # unreachable from the neighbour on each side and so a bad position wherever it landed.
        #
        # `_pieces` is what stops the second from meaning "an animal with one fix". Five caribou
        # in the South Peace study have exactly one location each, and a single fix has no
        # neighbours to be unreachable from -- without this they went as spikes and the withheld
        # page dropped from 260 animals to 255. An animal's only stretch is never a spike.
        survivors = judged.filter(
            (pl.col("_stray") <= MAX_STRAY_KM) & ((pl.col("_size") > 1) | (pl.col("_pieces") == 1))
        )
        if survivors.height == working.height:
            break
        working = survivors.drop(*SCRATCH, "_home_lat", "_home_lon", "_size", "_pieces", "_stray")

    dropped = total - working.height
    if dropped:
        # Named, because a filter that can delete a real track has to say what it took, and the
        # per-animal counts are what a reader checks against the study's own description.
        worst = (
            frame.join(working, on=frame.columns, how="anti", nulls_equal=True)
            .group_by(over)
            .agg(n=pl.len())
            .sort("n", descending=True)
            .head(6)
        )
        log.info(
            "  %d of %d rows unreachable (%.2f%%): %s",
            dropped,
            total,
            100 * dropped / total,
            ", ".join(f"{row[0]} {row[1]}" for row in worst.iter_rows()),
        )
    return working


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


def named(source_id: str, frame: pl.DataFrame) -> pl.DataFrame:
    """Drop rows whose species the archive never recorded, and say how many there were.

    This used to be a ``drop_nulls()`` inside `screen_taxa`, which meant the floor was asked about
    every taxon *except* the rows that had none -- and those went into the lake: 10,438 fixes of one
    Ya Ha Tinda elk and 3,528 of seven Missouri bison, 13,966 in all, never screened. The floor
    refuses an unnamed row now, so hiding them from it is no longer possible; this is the adapter
    declining to hand it something it cannot answer, out loud.

    Dropped rather than fatal, and the difference is what is actually at risk. A *human* row means
    the taxon field is not what the ingest assumes and the whole study needs a person; a row with no
    taxon means one animal's species was never typed in. Refusing the study would lose 2.5 million
    good fixes over eight animals, and keeping them would put positions in the lake that no
    sensitivity rule can reach -- because a rule is per taxon, and there is no taxon.
    """
    unnamed = frame.filter(pl.col("individual_taxon_canonical_name").is_null())
    if unnamed.is_empty():
        return frame
    animals = unnamed["individual_local_identifier"].unique().sort().to_list()
    log.warning(
        "  %s: %d rows carry no taxon and cannot be screened, dropping %d animal(s): %s",
        source_id,
        unnamed.height,
        len(animals),
        ", ".join(animals[:8]),
    )
    return frame.filter(pl.col("individual_taxon_canonical_name").is_not_null())


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
    parsed = parse(body)

    # Rows with no taxon go first, because the floor now refuses one and it is right to: a gate
    # asked about nothing cannot answer. `named` says how many and which animals.
    parsed = named(source_id, parsed)

    # Then the floor screens what the study *contains*, before anything is dropped for being
    # unreachable. A human row that the reachability filter happened to isolate must still stop the
    # ingest: this gate is about what the taxon field says, and a filter may not answer it.
    names = screen_taxa(source_id, parsed)

    frame = unreachable(parsed)

    # Measured on what survives, not on what arrived. A study whose only early fixes are a bench
    # test would otherwise report a span it does not have.
    span = span_years(frame)
    if span < MIN_STUDY_YEARS:
        msg = (
            f"{source_id} spans {span} year(s), under the {MIN_STUDY_YEARS}-year floor. A study "
            f"shorter than the annual cycle cannot inform an annual date."
        )
        raise ValueError(msg)

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
