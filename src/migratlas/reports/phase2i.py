"""Phase 2i -- is the radar's residual in the front's speed, or in the departure?

Pre-registered in ``docs/methods/phase2i-front-speed.md`` before any latitude gradient of passage
date was fitted. A passage date is a transit observation whose cause sits upstream in a residence
phase: it is the departure date plus the time spent getting there, and that time is flying and
stopping over in alternation. Every driver ever fitted to this record was a residence-side driver.
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final
from zlib import crc32

import numpy as np
import polars as pl

from migratlas.constants import MIN_COVERAGE
from migratlas.evidence.types import EvidenceType
from migratlas.lake.reader import scan
from migratlas.reports import phase1, phase1c, phase2a_timing
from migratlas.reports.phase1 import AUTUMN, SPRING
from migratlas.reports.phase1_robustness import FLEET_MIDPOINT_YEAR

if TYPE_CHECKING:
    from migratlas.metrics.phenology import Season

log = logging.getLogger(__name__)

SEED: Final = 1
DRAWS: Final = 1_000

KM_PER_DEGREE: Final = 111.19
"""One degree of latitude, in kilometres. The front's distance, and a lower bound on the path."""

PRIMARY_BAND: Final[tuple[float, float]] = (30.0, 50.0)
"""Registered primary: twenty degrees, to give the gradient something to be fitted over."""
CLAIM_BAND: Final[tuple[float, float]] = (37.0, 50.0)
"""Phase 2a's own band, carried for comparability with the published `S`."""

MIN_PANEL: Final = 20
"""Stations a year needs before its gradient is fitted."""
DUTY_CYCLE_BAR: Final = 0.25
"""Prediction 2: below this, the front advances as if the birds flew under a quarter of the dark."""

STEP_CHECK: Final[dict[float, float]] = {28.0: 2.16, 46.0: 0.01}
"""Phase 1c's published autumn step by latitude band, for prediction 5's consistency check."""
STEP_CHECK_ERROR: Final = 0.66
"""Phase 1c's stated error on the mean autumn step."""

QUANTITY: Final = "reflectivity_traffic"
NIGHT: Final = "night"


def _seed(name: str) -> int:
    return (crc32(name.encode()) ^ SEED) & 0x7FFF_FFFF


@dataclass(frozen=True, slots=True)
class YearFit:
    """One year's gradient: where the front was, and how fast it crossed a degree."""

    year: int
    intercept: float
    """Median passage day of year at the panel's mean latitude."""
    slope: float
    """Days per degree of latitude. Negative in autumn, when the birds move south."""
    stations: int

    @property
    def front_km_per_day(self) -> float:
        """The isochrone's speed. A lower bound: latitude is not the path."""
        return KM_PER_DEGREE / abs(self.slope) if self.slope else float("nan")


@dataclass(frozen=True, slots=True)
class Trend:
    """A per-decade drift and a 2012 step in one series, with year-resampled intervals."""

    per_decade: float
    decade_interval: tuple[float, float]
    step: float
    step_interval: tuple[float, float]

    @staticmethod
    def _clear(interval: tuple[float, float]) -> bool:
        low, high = interval
        return bool(np.isfinite(low) and np.isfinite(high)) and (high < 0.0 or low > 0.0)

    @property
    def trend_clear(self) -> bool:
        return self._clear(self.decade_interval)

    @property
    def step_clear(self) -> bool:
        return self._clear(self.step_interval)


@dataclass(frozen=True, slots=True)
class Speeds:
    """One year's front, flight and the ratio between them."""

    year: int
    front_km_per_day: float
    flight_km_per_hour: float
    night_hours: float

    @property
    def duty_cycle(self) -> float:
        """The share of the night's darkness the front advances as if the birds had flown."""
        available = self.flight_km_per_hour * self.night_hours
        return self.front_km_per_day / available if available > 0 else float("nan")


