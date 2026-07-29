"""FISHGLOB: 29 harmonised bottom-trawl surveys, as SURVEY_INDEX.

The first source in the lake where **effort is fixed by design** rather than corrected for after
the fact. A scientific trawl survey tows the same gear over the same stratified stations in the
same season every year and records how far each haul swept, which is what makes a distribution
trend separable from the history of who was looking. See docs/methods/phase1b-marine.md for why
neither MegaMove nor OBIS can do that job.

Read from the per-survey files, not the compiled one. The compiled 88 MiB file carries a Latin-1
vessel name inside a haul id -- ``R\\xe9my-Martin``, from a French survey -- which makes pyreadr
fail on the entire file and the pure-Python reader take longer than ten minutes. The per-survey
files read cleanly in about a second each, and isolating them means one unreadable survey costs
one survey instead of all of them.
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import polars as pl

from migratlas.catalog import loader as catalog
from migratlas.config import get_settings
from migratlas.evidence import EvidenceType, Realm, TaxonScope, spec_for
from migratlas.ingest.http import RemoteFile, fetch
from migratlas.lake.writer import WriteResult, write_evidence
from migratlas.taxonomy import gbif

if TYPE_CHECKING:
    import pyarrow as pa

log = logging.getLogger(__name__)

SOURCE_ID: Final = "fishglob"
BASE: Final = "https://raw.githubusercontent.com/AquaAuma/FishGlob_data/main/outputs/Cleaned_data"

# The 29 public surveys, named as their files are. Listed rather than discovered so an ingest is
# reproducible from the repository state recorded here, not from whatever the branch holds today.
SURVEYS: Final[tuple[str, ...]] = (
    "AI",
    "BITS",
    "EBS",
    "EVHOE",
    "FR-CGFS",
    "GMEX",
    "GOA",
    "GSL-N",
    "GSL-S",
    "HS",
    "IE-IGFS",
    "NEUS",
    "NIGFS",
    "NOR-BTS",
    "NS-IBTS",
    "PT-IBTS",
    "QCS",
    "ROCKALL",
    "SCS",
    "SEUS",
    "SOG",
    "SP-ARSA",
    "SP-NORTH",
    "SP-PORC",
    "SWC-IBTS",
    "WCANN",
    "WCHG",
    "WCTRI",
    "WCVI",
)

# Columns the evidence rows need. Named explicitly so a schema change upstream fails loudly here
# rather than silently producing nulls.
NEEDED: Final[tuple[str, ...]] = (
    "survey_unit",
    "haul_id",
    "year",
    "month",
    "day",
    "latitude",
    "longitude",
    "depth",
    "num",
    "area_swept",
    # The three Alaska surveys report no raw catch and no swept area at all -- AFSC publishes
    # catch per unit area directly, and `num`/`area_swept` are 100% null in EBS, AI and GOA.
    # Without this column those three are lost, and they are the series the Bering Sea
    # distribution-shift literature is built on.
    "num_cpua",
    "gear",
    "accepted_name",
)

# The dates are built from year/month/day and not from the `timestamp` column, which is free text
# and not actually harmonised: HS writes "09/2020", NEUS writes a date. Nor are the dtypes
# harmonised across surveys -- `month` arrives as Int32, String or Float64 depending on the file,
# `day` is entirely null in the European series, and `gear` is an all-null column in HS. So every
# column is coerced to one type per survey before anything is concatenated.
NUMERIC: Final[tuple[str, ...]] = (
    "latitude",
    "longitude",
    "depth",
    "num",
    "area_swept",
    "num_cpua",
)
INTEGER: Final[tuple[str, ...]] = ("year", "month", "day")
TEXT: Final[tuple[str, ...]] = ("survey_unit", "haul_id", "gear", "accepted_name")

# Effort. `area_swept` is in square kilometres and is complete, where `haul_dur` is 20% null in
# the surveys checked -- so swept area is the effort measure and the unit is recorded with it.
EFFORT_UNIT: Final = "km2_swept"

# For the surveys that publish only catch-per-unit-area, the catch is already divided by effort, so
# effort is recorded as 1 and the unit says so. The centroid metric weights by count/effort, which
# then equals the published CPUA -- and because a weighted mean is invariant to a constant scaling
# of its weights, it does not matter whether the source's area unit is km2 or hectares. Only a
# comparison of levels between surveys would care, and surveys are never pooled.
PRESTANDARDISED_UNIT: Final = "cpua_prestandardised"


class SurveyUnreadableError(RuntimeError):
    """A survey file could not be read. Carries the survey, not a stack of reader internals."""


@dataclass(frozen=True, slots=True)
class SurveyRead:
    survey: str
    rows: int
    hauls: int
    species: int
    years: tuple[int, int]


def read_survey(survey: str) -> object:
    """Fetch and read one survey's cleaned file.

    Two readers, fast one first. pyreadr wraps librdata in C and reads 400,000 rows in under four
    seconds, but it assumes UTF-8 and dies on the Latin-1 vessel names in the French-Canadian
    series. The pure-Python reader accepts a forced encoding and took 12.7 s for GSL-N's 94,000
    rows -- too slow to use everywhere, exactly right as a fallback for the one file that needs it.

    Raises:
        SurveyUnreadableError: if both readers fail, so the caller can skip one survey.
    """
    import pyreadr  # noqa: PLC0415 -- an optional extra, and only this module needs it

    name = f"{survey}_clean.RData"
    path = fetch(RemoteFile(url=f"{BASE}/{name}", name=name), SOURCE_ID)
    try:
        objects = pyreadr.read_r(str(path))
    except UnicodeDecodeError:
        import rdata  # noqa: PLC0415 -- the slow path, imported only when it is needed

        log.info("  %s: not UTF-8, re-reading with a forced Latin-1 encoding", survey)
        try:
            objects = rdata.read_rda(path, default_encoding="latin1", force_default_encoding=True)
        except Exception as error:
            msg = f"{survey}: both readers failed: {type(error).__name__}: {str(error)[:90]}"
            raise SurveyUnreadableError(msg) from None
    except Exception as error:
        msg = f"{survey}: {type(error).__name__}: {str(error)[:120]}"
        raise SurveyUnreadableError(msg) from None

    frame = next(iter(objects.values()))
    missing = [column for column in NEEDED if column not in frame.columns]
    if missing:
        msg = f"{survey}: missing expected columns {missing}"
        raise SurveyUnreadableError(msg)
    return frame


def _haul_date() -> pl.Expr:
    """Haul date from the numeric parts, defaulting missing month and day to the first."""
    return pl.date(
        pl.col("year"),
        pl.col("month").fill_null(1).clip(1, 12),
        pl.col("day").fill_null(1).clip(1, 28),
    ).cast(pl.Datetime("ms", time_zone="UTC"))


def to_evidence(frame: pl.DataFrame, keys: dict[str, int]) -> pa.Table:
    """Reshape one survey's haul-by-species rows into SURVEY_INDEX rows.

    A haul is the site. Stations repeat in most of these surveys, but not all of them use fixed
    stations -- several are randomised within strata -- so the haul is the only identifier that
    means the same thing everywhere, and the position travels with it. Aggregating hauls into
    cells is the metric's job, where the footprint rule can be applied and reported.
    """
    resolved = frame.with_columns(
        taxon_key=pl.col("accepted_name").replace_strict(keys, default=None, return_dtype=pl.Int64)
    )
    unresolved = resolved.filter(pl.col("taxon_key").is_null())
    if unresolved.height:
        names = unresolved["accepted_name"].unique()
        log.warning(
            "  dropping %d rows for %d taxa with no GBIF key (e.g. %s)",
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
        taxon_label=pl.col("accepted_name"),
        # survey_unit prefixed so a station number cannot collide between two surveys.
        site_id=pl.col("survey_unit") + pl.lit(":") + pl.col("haul_id"),
        # Built from year/month/day, with missing parts defaulting to the first. Day is null for
        # every European survey, so haul dates are month-precision there and year-precision
        # nowhere -- which is enough, because the analysis is annual. Recording the real
        # precision beats inventing a day.
        period_start=_haul_date(),
        period_end=_haul_date(),
        site_longitude=pl.col("longitude").cast(pl.Float64),
        site_latitude=pl.col("latitude").cast(pl.Float64),
        site_depth_m=pl.col("depth").cast(pl.Float64),
        count=pl.col("num").cast(pl.Float64),
        effort=pl.col("area_swept").cast(pl.Float64),
        effort_unit=pl.col("effort_unit"),
        # Gear travels with the row because a gear change is a step change in the instrument, and
        # a break term cannot be fitted for something the lake did not keep.
        protocol=pl.col("survey_unit") + pl.lit(" gear=") + pl.col("gear").fill_null("unknown"),
    )
    schema = spec_for(EvidenceType.SURVEY_INDEX).schema
    return out.select(schema.names).to_arrow().cast(schema)


def taxon_keys(names: list[str]) -> dict[str, int]:
    """Resolve accepted scientific names to GBIF Backbone keys, cached between runs."""
    import json  # noqa: PLC0415 -- only this function needs it

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
                    known[name] = gbif.match_name(http, name).usage_key
                except (gbif.TaxonomyError, OSError) as error:
                    log.debug("unresolved %r: %s", name, error)
                if index % 200 == 0:
                    cache.parent.mkdir(parents=True, exist_ok=True)
                    cache.write_text(json.dumps(known, indent=1, sort_keys=True), encoding="utf-8")
                    log.info("  %d/%d", index, len(missing))
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(known, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return known


def prepare(survey: str) -> pl.DataFrame:
    """One survey as a polars frame with only the columns the evidence rows use."""
    # Typed as object: pandas has no stubs installed and is only ever handed straight to polars,
    # so importing it for one annotation would add a dependency the package does not otherwise use.
    pandas = read_survey(survey)
    frame = pl.from_pandas(pandas[list(NEEDED)]).with_columns(  # type: ignore[index]
        *[pl.col(c).cast(pl.Float64, strict=False) for c in NUMERIC],
        *[pl.col(c).cast(pl.String).cast(pl.Int32, strict=False) for c in INTEGER],
        *[pl.col(c).cast(pl.String) for c in TEXT],
    )
    # Surveys that publish only CPUA get their catch from there, with effort set to 1. Decided per
    # survey rather than per row: a mix within one survey would mean two different quantities in
    # one weighted mean.
    if frame["num"].is_null().all() and frame["num_cpua"].is_not_null().any():
        log.info("  %s: no raw catch, using published catch-per-unit-area", survey)
        frame = frame.with_columns(
            num=pl.col("num_cpua"),
            area_swept=pl.lit(1.0),
            effort_unit=pl.lit(PRESTANDARDISED_UNIT),
        )
    else:
        frame = frame.with_columns(effort_unit=pl.lit(EFFORT_UNIT))

    before = frame.height
    # A row with no position, no date or no catch cannot contribute to a distribution centroid.
    # Dropped with a count rather than carried as nulls into a weighted mean.
    frame = frame.filter(
        pl.col("latitude").is_not_null(),
        pl.col("longitude").is_not_null(),
        pl.col("year").is_not_null(),
        pl.col("num").is_not_null(),
        pl.col("area_swept").is_not_null(),
        pl.col("area_swept") > 0,
    )
    if frame.height != before:
        log.info("  %s: dropped %d of %d incomplete rows", survey, before - frame.height, before)
    return frame


def ingest(surveys: tuple[str, ...] = SURVEYS) -> WriteResult:
    """Fetch, reshape and land the surveys. Idempotent."""
    source = catalog.admit(SOURCE_ID)
    log.info("ingesting %s (%s)", source.title, source.licence)

    frames: list[pl.DataFrame] = []
    summaries: list[SurveyRead] = []
    skipped: list[str] = []

    for index, survey in enumerate(surveys, start=1):
        try:
            frame = prepare(survey)
        except SurveyUnreadableError as error:
            skipped.append(str(error))
            continue
        if frame.is_empty():
            skipped.append(f"{survey}: no usable rows")
            continue

        years = frame["year"].cast(pl.Int64).to_numpy()
        summaries.append(
            SurveyRead(
                survey=survey,
                rows=frame.height,
                hauls=frame["haul_id"].n_unique(),
                species=frame["accepted_name"].n_unique(),
                years=(int(years.min()), int(years.max())),
            )
        )
        frames.append(frame)
        log.info(
            "  %2d/%d %-9s %8d rows  %6d hauls  %4d taxa  %d-%d",
            index,
            len(surveys),
            survey,
            frame.height,
            summaries[-1].hauls,
            summaries[-1].species,
            *summaries[-1].years,
        )

    if skipped:
        log.warning("%d survey(s) skipped: %s", len(skipped), "; ".join(skipped))
    if not frames:
        msg = "No surveys could be read. Nothing to write."
        raise SurveyUnreadableError(msg)

    combined = pl.concat(frames, how="vertical_relaxed")
    keys = taxon_keys(combined["accepted_name"].unique().to_list())
    table = to_evidence(combined, keys)
    log.info(
        "%d evidence rows from %d surveys, %d hauls",
        table.num_rows,
        len(summaries),
        sum(s.hauls for s in summaries),
    )
    return write_evidence(table, spec_for(EvidenceType.SURVEY_INDEX), source_id=SOURCE_ID)
