"""Phase 2d -- does the butterflies' flight date follow the temperature, per species?

Pre-registered in ``docs/methods/phase2d-flight-response.md`` on 2026-09-02, before any ERA5 value
existed at a UK coordinate. The second of ADR 0018's two studies and the first test of its decision
2: a species' *response* to a driver is fitted before any network number is, because a response
pooled across every site a species occupies is well determined where that species' *trend* at one
site is not -- Phase 1k measured a single flight-date series at 1.05 standard errors from zero.

**The unit is a species-generation.** Its response `S` is days of flight-date shift per degC of
pre-season warmth, fitted within site across years with a linear year term (arm B, the primary)
and without one (arm A, the sensitivity), on Phase 2c's lesson that two trending series share a
slope the coefficient will otherwise absorb. Its interval is clustered on **year**, because every
site in Britain sees roughly the same spring and Phase 1k measured the price of pretending otherwise
at 4.5 times on this very source.

**The pre-season is fixed per unit by a rule, not chosen against a fit**: the two calendar months
ending the month before the unit's climatological median flight month. It uses the unit's mean
timing and nothing about its year-to-year variation, which is what keeps it non-circular.

**Pooled across units** are a median with a bootstrap over units, Cochran's Q across the units'
responses -- the registered test of whether the response is the species' -- and the thermal share
`median(S x W) / median(A)`, a ratio of medians because a per-unit ratio is unstable where a trend
is near zero.
"""

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING, Final, NamedTuple
from zlib import crc32

import numpy as np
import polars as pl
from scipy import stats

from migratlas.evidence import EvidenceType
from migratlas.lake.reader import scan, scan_dataset
from migratlas.metrics import range as range_metrics
from migratlas.models.influence import SMALL_PANEL, Influence, leave_one_out

if TYPE_CHECKING:
    from collections.abc import Sequence

    from migratlas.reports.phase1k import TimingResult

log = logging.getLogger(__name__)

SOURCE: Final = "ukbms_phenology"
DRIVER_SOURCE: Final = "era5_uk"
TEMPERATURE: Final = "air_temperature_2m"

SEED: Final = 1
DRAWS: Final = 1_000

MIN_YEARS: Final = 15
"""Phase 1k's floor on a series, applied to a unit's distinct years carrying a date and a driver."""
MIN_SITES: Final = 10
MIN_UNITS: Final = 20
"""Below this the pooled quantities publish as a coverage statement."""
MIN_POINTS: Final = 2
"""A trend, an interval or a heterogeneity over fewer than two things is not one."""

WINDOW_MONTHS: Final = 2
"""The pre-season is this many calendar months, ending the month before the median flight month."""

MATCH_KM: Final = 30.0
"""Prediction 1: a site's ERA5 cell must be within this of the transect. A quarter-degree grid puts
the furthest point about twenty kilometres from a cell centre, so a match beyond this is a bug."""
MATCH_SHARE: Final = 0.99

RADAR_RESPONSE: Final = -0.66
"""Prediction 3's bar: the radar's published thermal response, in days per degC."""
RADAR_SHARE: Final = 0.54
"""Prediction 6's bar: the upper end of Phase 2c's bracket on the radar's thermal share."""

CALIBRATION_MEDIAN: Final = -2.104
CALIBRATION_TOLERANCE: Final = 5e-4
"""Three significant figures on `flight-advance`'s published median."""

MIGRANTS: Final[tuple[str, ...]] = ("Vanessa cardui", "Vanessa atalanta", "Colias croceus")
"""Phase 1j's registered list, unchanged. Prediction 8 sets these three against everyone else."""

EARTH_RADIUS_KM: Final = 6371.0


class Columns(NamedTuple):
    """One unit's panel as arrays, so the bootstrap can index rows without a frame in the loop."""

    site: np.ndarray
    """Integer site codes, dense from zero, for `np.bincount`."""
    flight: np.ndarray
    temperature: np.ndarray
    year: np.ndarray

    def take(self, rows: np.ndarray) -> Columns:
        return Columns(self.site[rows], self.flight[rows], self.temperature[rows], self.year[rows])


@dataclass(frozen=True, slots=True)
class Coverage:
    """Prediction 1: did the driver land where the transects are?"""

    sites: int
    matched: int
    within: int
    """Sites whose ERA5 cell centre lies within `MATCH_KM` of the transect."""
    furthest_km: float

    @property
    def share_within(self) -> float:
        return self.within / self.sites if self.sites else float("nan")

    @property
    def landed(self) -> bool:
        return self.share_within >= MATCH_SHARE


