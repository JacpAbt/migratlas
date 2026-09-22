"""UK Butterfly Monitoring Scheme flight-period phenology, per `docs/methods/phase1j-fourth-leg.md`.

**`count` is days from first appearance to the mean flight date, not a day number.** `count` is this
table's value column, where `sabap1` puts a reporting rate and `fishglob` a standardised index --
every one of those an intensity. A day of year is a coordinate on the time axis instead, and
anything aggregating the column would be averaging calendars. So the period columns carry the dates
they are for and `count` carries a real count of days: `period_start + count` recovers the mean
flight date exactly.
"""

import logging
from typing import TYPE_CHECKING, Final

import polars as pl

from migratlas.catalog import loader as catalog
from migratlas.evidence import EvidenceType, Realm, TaxonScope, spec_for
from migratlas.ingest.http import RemoteFile, fetch
from migratlas.lake.writer import WriteResult, write_evidence
from migratlas.taxonomy import gbif

if TYPE_CHECKING:
    import pyarrow as pa

log = logging.getLogger(__name__)

SOURCE_ID: Final = "ukbms_phenology"
SITES_SOURCE_ID: Final = "ukbms_sites"

PHENOLOGY_ARCHIVE: Final = "ukbms-phenology.zip"
SITES_ARCHIVE: Final = "ukbms-sites.zip"

# British National Grid. pyproj carries the datum shift; a Helmert approximation of it is accurate
# to metres, which is ample for sampling a reanalysis whose cells are tens of kilometres across.
BNG: Final = "EPSG:27700"

# Every day column is numbered from this date, inclusive: day 1 is 1 April.
SEASON_START_MONTH: Final = 4
SEASON_START_DAY: Final = 1

# A Pollard walk: fixed route, weekly through the season, under stated weather criteria. The
# phenology product is computed from these alone -- the two-or-three-visit squares cannot support a
# flight curve -- so the effort behind every row here is the same by design.
PROTOCOL: Final = "pollard-walk"

# Both CSVs are Windows-1252, not UTF-8, and only two site names in the whole scheme prove it: a
# curly apostrophe (0x92) in "RSPB Chafey's Weymouth" is the single byte that fails, 81.7 MB into
# the phenology file. Polars raises `invalid utf-8 sequence` with no hint of where or why, and a
# reader that guessed latin-1 would silently turn it into a different character rather than fail.
ENCODING: Final = "cp1252"

# One name in fifty-nine that the Backbone will not take bare, checked against /species/match before
# being written here, as `sabap1.SYNONYMS` was.
SYNONYMS: Final[dict[str, str]] = {
    # The White Admiral. GBIF's accepted name is `Ladoga camilla`, and the bare binomial the scheme
    # uses matches only the *genus* -- matchType HIGHERRANK -- which the matcher refuses rather than
    # accepting a genus for a species. Appending the authority resolves it exactly, at confidence
    # 100, to the same accepted key 7712938 that `Ladoga camilla` gives. Keeping the scheme's own
    # binomial and adding the authority is the `Bubo capensis` case again.
    "Limenitis camilla": "Limenitis camilla (Linnaeus, 1764)",
}


def _member(archive: str, source_id: str, suffix: str) -> bytes:
    """The one CSV inside a downloaded archive, as UTF-8 bytes."""
    import zipfile  # noqa: PLC0415 -- one function, stdlib

    source = catalog.admit(source_id)
    path = fetch(RemoteFile(url=source.download_uri, name=archive), source_id)
    with zipfile.ZipFile(path) as bundle:
        names = [n for n in bundle.namelist() if n.lower().endswith(suffix)]
        if len(names) != 1:
            msg = f"{archive}: expected one {suffix}, found {names}"
            raise ValueError(msg)
        # Re-encoded rather than passed through: polars reads UTF-8, and the archive is not.
        return bundle.read(names[0]).decode(ENCODING).encode("utf-8")


def sites() -> pl.DataFrame:
    """Site positions in degrees, from the scheme's separate site-location dataset.

    The publisher withholds the locations of sites it classes as sensitive. Those sites simply do
    not appear here, and because `SURVEY_INDEX` requires a non-null longitude and latitude they
    cannot enter the lake at all -- another organisation's sensitivity decision enforced by the
    schema rather than by a rule in this file.
    """
    import pyproj  # noqa: PLC0415 -- the geo extra, not needed for a lean install

    frame = pl.read_csv(_member(SITES_ARCHIVE, SITES_SOURCE_ID, ".csv"))
    frame = frame.drop_nulls(["Easting", "Northing"])
    to_degrees = pyproj.Transformer.from_crs(BNG, "EPSG:4326", always_xy=True)
    longitude, latitude = to_degrees.transform(
        frame["Easting"].to_list(), frame["Northing"].to_list()
    )
    return frame.select(
        site=pl.col("Site_Number").cast(pl.Int64),
        country="Country",
        site_longitude=pl.Series(longitude, dtype=pl.Float64),
        site_latitude=pl.Series(latitude, dtype=pl.Float64),
    )


def phenology() -> pl.DataFrame:
    """The flight-period table, with the pooled row dropped where generations are split.

    `NUMBER_OF_BROODS` is how many distinct flight periods the scheme was able to separate, and
    `BROOD` is which one a row describes -- 0 being the whole season. Where the generations were
    separated the pooled row is a mean across two peaks; where they were not, it is the record.
    """
    frame = pl.read_csv(_member(PHENOLOGY_ARCHIVE, SOURCE_ID, ".csv"))
    split = frame.filter(pl.col("NUMBER_OF_BROODS") > 1, pl.col("BROOD") > 0)
    whole = frame.filter(pl.col("NUMBER_OF_BROODS") <= 1, pl.col("BROOD") == 0)
    log.info(
        "phenology: %d rows -> %d whole-season + %d split-generation",
        frame.height,
        whole.height,
        split.height,
    )
    return pl.concat([whole, split]).drop_nulls(["FIRSTDAY", "LASTDAY", "MEAN_FLIGHT_DATE"])