@dataclass(frozen=True, slots=True)
class Band:
    """One latitude band, fitted."""

    name: str
    low: float
    high: float
    stations: int
    mean_latitude: float
    fits: tuple[YearFit, ...]
    speeds: tuple[Speeds, ...]
    slope_trend: Trend | None
    intercept_trend: Trend | None

    @property
    def median_duty_cycle(self) -> float:
        values = np.array([s.duty_cycle for s in self.speeds])
        finite = values[np.isfinite(values)]
        return float(np.median(finite)) if finite.size else float("nan")

    @property
    def front_mostly_stationary(self) -> bool:
        return bool(np.isfinite(self.median_duty_cycle)) and self.median_duty_cycle < DUTY_CYCLE_BAR

    def implied_step_at(self, latitude: float) -> float:
        """The passage-date step the slope's own step implies at one latitude, in days."""
        if self.slope_trend is None:
            return float("nan")
        return self.slope_trend.step * (latitude - self.mean_latitude)


@dataclass(frozen=True, slots=True)
class Phase2i:
    primary: Band | None
    claim: Band | None
    spring: Trend | None
    """The spring slope's own 2012 step -- prediction 6's control, not a claim."""
    airspeed_level: float

    @property
    def step_consistent(self) -> bool:
        """Prediction 5: the slope's step reproduces Phase 1c's published step by latitude."""
        if self.primary is None or self.primary.slope_trend is None:
            return False
        return all(
            abs(self.primary.implied_step_at(latitude) - published) <= STEP_CHECK_ERROR
            for latitude, published in STEP_CHECK.items()
        )


# --- The panel ------------------------------------------------------------------------------


def fixed_panel(frame: pl.DataFrame, band: tuple[float, float]) -> pl.DataFrame:
    """Stations inside the band that carry a passage date in every year of the record.

    A gradient fitted on a changing panel is partly a gradient in which stations exist: the network
    runs 104 stations in 1995 and 159 by 2017. Phase 1c fixed its panel for the same reason.
    """
    low, high = band
    inside = frame.filter(pl.col("station_latitude").is_between(low, high))
    if inside.is_empty():
        return inside
    years = inside["year"].n_unique()
    complete = (
        inside.group_by("station_id")
        .agg(pl.col("year").n_unique().alias("years"))
        .filter(pl.col("years") == years)
        .select("station_id")
    )
    return inside.join(complete, on="station_id", how="inner").sort("station_id", "year")


def year_fits(panel: pl.DataFrame, mean_latitude: float) -> list[YearFit]:
    """Least squares of passage date on centred latitude, one fit per year."""
    out: list[YearFit] = []
    for (year,), group in panel.sort("year", "station_id").group_by(["year"], maintain_order=True):
        if group.height < MIN_PANEL:
            continue
        latitude = group["station_latitude"].to_numpy().astype(float) - mean_latitude
        response = group["q50_doy"].to_numpy().astype(float)
        design = np.column_stack([np.ones_like(latitude), latitude])
        if np.linalg.matrix_rank(design) < design.shape[1]:
            continue
        coefficients, *_ = np.linalg.lstsq(design, response, rcond=None)
        out.append(
            YearFit(
                year=int(year),
                intercept=float(coefficients[0]),
                slope=float(coefficients[1]),
                stations=group.height,
            )
        )
    return out


def night_hours(stations: pl.Series, season: Season) -> pl.DataFrame:
    """Traffic-weighted mean length of the observation night, per year, in hours.

    Read here rather than through `phase1.load_conus_nights`, which does not carry
    `integration_hours` and is called from twenty-five places. Night length is not an analysis
    decision, and the decisions that are -- the station set, the season, the coverage floor -- come
    from the panel and the shared constants rather than from a second copy of the filters.
    """
    rows = (
        scan(EvidenceType.FLUX, source_id=phase1.SOURCE_ID)
        .filter(
            pl.col("window_kind") == NIGHT,
            pl.col("quantity") == QUANTITY,
            pl.col("coverage_fraction") >= MIN_COVERAGE,
            pl.col("integration_hours").is_not_null(),
            pl.col("magnitude") > 0,
            pl.col("station_id").is_in(stations.implode()),
        )
        .select(
            year=pl.col("timestamp").dt.year(),
            doy=pl.col("timestamp").dt.ordinal_day(),
            hours=pl.col("integration_hours"),
            magnitude=pl.col("magnitude"),
        )
        .collect()
        .filter(pl.col("doy").is_between(season.start_doy, season.end_doy))
    )
    if rows.is_empty():
        return rows
    return (
        rows.group_by("year")
        .agg(
            night_hours=(pl.col("hours") * pl.col("magnitude")).sum() / pl.col("magnitude").sum(),
        )
        .sort("year")
    )


