"""Where change could ever be measured, and where it could not.

`docs/DATASETS.md` audits the lake and concludes that global extent and measurable change are, so
far, different data. This turns that conclusion into geography: a one-degree grid where each cell
carries the best status any source can give it, and the reason when that status is not "detectable".

**A different question from the one the literature already answers.** There is a mature body of work
on biodiversity knowledge gaps -- the Wallacean shortfall and its relatives -- and it asks *do we
know where species are*. This asks *could a change here ever be detected*, which needs three things
the first question does not: a time axis, a repeated protocol, and effort fixed by design. The two
maps disagree sharply. `obis_speciesgrids` covers 46,809 cells and scores as well as anything on
knowing where species are, and it cannot support a single trend.

**Grey is the finding.** Most of the world has no source that clears the bar, and that is not a gap
in this project's ambition -- long digitised radar and trawl series exist where they were funded. A
results map without this layer underneath it would invite the reader to think the empty ocean was
empty of animals rather than of measurement.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Final

import polars as pl

from migratlas.evidence import EvidenceType

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)

SCHEMA_VERSION: Final = 1

CELL_DEG: Final = 1.0
"""One degree, matching every other gridded surface in the lake so the layers overlay."""

MIN_YEARS: Final = 15
"""Years of a series a unit needs before a trend fitted in it means anything.

Not a threshold invented here: it is the bar `phase1b` and `phase2a_timing` already apply, and
the bar ENRAM failed -- one radar of roughly 190 reaches it, which is why it is not in the lake.
"""

# Ordered worst to best, so a cell can take the best status any source gives it by taking the max.
STATUSES: Final[tuple[str, ...]] = (
    "no-time-axis",
    "effort-not-measured",
    "too-short",
    "detectable",
)

UNITS: Final[dict[str, pl.Expr | None]] = {
    "station": pl.col("station_id"),
    "site": pl.col("site_id"),
    # A haul happens once, so `site_id` here would give every unit a single year. What recurs in a
    # trawl survey is the stratum, which FISHGLOB does not ship -- so the survey programme stands
    # in, exactly as `phase1b` pools by it.
    "survey": pl.col("site_id").str.split(":").list.first(),
    "cell": None,
}
"""What carries the protocol, per source. Years are counted per unit, never per cell.