@dataclass(frozen=True, slots=True)
class UnitResponse:
    """One species-generation's thermal response, with everything the predictions read off it."""

    unit: str
    label: str
    generation: str
    migrant: bool
    years: int
    sites: int
    rows: int
    window: tuple[int, int]
    response_a: float
    """Arm A: no year term. The sensitivity."""
    response_b: float
    """Arm B: with a year term. The primary."""
    interval_b: tuple[float, float]
    """Percentile bootstrap over years, all their rows attached."""
    naive_b: tuple[float, float]
    """Over rows, as if every site-year were independent. Printed, never graded."""
    warming: float
    """`W`: trend per decade in the unit's cross-site mean pre-season temperature."""
    advance: float
    """`A`: the unit's median per-site flight-date trend, days per decade."""

    @property
    def stderr_b(self) -> float:
        low, high = self.interval_b
        return (high - low) / 3.92 if np.isfinite(low) and np.isfinite(high) else float("nan")

    @property
    def explained(self) -> float:
        """`S x W`, days per decade of advance the response predicts from the observed warming."""
        return self.response_b * self.warming

    @property
    def clears_zero(self) -> bool:
        low, high = self.interval_b
        return high < 0.0 or low > 0.0


@dataclass(frozen=True, slots=True)
class Pooled:
    """The network, as a summary of its species rather than in place of them."""

    units: int
    median_a: float
    median_b: float
    interval_b: tuple[float, float]
    """Bootstrap over units."""
    q_statistic: float
    q_bar: float
    median_warming: float
    warming_interval: tuple[float, float]
    share: float
    """`median(S x W) / median(A)`."""
    median_advance: float
    migrant_median: float
    resident_median: float
    leverage: Influence | None

    @property
    def negative_and_clear(self) -> bool:
        """Prediction 3, first half."""
        return self.interval_b[1] < 0.0

    @property
    def stronger_than_radar(self) -> bool:
        """Prediction 3, second half: larger in magnitude than the radar's response."""
        return self.median_b < RADAR_RESPONSE

    @property
    def warmed(self) -> bool:
        """Prediction 4."""
        return self.warming_interval[0] > 0.0

    @property
    def heterogeneous(self) -> bool:
        """Prediction 5: the responses are the species'."""
        return self.q_statistic > self.q_bar

    @property
    def more_thermal_than_radar(self) -> bool:
        """Prediction 6."""
        return self.share > RADAR_SHARE

    @property
    def year_term_shrinks(self) -> bool:
        """Prediction 7: |arm B| < |arm A|."""
        return abs(self.median_b) < abs(self.median_a)

    @property
    def migrants_respond_less(self) -> bool:
        """Prediction 8, on the medians of |S|."""
        return abs(self.migrant_median) < abs(self.resident_median)


@dataclass(frozen=True, slots=True)
class Phase2d:
    """The whole phase."""

    calibration: float
    coverage: Coverage
    units: tuple[UnitResponse, ...]
    dropped: int
    """Species-generations under a floor, published as coverage."""
    pooled: Pooled | None

    @property
    def calibrated(self) -> bool:
        return abs(self.calibration - CALIBRATION_MEDIAN) < CALIBRATION_TOLERANCE

    @property
    def clear(self) -> int:
        """Units whose year-clustered interval excludes zero. A count is a computed quantity and
        belongs in the output; the first run's 60 of 75 was counted off the printed intervals."""
        return sum(1 for unit in self.units if unit.clears_zero)


def _seed(name: str) -> int:
    return (crc32(name.encode()) ^ SEED) & 0x7FFF_FFFF


# --- The panel -----------------------------------------------------------------------------


def flights() -> pl.DataFrame:
    """Every site-species-generation-year's mean flight date, as `phase1k.timing` reconstructs it.

    `period_start` is the first day of flight and `count` the days from there to the count-weighted
    mean, so the mean's day of year is their sum. Fitting `count` alone would fit a shape, not a
    date -- Phase 1k's own recorded correction.
    """
    frame = (
        scan(EvidenceType.SURVEY_INDEX, source_id=SOURCE)
        .select(
            "site_id",
            "period_start",
            "count",
            "protocol",
            "taxon_key",
            "taxon_label",
            "site_latitude",
            "site_longitude",
            "year",
        )
        .collect()
    )
    if frame.is_empty():
        return frame
    return frame.select(
        unit=pl.col("taxon_key").cast(pl.String) + pl.lit(":") + pl.col("protocol").cast(pl.String),
        label=pl.col("taxon_label").cast(pl.String),
        generation=pl.col("protocol").cast(pl.String),
        site_id=pl.col("site_id").cast(pl.String),
        site_latitude=pl.col("site_latitude").cast(pl.Float64),
        site_longitude=pl.col("site_longitude").cast(pl.Float64),
        year=pl.col("year").cast(pl.Int64),
        flight_day=(pl.col("period_start").dt.ordinal_day().cast(pl.Float64) + pl.col("count")),
    ).drop_nulls()