def airspeed_nights() -> pl.DataFrame:
    """Every station-night with an airspeed, loaded once.

    `phase1c` is called rather than reimplemented: the wind join, the coverage floor and the
    traffic weighting are its registered decisions and the `composition-stable` finding rests on
    them. Loaded once and passed down because it is 901,083 rows joined to a driver, and the two
    bands and the level would otherwise each pay for it.
    """
    return phase1c._airspeed_nights(2025)  # noqa: SLF001 -- one copy of the wind join, not two


def flight_speeds(nights: pl.DataFrame, stations: pl.Series, season: Season) -> pl.DataFrame:
    """Traffic-weighted airspeed per year, in m/s, for one station set."""
    if nights.is_empty():
        return pl.DataFrame()
    per_station_year = phase1c._per_station_year(  # noqa: SLF001 -- Phase 1c's own weighting
        nights.filter(pl.col("station_id").is_in(stations.implode())), season
    )
    if per_station_year.is_empty():
        return pl.DataFrame()
    return (
        per_station_year.group_by("year")
        .agg(airspeed=pl.col("airspeed").mean(), stations=pl.len())
        .sort("year")
    )


# --- The trends -----------------------------------------------------------------------------


def trend_with_break(
    years: np.ndarray, values: np.ndarray, *, name: str, draws: int
) -> Trend | None:
    """Per-decade drift and 2012 step, with a year-resampling bootstrap around both.

    The specification is `phase1c.fit_break`'s, called rather than restated, because Phase 1a, 1c
    and 2a all carry the same break and a fourth copy of it is a fourth thing that can move.
    """
    finite = np.isfinite(values)
    years, values = years[finite], values[finite]
    fit = phase1c.fit_break(years, values, FLEET_MIDPOINT_YEAR)
    if fit is None:
        return None
    rng = np.random.default_rng(_seed(name))
    trends = np.full(draws, np.nan)
    steps = np.full(draws, np.nan)
    for draw in range(draws):
        picked = rng.integers(0, years.size, size=years.size)
        resampled = phase1c.fit_break(years[picked], values[picked], FLEET_MIDPOINT_YEAR)
        if resampled is not None:
            trends[draw] = resampled.trend * 10.0
            steps[draw] = resampled.step
    return Trend(
        per_decade=fit.trend * 10.0,
        decade_interval=_interval(trends),
        step=fit.step,
        step_interval=_interval(steps),
    )


def _interval(values: np.ndarray) -> tuple[float, float]:
    finite = values[np.isfinite(values)]
    if finite.size < values.size // 2:
        return (float("nan"), float("nan"))
    low, high = np.percentile(finite, [2.5, 97.5])
    return (float(low), float(high))


def band_result(
    frame: pl.DataFrame,
    name: str,
    band: tuple[float, float],
    *,
    nights: pl.DataFrame,
    draws: int,
) -> Band | None:
    """One latitude band: its panel, its gradients, its speeds and its two trends."""
    panel = fixed_panel(frame, band)
    if panel.is_empty():
        return None
    mean_latitude = float(np.mean(panel["station_latitude"].to_numpy()))
    fits = year_fits(panel, mean_latitude)
    if not fits:
        return None

    stations = panel["station_id"].unique()
    speeds = _speeds(fits, stations, nights)
    years = np.array([fit.year for fit in fits], dtype=float)
    return Band(
        name=name,
        low=band[0],
        high=band[1],
        stations=int(stations.len()),
        mean_latitude=mean_latitude,
        fits=tuple(fits),
        speeds=tuple(speeds),
        slope_trend=trend_with_break(
            years,
            np.array([fit.slope for fit in fits]),
            name=f"{name}:slope",
            draws=draws,
        ),
        intercept_trend=trend_with_break(
            years,
            np.array([fit.intercept for fit in fits]),
            name=f"{name}:intercept",
            draws=draws,
        ),
    )


