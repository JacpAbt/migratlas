"""eBird Status and Trends weekly relative abundance, for validating the radar phenology.

**This source may never be published.** Its Terms permit analysis and permit reporting results;
they forbid serving the products or anything derived from them. The registry records
``redistribution.allowed: false`` and the gate refuses a clearance for it, so the enforcement is
structural rather than a note. Nothing here reaches the globe.

Fifty species, because the Terms cap non-peer-reviewed use at fifty. That is why the list below
is a fixed constant and not a query: a cap you can accidentally exceed is not a cap.

What this can and cannot settle, stated once so it is not misread downstream: the 2023 release
models a single representative year at weekly resolution, from data collected 2009 onwards. It
can corroborate the *shape and timing* of a seasonal cycle. It cannot corroborate a trend across
years, and it cannot speak to the 2012 instrument step in the radar record. Relative abundance is
standing stock; radar traffic is passage flux. Compare timing landmarks, never levels.
"""

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np
import polars as pl
import pyarrow as pa

from migratlas.catalog import loader as catalog
from migratlas.config import Settings, get_settings
from migratlas.evidence import EvidenceType, Realm, TaxonScope, spec_for
from migratlas.ingest.http import RemoteFile, fetch
from migratlas.lake.writer import WriteResult, write_evidence
from migratlas.taxonomy import gbif

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)

SOURCE_ID: Final = "ebird_status_trends"
RELEASE: Final = "2023"
API: Final = "https://st-download.ebird.org/v1"

# The Terms' ceiling for non-peer-reviewed use.
MAX_SPECIES: Final = 50

# 27 km is the coarsest published resolution and the only sane choice here: the comparison is
# against a radar network whose stations are ~230 km apart, and the finer products are 100x the
# download for detail the question cannot use.
RESOLUTION: Final = "27km"

# Aggregated to one degree at ingest, matching every other surface in the lake. Relative
# abundance is a density-like quantity -- an expected count on a standard checklist -- so
# sub-cells are averaged, never summed. Summing would scale with how many 27 km cells happen to
# fall inside a degree.
TARGET_CELL_DEG: Final = 1.0

# Contiguous US, matching reports.phase1's radar footprint. Restricting at ingest is a scoping
# decision, not data loss: the comparison is CONUS-only by construction, and the full continental
# extent would be 40x the rows for cells no radar ever saw.
CONUS_LON: Final = (-125.0, -66.0)
CONUS_LAT: Final = (24.0, 50.0)


@dataclass(frozen=True, slots=True)
class Species:
    """One curated species. Both fields are verified before use, neither is trusted."""

    code: str
    """eBird 6-letter code, checked by fetching its config from the release."""
    scientific_name: str
    """Checked against the GBIF Backbone, which supplies the taxon key."""
    common_name: str