def temperatures() -> pl.DataFrame:
    """Monthly 2 m temperature per site from the UK driver rows, with the cell each site matched."""
    return (
        scan_dataset("driver_samples", source_id=DRIVER_SOURCE)
        .filter(pl.col("variable") == TEMPERATURE)
        .select(
            site_id=pl.col("site_id").cast(pl.String),
            year=pl.col("period_start").dt.year().cast(pl.Int64),
            month=pl.col("period_start").dt.month().cast(pl.Int64),
            value=pl.col("value").cast(pl.Float64),
            cell_latitude=pl.col("latitude").cast(pl.Float64),
            cell_longitude=pl.col("longitude").cast(pl.Float64),
        )
        .collect()
    )


def _haversine_km(
    lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray
) -> np.ndarray:
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = phi2 - phi1
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2) ** 2
    return np.asarray(2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a)), dtype=float)


def coverage(sites: pl.DataFrame, driver: pl.DataFrame) -> Coverage:
    """Prediction 1: how many transects found a cell, and how far away it was."""
    cells = driver.group_by("site_id").agg(
        pl.col("cell_latitude").first(), pl.col("cell_longitude").first()
    )
    joined = sites.join(cells, on="site_id", how="left")
    matched = joined.drop_nulls("cell_latitude")
    if matched.is_empty():
        return Coverage(sites=sites.height, matched=0, within=0, furthest_km=float("nan"))
    distance = _haversine_km(
        matched["site_latitude"].to_numpy(),
        matched["site_longitude"].to_numpy(),
        matched["cell_latitude"].to_numpy(),
        matched["cell_longitude"].to_numpy(),
    )
    return Coverage(
        sites=sites.height,
        matched=matched.height,
        within=int((distance <= MATCH_KM).sum()),
        furthest_km=float(distance.max()),
    )


def flight_month(flight_days: np.ndarray) -> int:
    """The calendar month of a unit's climatological median flight day, in a non-leap year."""
    median = float(np.median(flight_days))
    return (date(2001, 1, 1) + timedelta(days=round(median) - 1)).month


def window_for(month: int) -> tuple[int, int] | None:
    """The two calendar months ending the month before `month`, or None where none exist.

    A unit whose median flight falls in February would need a December pre-season from the year
    before, which this design does not build; it is reported as coverage instead.
    """
    end = month - 1
    start = end - WINDOW_MONTHS + 1
    if start < 1:
        return None
    return (start, end)


def pre_season(driver: pl.DataFrame, window: tuple[int, int]) -> pl.DataFrame:
    """Mean temperature over the window per site-year, only where every window month is present."""
    start, end = window
    return (
        driver.filter(pl.col("month").is_between(start, end))
        .group_by("site_id", "year")
        .agg(temperature=pl.col("value").mean(), months=pl.len())
        .filter(pl.col("months") == WINDOW_MONTHS)
        .drop("months")
    )


# --- The fit --------------------------------------------------------------------------------


def _within_fit(columns: Columns, *, with_year: bool) -> float:
    """The response, by within-site demeaning then least squares on the demeaned columns.

    `np.bincount` rather than a group_by, because the bootstrap calls this a thousand times per
    unit on resampled rows, and a site's mean over duplicated rows is exactly what the resample
    intends.
    """
    site = columns.site
    counts = np.bincount(site).astype(float)
    counts[counts == 0] = np.nan

    def demean(values: np.ndarray) -> np.ndarray:
        means = np.bincount(site, weights=values) / counts
        return np.asarray(values - means[site], dtype=float)

    y = demean(columns.flight)
    design_columns = [demean(columns.temperature)]
    if with_year:
        design_columns.append(demean(columns.year.astype(float)))
    design = np.column_stack(design_columns)
    if np.linalg.matrix_rank(design) < design.shape[1]:
        return float("nan")
    solution, *_ = np.linalg.lstsq(design, y, rcond=None)
    return float(solution[0])