def keys_for(names: list[str]) -> dict[str, int]:
    """Resolve each binomial against the GBIF Backbone once, through `SYNONYMS` where needed.

    Keyed by the name *the scheme uses*, so `to_evidence` can look up what the file actually says
    while the Backbone is asked about something it will accept.
    """
    resolved: dict[str, int] = {}
    with gbif.client() as http:
        for name in names:
            try:
                resolved[name] = gbif.match_name(http, SYNONYMS.get(name, name)).usage_key
            except gbif.TaxonomyError:
                log.warning("no Backbone match for %r", name)
    log.info("resolved %d of %d names", len(resolved), len(names))
    return resolved


def to_evidence(frame: pl.DataFrame, positions: pl.DataFrame, keys: dict[str, int]) -> pl.DataFrame:
    """Reshape into SURVEY_INDEX rows.

    Realm is terrestrial: a transect records butterflies over a patch of ground, which is the same
    judgement `sabap1` records for atlas cards and for the same reason.
    """
    joined = frame.join(positions, left_on="SITENO", right_on="site", how="inner")
    dropped = frame.height - joined.height
    if dropped:
        log.info("%d rows dropped: no published position for the site", dropped)

    # Day 1 is 1 April, so a day number N is 1 April plus N-1 days.
    season = pl.date(pl.col("YEAR"), SEASON_START_MONTH, SEASON_START_DAY)
    first = season.dt.offset_by(pl.format("{}d", pl.col("FIRSTDAY").cast(pl.Int64) - 1))
    last = season.dt.offset_by(pl.format("{}d", pl.col("LASTDAY").cast(pl.Int64) - 1))

    return (
        joined.with_columns(
            taxon_key=pl.col("SPECIES_NAME").replace_strict(
                keys, default=None, return_dtype=pl.Int64
            )
        )
        .drop_nulls("taxon_key")
        .select(
            source_id=pl.lit(SOURCE_ID),
            realm=pl.lit(Realm.TERRESTRIAL.value),
            taxon_scope=pl.lit(TaxonScope.EXACT.value),
            taxon_key="taxon_key",
            taxon_label="SPECIES_NAME",
            site_id=pl.col("SITENO").cast(pl.String),
            period_start=first.cast(pl.Datetime("ms", "UTC")),
            period_end=last.cast(pl.Datetime("ms", "UTC")),
            site_longitude="site_longitude",
            site_latitude="site_latitude",
            site_depth_m=pl.lit(None, dtype=pl.Float64),
            # Days from first appearance to the count-weighted mean flight date. See the module
            # docstring for why the mean flight date is not stored as a day number.
            count=(pl.col("MEAN_FLIGHT_DATE") - pl.col("FIRSTDAY")).cast(pl.Float64),
            effort=pl.lit(None, dtype=pl.Float64),
            effort_unit=pl.lit(None, dtype=pl.String),
            protocol=pl.when(pl.col("BROOD") > 0)
            .then(pl.format("{}/gen{}", pl.lit(PROTOCOL), pl.col("BROOD")))
            .otherwise(pl.lit(PROTOCOL)),
        )
    )


def ingest() -> WriteResult:
    """Fetch both archives, join, resolve and land the series."""
    positions = sites()
    frame = phenology()
    keys = keys_for(sorted(frame["SPECIES_NAME"].unique().to_list()))
    rows = to_evidence(frame, positions, keys)
    years = rows["period_start"].dt.year()
    log.info(
        "UKBMS: %d rows, %d sites, %d taxa, %s-%s",
        rows.height,
        rows["site_id"].n_unique(),
        rows["taxon_key"].n_unique(),
        years.min(),
        years.max(),
    )
    spec = spec_for(EvidenceType.SURVEY_INDEX)
    table: pa.Table = rows.select(spec.schema.names).to_arrow().cast(spec.schema)
    return write_evidence(table, spec, source_id=SOURCE_ID)


def shape_series() -> pl.DataFrame:
    """The flight curve's *shape* per row, for the guard Phase 1j registered as prediction 6.

    Neither quantity belongs in the lake and neither is there. `SURVEY_INDEX` carries one value
    column, that column carries the flight date, and a second and third number about the same
    period have nowhere to go -- so the guard reads the archive rather than widening a schema for
    a diagnostic.

    The two are not equally trustworthy and a grading has to say which of them moved.
    `FLIGHTPERIOD_SD` is the measure the scheme's own supporting document recommends.
    `FLIGHTPERIOD_RANGE` rests on `FIRSTDAY` and `LASTDAY`, which the same document warns are
    unreliable where a flight period runs past the 1 April to 30 September window. A trend in the
    duration with none in the spread is therefore as likely to be the window as the animals.
    """
    return phenology().select(
        site=pl.col("SITENO").cast(pl.Int64),
        taxon_label=pl.col("SPECIES_NAME"),
        brood=pl.col("BROOD").cast(pl.Int64),
        year=pl.col("YEAR").cast(pl.Int64),
        sd_days=pl.col("FLIGHTPERIOD_SD").cast(pl.Float64),
        duration_days=pl.col("FLIGHTPERIOD_RANGE").cast(pl.Float64),
    )