# Selection rule, applied deliberately rather than by convenience:
#
# 1. Families that migrate nocturnally in North America -- Parulidae, Catharus and Hylocichla
#    thrushes, Passerellidae, Vireonidae, Cardinalidae, Icteridae, Tyrannidae, Mimidae,
#    Troglodytidae, Cuculidae. This is the standard composition of a "nocturnal migrant
#    landbird" set in the radar-ornithology literature, and it is what the radar's night window
#    is measuring. Waterfowl and raptors are excluded: they migrate by day.
# 2. Long-distance migrants preferred over short-distance ones, so the seasonal signal is a
#    passage rather than a local shuffle.
# 3. eBird's own IS_RESIDENT flag must be false. Checked per species against its config, so a
#    resident cannot enter the set through a mistake in this list.
SPECIES: Final[tuple[Species, ...]] = (
    # Parulidae
    Species("ovenbi1", "Seiurus aurocapilla", "Ovenbird"),
    Species("norwat", "Parkesia noveboracensis", "Northern Waterthrush"),
    Species("bawwar", "Mniotilta varia", "Black-and-white Warbler"),
    Species("prowar", "Protonotaria citrea", "Prothonotary Warbler"),
    Species("tenwar", "Leiothlypis peregrina", "Tennessee Warbler"),
    Species("naswar", "Leiothlypis ruficapilla", "Nashville Warbler"),
    Species("comyel", "Geothlypis trichas", "Common Yellowthroat"),
    Species("amered", "Setophaga ruticilla", "American Redstart"),
    Species("magwar", "Setophaga magnolia", "Magnolia Warbler"),
    Species("bkbwar", "Setophaga fusca", "Blackburnian Warbler"),
    Species("yelwar", "Setophaga petechia", "Yellow Warbler"),
    Species("chswar", "Setophaga pensylvanica", "Chestnut-sided Warbler"),
    Species("blpwar", "Setophaga striata", "Blackpoll Warbler"),
    Species("palwar", "Setophaga palmarum", "Palm Warbler"),
    Species("bktwar", "Setophaga virens", "Black-throated Green Warbler"),
    Species("canwar", "Cardellina canadensis", "Canada Warbler"),
    Species("wlswar", "Cardellina pusilla", "Wilson's Warbler"),
    Species("hoowar", "Setophaga citrina", "Hooded Warbler"),
    Species("norpar", "Setophaga americana", "Northern Parula"),
    Species("babwar", "Setophaga castanea", "Bay-breasted Warbler"),
    Species("capwar", "Setophaga tigrina", "Cape May Warbler"),
    Species("bkpwar", "Setophaga caerulescens", "Black-throated Blue Warbler"),
    # Turdidae
    Species("veery", "Catharus fuscescens", "Veery"),
    Species("swathr", "Catharus ustulatus", "Swainson's Thrush"),
    Species("herthr", "Catharus guttatus", "Hermit Thrush"),
    Species("gycthr", "Catharus minimus", "Gray-cheeked Thrush"),
    Species("woothr", "Hylocichla mustelina", "Wood Thrush"),
    # Vireonidae
    Species("reevir1", "Vireo olivaceus", "Red-eyed Vireo"),
    Species("warvir", "Vireo gilvus", "Warbling Vireo"),
    Species("yetvir", "Vireo flavifrons", "Yellow-throated Vireo"),
    Species("buhvir", "Vireo solitarius", "Blue-headed Vireo"),
    # Passerellidae
    Species("whtspa", "Zonotrichia albicollis", "White-throated Sparrow"),
    Species("whcspa", "Zonotrichia leucophrys", "White-crowned Sparrow"),
    Species("linspa", "Melospiza lincolnii", "Lincoln's Sparrow"),
    Species("swaspa", "Melospiza georgiana", "Swamp Sparrow"),
    Species("chispa", "Spizella passerina", "Chipping Sparrow"),
    Species("foxspa", "Passerella iliaca", "Fox Sparrow"),
    # Cardinalidae
    Species("scatan", "Piranga olivacea", "Scarlet Tanager"),
    Species("sumtan", "Piranga rubra", "Summer Tanager"),
    Species("robgro", "Pheucticus ludovicianus", "Rose-breasted Grosbeak"),
    Species("indbun", "Passerina cyanea", "Indigo Bunting"),
    # Icteridae
    Species("balori", "Icterus galbula", "Baltimore Oriole"),
    Species("orcori", "Icterus spurius", "Orchard Oriole"),
    Species("boboli", "Dolichonyx oryzivorus", "Bobolink"),
    # Tyrannidae
    Species("leafly", "Empidonax minimus", "Least Flycatcher"),
    Species("yebfly", "Empidonax flaviventris", "Yellow-bellied Flycatcher"),
    Species("easkin", "Tyrannus tyrannus", "Eastern Kingbird"),
    Species("eawpew", "Contopus virens", "Eastern Wood-Pewee"),
    # Mimidae, Troglodytidae, Cuculidae
    Species("gracat", "Dumetella carolinensis", "Gray Catbird"),
    Species("yebcuc", "Coccyzus americanus", "Yellow-billed Cuckoo"),
)


class SpeciesRejectedError(ValueError):
    """A curated species failed verification against the release or the backbone."""


class DownloadFailedError(RuntimeError):
    """An API object could not be fetched. Carries no URL, so it carries no access key."""


def _key() -> str:
    return Settings.credential("ebird_st_key")


def _download(object_key: str, name: str) -> Path:
    """Fetch one API object, keeping the access key out of any error that escapes.

    The key travels as a query parameter because the API requires it there. httpx puts the
    request URL into HTTPStatusError, so an unhandled 403 would print the credential into a
    traceback or a CI log. Scrubbed here rather than trusted not to happen.
    """
    key = _key()
    try:
        remote = RemoteFile(url=f"{API}/fetch?objKey={object_key}&key={key}", name=name)
        return fetch(remote, SOURCE_ID)
    except Exception as error:
        raise type(error)(str(error).replace(key, "<key>")) from None