def _year_bootstrap(
    columns: Columns, *, name: str, clustered: bool, draws: int
) -> tuple[float, float]:
    """A percentile interval on arm B's response, over years or over rows."""
    rng = np.random.default_rng(_seed(f"{name}:{'years' if clustered else 'rows'}"))
    blocks = [np.flatnonzero(columns.year == value) for value in np.unique(columns.year)]
    values = np.empty(draws, dtype=float)
    for draw in range(draws):
        if clustered:
            picked = rng.integers(0, len(blocks), size=len(blocks))
            rows = np.concatenate([blocks[index] for index in picked])
        else:
            rows = rng.integers(0, columns.site.size, size=columns.site.size)
        values[draw] = _within_fit(columns.take(rows), with_year=True)
    finite = values[np.isfinite(values)]
    if finite.size < draws // 2:
        return (float("nan"), float("nan"))
    low, high = np.percentile(finite, [2.5, 97.5])
    return (float(low), float(high))


def _trend_per_decade(years: np.ndarray, values: np.ndarray) -> float:
    if np.unique(years).size < MIN_POINTS:
        return float("nan")
    return float(stats.linregress(years.astype(float), values).slope * 10.0)


def unit_response(
    panel: pl.DataFrame, *, unit: str, window: tuple[int, int], draws: int = DRAWS
) -> UnitResponse:
    """One species-generation, end to end.

    `panel` carries `site_id`, `year`, `flight_day`, `temperature`, and the unit's `label` and
    `generation` on every row.
    """
    codes, site = np.unique(panel["site_id"].to_numpy(), return_inverse=True)
    columns = Columns(
        site=np.asarray(site, dtype=int),
        flight=panel["flight_day"].to_numpy().astype(float),
        temperature=panel["temperature"].to_numpy().astype(float),
        year=panel["year"].to_numpy().astype(int),
    )
    label = str(panel["label"][0])

    per_year = panel.group_by("year").agg(pl.col("temperature").mean()).sort("year")
    series = panel.select(site_id="site_id", year="year", mean_latitude="flight_day")
    trends = range_metrics.shift_per_decade(
        series, column="mean_latitude", group_by=("site_id",), min_years=MIN_YEARS
    )
    return UnitResponse(
        unit=unit,
        label=label,
        generation=str(panel["generation"][0]),
        migrant=label in MIGRANTS,
        years=int(np.unique(columns.year).size),
        sites=int(codes.size),
        rows=int(columns.site.size),
        window=window,
        response_a=_within_fit(columns, with_year=False),
        response_b=_within_fit(columns, with_year=True),
        interval_b=_year_bootstrap(columns, name=unit, clustered=True, draws=draws),
        naive_b=_year_bootstrap(columns, name=unit, clustered=False, draws=draws),
        warming=_trend_per_decade(
            per_year["year"].to_numpy(), per_year["temperature"].to_numpy().astype(float)
        ),
        advance=(
            float(np.median(trends["per_decade"].to_numpy().astype(float)))
            if trends.height
            else float("nan")
        ),
    )


def responses(
    flight: pl.DataFrame, driver: pl.DataFrame, *, draws: int = DRAWS
) -> tuple[list[UnitResponse], int]:
    """Every species-generation that clears the floors, and how many did not."""
    out: list[UnitResponse] = []
    dropped = 0
    for (unit,), rows in flight.group_by(["unit"], maintain_order=True):
        window = window_for(flight_month(rows["flight_day"].to_numpy().astype(float)))
        if window is None:
            log.info("%s: median flight too early for a pre-season; coverage", unit)
            dropped += 1
            continue
        panel = rows.join(pre_season(driver, window), on=["site_id", "year"], how="inner")
        years = panel["year"].n_unique()
        sites = panel["site_id"].n_unique()
        if years < MIN_YEARS or sites < MIN_SITES:
            log.info("%s: %d years, %d sites; under a floor", unit, years, sites)
            dropped += 1
            continue
        result = unit_response(panel, unit=str(unit), window=window, draws=draws)
        log.info(
            "%s (%s): S_B %+.2f [%+.2f, %+.2f] d/degC over %d years, %d sites; W %+.2f, A %+.2f",
            result.label, result.generation, result.response_b, *result.interval_b,
            result.years, result.sites, result.warming, result.advance,
        )  # fmt: skip
        out.append(result)
    return out, dropped