The distinction is the whole point: fifteen years of a rotating set of one-year units is not a
series, and counting the cell's own span would call it one.
"""


@dataclass(frozen=True, slots=True)
class SourceRule:
    """Why a source can or cannot support change detection, decided once and applied per cell."""

    source_id: str
    evidence_type: EvidenceType
    realm: str
    latitude: str
    longitude: str
    unit: str
    """Key into `UNITS`: the thing whose repeated visits make a series here."""

    ceiling: str
    """The best status this source can reach anywhere, whatever a particular cell looks like."""

    reason: str
    """Why the ceiling is where it is, in one line a reader can act on."""

    effort_note: str = ""
    """Any qualification on "effort fixed by design" that a claim built here has to carry."""


# Decided from `docs/DATASETS.md` and each source's own method note, not from the row counts.
RULES: Final[tuple[SourceRule, ...]] = (
    SourceRule(
        source_id="darkecology_daily",
        evidence_type=EvidenceType.FLUX,
        realm="aerial",
        latitude="station_latitude",
        longitude="station_longitude",
        unit="station",
        ceiling="detectable",
        reason=(
            "One instrument, one protocol, nightly since 1995. Effort is fixed by the radar rather "
            "than by who was watching."
        ),
    ),
    SourceRule(
        source_id="fishglob",
        evidence_type=EvidenceType.SURVEY_INDEX,
        realm="marine",
        latitude="site_latitude",
        longitude="site_longitude",
        unit="survey",
        ceiling="detectable",
        reason=(
            "Scientific bottom-trawl surveys: the same gear over the same stratified stations in "
            "the same season, with swept area recorded per haul."
        ),
    ),
    SourceRule(
        source_id="bbs",
        evidence_type=EvidenceType.SURVEY_INDEX,
        realm="terrestrial",
        latitude="site_latitude",
        longitude="site_longitude",
        unit="site",
        ceiling="detectable",
        reason="The same route, the same 50 three-minute stops, every June since 1966.",
        effort_note=(
            "Roadside by design, so the sample is not random with respect to land use, and "
            "observer skill is the best-documented bias in the dataset."
        ),
    ),
    SourceRule(
        source_id="sabap1",
        evidence_type=EvidenceType.SURVEY_INDEX,
        realm="terrestrial",
        latitude="site_latitude",
        longitude="site_longitude",
        unit="site",
        ceiling="detectable",
        reason="Atlas cards are a countable effort denominator: one observer, one cell, one month.",
        effort_note=(
            "Citizen science, so effort is measured rather than fixed: cards per cell run from 4 "
            "to 2,271 over the atlas core, and the consistent-footprint rule has to be applied."
        ),
    ),
    SourceRule(
        source_id="sabap2",
        evidence_type=EvidenceType.SURVEY_INDEX,
        realm="terrestrial",
        latitude="site_latitude",
        longitude="site_longitude",
        unit="site",
        ceiling="detectable",
        reason="As SABAP1, with the full protocol separated from ad-hoc lists.",
        effort_note=(
            "Citizen science. Cards per pentad run from 1 to 3,963, and ad-hoc lists average 9.5 "
            "species against a full card's 52, so the two are never pooled."
        ),
    ),
    SourceRule(
        source_id="obis_speciesgrids",
        evidence_type=EvidenceType.ABUNDANCE_SURFACE,
        realm="marine",
        latitude="cell_latitude",
        longitude="cell_longitude",
        unit="cell",
        ceiling="effort-not-measured",
        reason=(
            "Occurrence records with a first and last year per taxon-cell and no per-year sampling "
            "record, so there is nothing to build an effort correction from. Survey effort also "
            "expanded polewards over exactly the period a range-shift hypothesis is about."
        ),
    ),
    SourceRule(
        source_id="megamove",
        evidence_type=EvidenceType.ABUNDANCE_SURFACE,
        realm="marine",
        latitude="cell_latitude",
        longitude="cell_longitude",
        unit="cell",
        ceiling="no-time-axis",
        reason=(
            "One pooled 1985-2018 product. Every row carries the same period, so there is no "
            "series to trend -- however many sharks, turtles and whales are in it."
        ),
    ),
    SourceRule(
        source_id="ebird_status_trends",
        evidence_type=EvidenceType.ABUNDANCE_SURFACE,
        realm="aerial",
        latitude="cell_latitude",
        longitude="cell_longitude",
        unit="cell",
        ceiling="no-time-axis",
        reason=(
            "A single modelled year, and its licence forbids redistribution, so it serves as an "
            "independent cross-check rather than as a layer."
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class Coverage:
    """What one source contributes, in cells."""

    source_id: str
    realm: str
    ceiling: str
    reason: str
    effort_note: str
    cells: int
    detectable_cells: int
    years: tuple[int, int]


@dataclass(frozen=True, slots=True)
class Grid:
    """The compact envelope the globe's surface reader already understands, plus categories."""

    format: str
    cell_size_deg: float
    value_kind: str
    categories: list[str]
    """Index into this by the integer in `v`. Present so a renderer knows the values are nominal
    rather than a magnitude on a ramp -- colouring `no-time-axis` as "less than detectable" on a
    continuous scale would imply an ordering the statuses do not have."""
    x: list[int]
    y: list[int]
    v: list[int]


@dataclass(frozen=True, slots=True)
class Detectability:
    schema_version: int
    min_years: int
    grid: Grid
    coverage: list[Coverage]
    summary: dict[str, int]
    """Cells per status across the whole grid, which is the number the panel states."""

    caveat: str
    method: str
    supporting: list[str] = field(default_factory=list)


def _cells(rule: SourceRule) -> pl.DataFrame:
    """Per-cell status for one source: its ceiling, lowered where the series is too short."""
    from migratlas.lake.reader import scan  # noqa: PLC0415

    frame = (
        scan(rule.evidence_type, source_id=rule.source_id)
        .select(
            # Offset before dividing, matching `tiles/export.py`: the wire format's inverse is
            # `(index + 0.5) * size - 180`, so an index that is not shifted first decodes 180
            # degrees west and 90 south. Written without the offset the first time, which drew the
            # whole layer as a crescent along the limb of the globe.
            x=((pl.col(rule.longitude) + 180.0) / CELL_DEG).floor().cast(pl.Int32),
            y=((pl.col(rule.latitude) + 90.0) / CELL_DEG).floor().cast(pl.Int32),
            unit=_unit(rule),
            year=pl.col(_time_column(rule)).dt.year(),
        )
        .collect()
    )
    if frame.is_empty():
        return frame

    per_cell = (
        frame.group_by("x", "y", "unit")
        .agg(years=pl.col("year").n_unique())
        .group_by("x", "y")
        .agg(best_years=pl.col("years").max())
    )
    ceiling = STATUSES.index(rule.ceiling)
    too_short = STATUSES.index("too-short")
    return per_cell.with_columns(
        status=pl.when(pl.col("best_years") >= MIN_YEARS)
        .then(pl.lit(ceiling))
        # A source whose ceiling is already below "too-short" is not limited by length, so its
        # ceiling stands: saying megamove is "too short" would name the wrong problem.
        .otherwise(pl.lit(min(ceiling, too_short)))
    ).select("x", "y", "status")