def verify(species: Species) -> dict[str, object]:
    """Fetch and check one species' config, or refuse it.

    Checks the code exists in this release and that eBird does not call it resident. A curated
    list is a place for mistakes; this is where they surface rather than becoming quiet rows.
    """
    destination = _download(
        f"{RELEASE}/{species.code}/config.json", f"{RELEASE}/{species.code}-config.json"
    )
    config: dict[str, object] = json.loads(destination.read_text(encoding="utf-8"))

    codes = config.get("SPECIES_CODE") or [""]
    resident = config.get("IS_RESIDENT") or [True]
    if not isinstance(codes, list) or str(codes[0]) != species.code:
        msg = f"{species.code!r} is not the code in its own config: {codes!r}"
        raise SpeciesRejectedError(msg)
    if not isinstance(resident, list) or bool(resident[0]):
        msg = (
            f"{species.code!r} ({species.common_name}) is resident per eBird, so it has no "
            f"migration to compare. Remove it from SPECIES."
        )
        raise SpeciesRejectedError(msg)
    return config


def weekly_dates(species: Species) -> list[str]:
    """The 52 week-ending dates the raster's bands correspond to."""
    destination = _download(
        f"{RELEASE}/{species.code}/weekly/band-dates.csv",
        f"{RELEASE}/{species.code}-band-dates.csv",
    )
    return pl.read_csv(destination)["date"].cast(pl.String).to_list()


def download_abundance(species: Species) -> Path:
    """Fetch one species' 52-band weekly abundance raster."""
    name = f"{species.code}_abundance_median_{RESOLUTION}_{RELEASE}.tif"
    return _download(f"{RELEASE}/{species.code}/weekly/{name}", f"{RELEASE}/{name}")


def read_conus_weeks(raster: Path, dates: list[str]) -> pl.DataFrame:
    """Read a weekly abundance raster into one-degree CONUS cells.

    Cell centres are transformed from the native equal-area grid rather than the raster being
    reprojected: transforming coordinates is exact, while warping resamples the values being
    measured. The 27 km cells are then averaged into one-degree cells, because relative abundance
    is an expected count on a standard checklist and averages rather than sums.
    """
    import rasterio  # noqa: PLC0415 -- the geo extra, not needed for a lean install
    from rasterio.warp import transform as warp_transform  # noqa: PLC0415

    with rasterio.open(raster) as source:
        rows, cols = np.meshgrid(np.arange(source.height), np.arange(source.width), indexing="ij")
        native_x, native_y = source.xy(rows.ravel(), cols.ravel())
        longitude, latitude = warp_transform(
            source.crs, "EPSG:4326", list(native_x), list(native_y)
        )
        lon = np.asarray(longitude)
        lat = np.asarray(latitude)

        inside = (
            (lon >= CONUS_LON[0])
            & (lon <= CONUS_LON[1])
            & (lat >= CONUS_LAT[0])
            & (lat <= CONUS_LAT[1])
        )
        if not inside.any():
            return pl.DataFrame()

        frames = []
        for band, date in enumerate(dates, start=1):
            values = source.read(band).ravel()[inside].astype("float64")
            usable = np.isfinite(values) & (values > 0)
            if not usable.any():
                continue
            frames.append(
                pl.DataFrame(
                    {
                        "week_date": [date] * int(usable.sum()),
                        "lon": lon[inside][usable],
                        "lat": lat[inside][usable],
                        "value": values[usable],
                    }
                )
            )

    if not frames:
        return pl.DataFrame()
    return to_degree_cells(pl.concat(frames))


def to_degree_cells(points: pl.DataFrame) -> pl.DataFrame:
    """Average 27 km values into one-degree cells, per week.

    Mean, not sum. Relative abundance is an expected count on a standard checklist -- an
    intensive quantity -- so it does not add over area. Summing would scale the value with how
    many 27 km cells happen to fall inside a given degree, which varies with latitude.
    """
    half = TARGET_CELL_DEG / 2
    return (
        points.with_columns(
            cell_longitude=(pl.col("lon") / TARGET_CELL_DEG).floor() * TARGET_CELL_DEG + half,
            cell_latitude=(pl.col("lat") / TARGET_CELL_DEG).floor() * TARGET_CELL_DEG + half,
        )
        .group_by("week_date", "cell_longitude", "cell_latitude")
        .agg(pl.col("value").mean().alias("value"))
        .sort("week_date", "cell_longitude", "cell_latitude")
    )