# --- Pooled ---------------------------------------------------------------------------------


def _median_interval(values: np.ndarray, *, name: str, draws: int = DRAWS) -> tuple[float, float]:
    rng = np.random.default_rng(_seed(name))
    finite = values[np.isfinite(values)]
    if finite.size < MIN_POINTS:
        return (float("nan"), float("nan"))
    medians = np.array(
        [np.median(rng.choice(finite, size=finite.size, replace=True)) for _ in range(draws)]
    )
    low, high = np.percentile(medians, [2.5, 97.5])
    return (float(low), float(high))


def heterogeneity(units: Sequence[UnitResponse]) -> tuple[float, float]:
    """Cochran's Q across the units' arm-B responses, weighted by their own standard errors."""
    usable = [u for u in units if np.isfinite(u.stderr_b) and u.stderr_b > 0]
    if len(usable) < MIN_POINTS:
        return (float("nan"), float("nan"))
    values = np.array([u.response_b for u in usable])
    weights = np.array([1.0 / u.stderr_b**2 for u in usable])
    centre = float(np.sum(weights * values) / np.sum(weights))
    return (
        float(np.sum(weights * (values - centre) ** 2)),
        float(stats.chi2.ppf(0.95, len(usable) - 1)),
    )


def pooled(units: Sequence[UnitResponse], *, draws: int = DRAWS) -> Pooled | None:
    """The network as a summary of its species."""
    if len(units) < MIN_UNITS:
        log.warning("phase2d: %d units clear the floors, under %d", len(units), MIN_UNITS)
        return None
    a = np.array([u.response_a for u in units])
    b = np.array([u.response_b for u in units])
    warming = np.array([u.warming for u in units])
    explained = np.array([u.explained for u in units])
    advance = np.array([u.advance for u in units])
    q, bar = heterogeneity(units)
    migrants = np.array([u.response_b for u in units if u.migrant])
    residents = np.array([u.response_b for u in units if not u.migrant])

    def refit(subset: Sequence[UnitResponse]) -> tuple[float, float]:
        values = np.array([u.response_b for u in subset])
        low, high = _median_interval(values, name="phase2d:median:loo", draws=200)
        centre = float(np.nanmedian(values))
        return (centre, max(abs(centre - low), abs(high - centre)))

    return Pooled(
        units=len(units),
        median_a=float(np.nanmedian(a)),
        median_b=float(np.nanmedian(b)),
        interval_b=_median_interval(b, name="phase2d:median", draws=draws),
        q_statistic=q,
        q_bar=bar,
        median_warming=float(np.nanmedian(warming)),
        warming_interval=_median_interval(warming, name="phase2d:warming", draws=draws),
        share=float(np.nanmedian(explained) / np.nanmedian(advance)),
        median_advance=float(np.nanmedian(advance)),
        migrant_median=float(np.nanmedian(migrants)) if migrants.size else float("nan"),
        resident_median=float(np.nanmedian(residents)) if residents.size else float("nan"),
        # ADR 0016 binds on a small panel only; above its floor one unit cannot carry a median.
        leverage=(
            leave_one_out(list(units), refit, name=lambda u: u.label)
            if len(units) < SMALL_PANEL
            else None
        ),
    )


# --- The phase ------------------------------------------------------------------------------


def collect(*, draws: int = DRAWS, timing: TimingResult | None = None) -> Phase2d | None:
    """Calibrate against `flight-advance`, then every unit, then the pooled summary.

    `timing` lets the ledger hand in the `phase1k.timing()` it has already computed for
    `flight-advance`, so the calibration is against that very object rather than a second run of
    twelve thousand fits and their nulls.
    """
    if timing is None:
        from migratlas.reports import phase1k  # noqa: PLC0415 -- heavy, and only the calibration

        timing = phase1k.timing()
    if timing is None:
        log.warning("phase2d: phase1k.timing() returned nothing, so there is no calibration")
        return None

    flight = flights()
    driver = temperatures()
    if flight.is_empty() or driver.is_empty():
        log.warning("phase2d: no flight dates or no UK driver rows in the lake")
        return None
    sites = flight.select("site_id", "site_latitude", "site_longitude").unique(subset=["site_id"])
    landed = coverage(sites, driver)
    units, dropped = responses(flight, driver, draws=draws)
    return Phase2d(
        calibration=timing.median,
        coverage=landed,
        units=tuple(units),
        dropped=dropped,
        pooled=pooled(units, draws=draws),
    )