def _speeds(fits: list[YearFit], stations: pl.Series, nights: pl.DataFrame) -> list[Speeds]:
    """The front, the flight and the night, joined by year."""
    flight = flight_speeds(nights, stations, AUTUMN)
    nights = night_hours(stations, AUTUMN)
    if flight.is_empty() or nights.is_empty():
        return []
    per_year = flight.join(nights, on="year", how="inner")
    lookup = {
        int(row["year"]): (float(row["airspeed"]), float(row["night_hours"]))
        for row in per_year.to_dicts()
    }
    out: list[Speeds] = []
    for fit in fits:
        if fit.year not in lookup:
            continue
        airspeed, hours = lookup[fit.year]
        out.append(
            Speeds(
                year=fit.year,
                front_km_per_day=fit.front_km_per_day,
                # m/s to km/h.
                flight_km_per_hour=airspeed * 3.6,
                night_hours=hours,
            )
        )
    return out


def collect(*, draws: int = DRAWS) -> Phase2i:
    """Both bands in autumn, and the spring slope as prediction 6's control."""
    frame = phase2a_timing.panel()
    log.info(
        "passage panel: %d station-years, %d stations",
        frame.height,
        frame["station_id"].n_unique(),
    )
    nights = airspeed_nights()
    log.info("airspeed nights: %d rows", nights.height)
    primary = band_result(frame, "30-50N", PRIMARY_BAND, nights=nights, draws=draws)
    claim = band_result(frame, "37-50N", CLAIM_BAND, nights=nights, draws=draws)
    for band in (primary, claim):
        if band is not None:
            log.info(
                "%s: %d stations in every year, %d years fitted, mean latitude %.2f",
                band.name,
                band.stations,
                len(band.fits),
                band.mean_latitude,
            )

    spring = None
    spring_panel = fixed_panel(_spring_panel(), PRIMARY_BAND)
    if not spring_panel.is_empty():
        mean_latitude = float(np.mean(spring_panel["station_latitude"].to_numpy()))
        spring_fits = year_fits(spring_panel, mean_latitude)
        if spring_fits:
            spring = trend_with_break(
                np.array([fit.year for fit in spring_fits], dtype=float),
                np.array([fit.slope for fit in spring_fits]),
                name="spring:slope",
                draws=draws,
            )

    level = 0.0
    flight = flight_speeds(nights, frame["station_id"].unique(), AUTUMN)
    if not flight.is_empty():
        level = float(np.mean(flight["airspeed"].to_numpy()))
    return Phase2i(primary=primary, claim=claim, spring=spring, airspeed_level=level)


def _spring_panel() -> pl.DataFrame:
    """The same passage panel in spring, for the control only.

    Built here rather than in `phase2a_timing`, whose `panel()` is autumn's by registration and
    whose joins carry an autumn temperature this control does not use.
    """
    from migratlas.constants import MIN_NIGHTS  # noqa: PLC0415 -- only this function
    from migratlas.evidence import spec_for  # noqa: PLC0415
    from migratlas.metrics.phenology import passage_quantiles  # noqa: PLC0415

    nights = phase1.load_conus_nights(quantity=QUANTITY)
    quantiles = passage_quantiles(
        nights,
        spec_for(EvidenceType.FLUX),
        seasons=[SPRING],
        quantiles=[0.5],
        min_coverage=MIN_COVERAGE,
        min_observations=MIN_NIGHTS,
    ).filter(pl.col("q50_doy").is_not_null())
    sites = nights.group_by("station_id").agg(
        pl.col("station_latitude").first(), pl.col("station_longitude").first()
    )
    return quantiles.join(sites, on="station_id", how="inner")


# --- The report -----------------------------------------------------------------------------