def taxon_keys() -> dict[str, int]:
    """Resolve the curated scientific names against the GBIF Backbone, cached between runs."""
    cache = get_settings().cache_dir / f"{SOURCE_ID}_taxon_keys.json"
    known: dict[str, int] = {}
    if cache.exists():
        known = {str(k): int(v) for k, v in json.loads(cache.read_text(encoding="utf-8")).items()}

    missing = [s.scientific_name for s in SPECIES if s.scientific_name not in known]
    if missing:
        log.info("resolving %d names against the GBIF Backbone", len(missing))
        with gbif.client() as http:
            for name in missing:
                try:
                    known[name] = gbif.match_name(http, name).usage_key
                except (gbif.TaxonomyError, OSError) as exc:
                    log.warning("unresolved %r: %s", name, exc)
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(known, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return known


def to_evidence(species: Species, weeks: pl.DataFrame, taxon_key: int) -> pa.Table:
    """Reshape one species' weekly CONUS cells into ABUNDANCE_SURFACE rows."""
    out = weeks.select(
        source_id=pl.lit(SOURCE_ID),
        # Birds in flight over land. The realm is the medium the movement happens in, and for a
        # nocturnal migrant that is the air, not the ground it was counted from.
        realm=pl.lit(Realm.AERIAL.value),
        taxon_scope=pl.lit(TaxonScope.EXACT.value),
        taxon_key=pl.lit(taxon_key, dtype=pl.Int64),
        taxon_label=pl.lit(species.scientific_name),
        cell_longitude=pl.col("cell_longitude").cast(pl.Float64),
        cell_latitude=pl.col("cell_latitude").cast(pl.Float64),
        cell_size_deg=pl.lit(TARGET_CELL_DEG, dtype=pl.Float64),
        cell_id=pl.lit(None, dtype=pl.String),
        cell_system=pl.lit(f"degree_{int(TARGET_CELL_DEG)}"),
        # A week, not a year: this is the finest period any surface in the lake carries, and it
        # is the whole reason this source is worth having.
        period_start=pl.col("week_date").str.to_datetime("%Y-%m-%d").dt.replace_time_zone("UTC"),
        period_end=(
            pl.col("week_date").str.to_datetime("%Y-%m-%d") + pl.duration(days=6)
        ).dt.replace_time_zone("UTC"),
        value=pl.col("value").cast(pl.Float64),
        # Modelled expected count on a standard checklist. Not a census, not comparable across
        # species without care, and never to be summed against occurrence records.
        value_kind=pl.lit("relative_abundance"),
        value_lower=pl.lit(None, dtype=pl.Float64),
        value_upper=pl.lit(None, dtype=pl.Float64),
    )
    schema = spec_for(EvidenceType.ABUNDANCE_SURFACE).schema
    return out.select(schema.names).to_arrow().cast(schema)


def ingest(limit: int | None = None) -> WriteResult:
    """Verify, fetch and land the curated species. Idempotent."""
    if len(SPECIES) > MAX_SPECIES:
        msg = (
            f"SPECIES holds {len(SPECIES)} entries but the Terms cap non-peer-reviewed use at "
            f"{MAX_SPECIES}. Shorten the list; do not raise the cap."
        )
        raise SpeciesRejectedError(msg)

    source = catalog.admit(SOURCE_ID)
    log.info("ingesting %s (%s)", source.title, source.licence)
    if source.redistribution.allowed:
        msg = (
            f"{SOURCE_ID} is registered as redistributable, which contradicts its Terms. "
            f"Refusing to ingest under a registry entry that would let it be published."
        )
        raise SpeciesRejectedError(msg)

    keys = taxon_keys()
    wanted = SPECIES[:limit] if limit else SPECIES
    tables: list[pa.Table] = []
    skipped: list[str] = []

    for index, species in enumerate(wanted, start=1):
        key = keys.get(species.scientific_name)
        if key is None:
            skipped.append(f"{species.code} (no GBIF key for {species.scientific_name!r})")
            continue
        try:
            verify(species)
            weeks = read_conus_weeks(download_abundance(species), weekly_dates(species))
        except (SpeciesRejectedError, DownloadFailedError) as error:
            # One bad code must not lose the other forty-nine.
            skipped.append(f"{species.code} ({error})")
            continue

        if weeks.is_empty():
            skipped.append(f"{species.code} (no CONUS cells with abundance above zero)")
            continue
        tables.append(to_evidence(species, weeks, key))
        log.info(
            "  %2d/%d %-8s %-32s %7d cell-weeks",
            index,
            len(wanted),
            species.code,
            species.scientific_name,
            weeks.height,
        )

    if skipped:
        log.warning("%d species skipped: %s", len(skipped), "; ".join(skipped))
    if not tables:
        msg = "No species landed. Nothing to write."
        raise SpeciesRejectedError(msg)

    table = pa.concat_tables(tables)
    log.info("%d evidence rows from %d species", table.num_rows, len(tables))
    return write_evidence(table, spec_for(EvidenceType.ABUNDANCE_SURFACE), source_id=SOURCE_ID)