def _grade(passed: bool) -> str:  # noqa: FBT001 -- a grade is a boolean by nature
    return "TRUE" if passed else "FALSE"


def render() -> str:
    """The calibration, the coverage, every unit, the pooled block, one verdict line."""
    out = [
        "Phase 2d -- does the butterflies' flight date follow the temperature?",
        "=" * 78,
        "Pre-registered in docs/methods/phase2d-flight-response.md before any fetch. The unit is",
        "the species-generation; the response is fitted within site with a year term and its",
        "interval is clustered on year. Predictions are graded in the note, not here.",
        "",
    ]
    read = collect()
    if read is None:
        return "\n".join([*out, "VERDICT: nothing to read -- see the log."])

    out += [
        f"Calibration -- flight-advance median {read.calibration:+.4f} against "
        f"{CALIBRATION_MEDIAN:+.3f}: {'PASS' if read.calibrated else 'FAIL'}",
        f"Coverage -- {read.coverage.matched} of {read.coverage.sites} sites matched a cell, "
        f"{read.coverage.within} within {MATCH_KM:.0f} km ({read.coverage.share_within:.1%}), "
        f"furthest {read.coverage.furthest_km:.1f} km: "
        f"{'landed' if read.coverage.landed else 'DID NOT land'}",
        "",
    ]
    if not read.calibrated:
        return "\n".join([*out, "VERDICT: calibration FAILED -- nothing above it is interpreted."])

    out.append(
        f"Units -- {len(read.units)} clear the floors, {read.dropped} published as coverage; "
        f"{read.clear} of {len(read.units)} have a year-clustered interval excluding zero"
    )
    for u in sorted(read.units, key=lambda u: u.response_b):
        flag = ", migrant" if u.migrant else ""
        out.append(
            f"  {u.label:<24} {u.generation:<16} months {u.window[0]}-{u.window[1]}  "
            f"S_A {u.response_a:+6.2f}  S_B {u.response_b:+6.2f} [{u.interval_b[0]:+.2f}, "
            f"{u.interval_b[1]:+.2f}]  W {u.warming:+.2f}  A {u.advance:+.2f}  "
            f"({u.years} yr, {u.sites} sites{flag})"
        )
    out.append("")

    p = read.pooled
    if p is None:
        return "\n".join([*out, f"VERDICT: fewer than {MIN_UNITS} units -- coverage statement."])

    out += [
        f"Pooled over {p.units} species-generations",
        f"  median S, arm A (no year term) {p.median_a:+.3f} d/degC",
        f"  median S, arm B (year term)    {p.median_b:+.3f} d/degC, units-bootstrap "
        f"[{p.interval_b[0]:+.3f}, {p.interval_b[1]:+.3f}]",
        f"  negative and clear of zero: {_grade(p.negative_and_clear)}; stronger than the "
        f"radar's {RADAR_RESPONSE:+.2f}: {_grade(p.stronger_than_radar)}",
        f"  median W {p.median_warming:+.3f} degC/decade [{p.warming_interval[0]:+.3f}, "
        f"{p.warming_interval[1]:+.3f}] -- warmed: {_grade(p.warmed)}",
        f"  Cochran's Q across species {p.q_statistic:.1f} against a bar of {p.q_bar:.1f} -- "
        f"the responses are the species': {_grade(p.heterogeneous)}",
        f"  thermal share median(S x W) / median(A) = {p.share:.2f} "
        f"(median A {p.median_advance:+.2f} d/decade) against the radar's {RADAR_SHARE:.2f}: "
        f"{_grade(p.more_thermal_than_radar)}",
        f"  |arm B| < |arm A|: {_grade(p.year_term_shrinks)}",
        f"  migrants {p.migrant_median:+.2f} against residents {p.resident_median:+.2f}: "
        f"migrants respond less: {_grade(p.migrants_respond_less)}",
    ]
    if p.leverage is not None:
        out.append(
            f"  ADR 0016 on the median: publishable {'yes' if p.leverage.publishable else 'NO'}"
        )
    out.append("")
    return "\n".join(
        [
            *out,
            f"VERDICT: median S {p.median_b:+.2f} d/degC "
            f"[{p.interval_b[0]:+.2f}, {p.interval_b[1]:+.2f}] over {p.units} units; "
            f"Q {p.q_statistic:.1f} vs {p.q_bar:.1f}; share {p.share:.2f}",
        ]
    )