def _unit(rule: SourceRule) -> pl.Expr:
    """The unit expression, falling back to the cell itself where nothing inside it recurs."""
    expression = UNITS[rule.unit]
    if expression is not None:
        return expression
    # A gridded surface samples a cell without naming a place inside it, so the cell has to
    # stand in. Both such sources are capped below "too-short" anyway, so this only decides
    # how their own coverage reads.
    return pl.concat_str([pl.col(rule.longitude), pl.col(rule.latitude)], separator=":")


def _time_column(rule: SourceRule) -> str:
    from migratlas.evidence import spec_for  # noqa: PLC0415

    column = spec_for(rule.evidence_type).time_column
    if column is None:  # pragma: no cover - every type in RULES has one
        msg = f"{rule.evidence_type} has no time column, so detectability is undefined for it"
        raise ValueError(msg)
    return column


def collect() -> Detectability:
    """Walk every registered source and reduce it to one status per cell."""
    coverage: list[Coverage] = []
    layers: list[pl.DataFrame] = []

    for rule in RULES:
        cells = _cells(rule)
        if cells.is_empty():
            log.warning("%s contributed no cells; is it ingested?", rule.source_id)
            continue
        # Reported whatever the ceiling: a single-epoch source shows as one year, which is the
        # clearest possible statement of why it cannot carry a trend.
        span = scan_years(rule)
        detectable = int(
            cells.filter(pl.col("status") == STATUSES.index("detectable")).height
            if rule.ceiling == "detectable"
            else 0
        )
        coverage.append(
            Coverage(
                source_id=rule.source_id,
                realm=rule.realm,
                ceiling=rule.ceiling,
                reason=rule.reason,
                effort_note=rule.effort_note,
                cells=cells.height,
                detectable_cells=detectable,
                years=span,
            )
        )
        layers.append(cells)
        log.info(
            "%s: %d cells, ceiling %s, %d detectable",
            rule.source_id,
            cells.height,
            rule.ceiling,
            detectable,
        )

    if not layers:
        msg = "no source contributed a cell; the lake looks empty"
        raise RuntimeError(msg)

    # The best status any source gives the cell. A cell FISHGLOB can trend and OBIS cannot is
    # detectable: the limitation belongs to the source, not to the place.
    best = pl.concat(layers).group_by("x", "y").agg(status=pl.col("status").max()).sort("x", "y")
    summary = {
        status: int(best.filter(pl.col("status") == index).height)
        for index, status in enumerate(STATUSES)
    }

    return Detectability(
        schema_version=SCHEMA_VERSION,
        min_years=MIN_YEARS,
        grid=Grid(
            format="grid",
            cell_size_deg=CELL_DEG,
            value_kind="detectability",
            categories=list(STATUSES),
            x=best["x"].to_list(),
            y=best["y"].to_list(),
            v=best["status"].to_list(),
        ),
        coverage=coverage,
        summary=summary,
        caveat=(
            "A cell counted as detectable means some source there has a long enough series with a "
            "measurable effort denominator — not that a change has been detected, and not that "
            "any particular species could be tracked in it. Cells with no source at all are "
            "absent from the grid rather than marked, because the lake says nothing about them."
        ),
        method="docs/methods/detectability.md",
        supporting=[
            "Fifteen years per unit is the bar phase1b and phase2a_timing already apply, and the "
            "bar ENRAM failed: one radar of roughly 190 reaches it.",
            "Years are counted per protocol unit -- a radar, a route, a pentad, a survey "
            "programme -- rather than per cell, so a rotating set of short-lived units "
            "cannot add up to a series.",
        ],
    )


def scan_years(rule: SourceRule) -> tuple[int, int]:
    """First and last year the source covers, for the coverage table."""
    from migratlas.lake.reader import scan  # noqa: PLC0415

    years = (
        scan(rule.evidence_type, source_id=rule.source_id)
        .select(year=pl.col(_time_column(rule)).dt.year())
        .collect()["year"]
    )
    low, high = years.min(), years.max()
    return (int(low), int(high))  # type: ignore[arg-type]


def render(found: Detectability) -> str:
    # Compact, as `tiles/export.py` writes its grids: fifty thousand cells at one integer per line
    # is a megabyte of indentation, and this is a payload rather than something to read in a diff.
    return json.dumps(asdict(found), separators=(",", ":"))


def write(destination: Path, computed: Detectability | None = None) -> int:
    payload = render(computed if computed is not None else collect())
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(payload + "\n", encoding="utf-8")
    return len(payload)