def _band_lines(band: Band) -> list[str]:
    slope = band.slope_trend
    intercept = band.intercept_trend
    out = [
        f"  {band.name}: {band.stations} stations in every year, {len(band.fits)} years, "
        f"mean latitude {band.mean_latitude:.2f}",
    ]
    if band.speeds:
        front = float(np.median([s.front_km_per_day for s in band.speeds]))
        flight = float(np.median([s.flight_km_per_hour for s in band.speeds]))
        hours = float(np.median([s.night_hours for s in band.speeds]))
        out.append(
            f"    front {front:.0f} km/day; flight {flight:.1f} km/h over {hours:.1f} h of night; "
            f"duty cycle {band.median_duty_cycle:.3f} against a bar of {DUTY_CYCLE_BAR}"
        )
    if slope is not None:
        out.append(
            f"    slope (days/degree) {slope.per_decade:+.4f}/decade "
            f"[{slope.decade_interval[0]:+.4f}, {slope.decade_interval[1]:+.4f}]"
            f" ({'CLEARS' if slope.trend_clear else 'covers zero'}); "
            f"2012 step {slope.step:+.4f} "
            f"[{slope.step_interval[0]:+.4f}, {slope.step_interval[1]:+.4f}]"
            f" ({'CLEARS' if slope.step_clear else 'covers zero'})"
        )
        out.append(
            "    implied passage step: "
            + ", ".join(
                f"{latitude:.0f}N {band.implied_step_at(latitude):+.2f} d against {published:+.2f}"
                for latitude, published in STEP_CHECK.items()
            )
        )
    if intercept is not None:
        out.append(
            f"    intercept (days) {intercept.per_decade:+.3f}/decade "
            f"[{intercept.decade_interval[0]:+.3f}, {intercept.decade_interval[1]:+.3f}]; "
            f"2012 step {intercept.step:+.3f}"
        )
    return out


def render() -> str:
    """Both bands, the spring control, and one verdict line."""
    read = collect()
    out = [
        "Phase 2i -- is the radar's residual in the front's speed, or in the departure?",
        "=" * 78,
        "Pre-registered in docs/methods/phase2i-front-speed.md before any latitude gradient",
        "of passage date was fitted. The band-average trend is the intercept's by",
        "construction, so what is tested is whether anything latitude-graded lives in the",
        "slope. Predictions are graded in the note.",
        "",
        f"airspeed level, traffic-weighted: {read.airspeed_level:.3f} m/s",
        "",
    ]
    for band in (read.primary, read.claim):
        if band is None:
            continue
        out += _band_lines(band)
    if read.spring is not None:
        out += [
            "",
            f"  spring control: slope 2012 step {read.spring.step:+.4f} "
            f"[{read.spring.step_interval[0]:+.4f}, {read.spring.step_interval[1]:+.4f}]"
            f" ({'CLEARS' if read.spring.step_clear else 'covers zero'})",
        ]
    out.append("")

    verdict: list[str] = []
    band = read.primary
    if band is None:
        verdict.append("no band fitted")
    else:
        verdict.append(
            f"duty cycle {band.median_duty_cycle:.3f} -- the front "
            + (
                "is mostly stationary"
                if band.front_mostly_stationary
                else "is not mostly stationary"
            )
        )
        if band.slope_trend is not None:
            verdict.append(
                "the front's speed "
                + ("changed" if band.slope_trend.trend_clear else "did not change")
            )
            verdict.append(
                "the 2012 step "
                + ("is in the slope" if band.slope_trend.step_clear else "is not in the slope")
            )
        verdict.append(
            "the step's size "
            + ("reproduces" if read.step_consistent else "does not reproduce")
            + " Phase 1c's"
        )
        if read.spring is not None and read.spring.step_clear:
            same_sign = band.slope_trend is not None and (
                np.sign(read.spring.step) == np.sign(band.slope_trend.step)
            )
            verdict.append(
                "spring control FIRED (same sign)" if same_sign else "spring step reverses"
            )
        else:
            verdict.append("spring step covers zero -- uninformative, as registered")
    return "\n".join([*out, "VERDICT: " + "; ".join(verdict)])
