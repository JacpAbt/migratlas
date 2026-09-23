"""Phase 2f -- does when an animal moves have more than one cue?

Pre-registered in ``docs/methods/phase2f-second-cue.md`` before any second driver was fitted to a
timing response and before the fetch it needs. Every timing response this project has fitted had one
environmental column in it, so it could leave a residual and not name it. This adds the columns the
lake holds and phenology names: precipitation in the same months as the temperature, downward solar
radiation for the butterflies, and the green-up day of the animal's own 1-degree cell.

**Two records, two units.** The radar station in the claim band, autumn `q50_doy`, on Phase 2c's
panel and design -- intercept, centred year, temperature, wind support, the 2012 step -- with the
new column added to it. The butterfly species-generation on Phase 2d's panel, windows and floors,
its design -- site intercepts, temperature, year -- with the new column added to it.

**Two quantities per unit per arm.** The added driver's coefficient with its interval, and the
held-out error: leave-one-year-out prediction of the response with the model refitted without that
year each time. An arm's improvement over the temperature-only arm is one minus the ratio of their
held-out errors. The coefficient says whether a cue is there; the improvement says whether it is
worth knowing.
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, NamedTuple
from zlib import crc32

import numpy as np
import polars as pl

from migratlas.lake.reader import scan_dataset
from migratlas.reports import phase2d
from migratlas.reports.phase1_robustness import FLEET_MIDPOINT_YEAR
from migratlas.reports.phase3a import binomial_bar

if TYPE_CHECKING:
    from collections.abc import Sequence

log = logging.getLogger(__name__)

SEED: Final = 1
DRAWS: Final = 1_000

RADAR_CALIBRATION: Final = -0.624
"""Phase 2c's arm B, the mean sensitivity with a centred year term over the claim band."""
BUTTERFLY_CALIBRATION: Final = -4.70
"""Phase 2d's arm B, the median response over 75 species-generations."""
CALIBRATION_TOLERANCE: Final = 5e-3
"""Three significant figures on each, as the note promises."""

RADAR_IMPROVEMENT_BAR: Final = 0.05
"""Prediction 5: the full model's median held-out gain over temperature alone, for the radar."""
BUTTERFLY_IMPROVEMENT_BAR: Final = 0.10
"""Prediction 6: the same for the butterflies. Above it, claim 1 names a second cue."""

MIN_YEARS: Final = 15
MIN_POINTS: Final = 2

UK_DRIVER: Final = "era5_uk"
RADAR_DRIVER: Final = "era5"
GREENUP_DRIVER: Final = "pku_gimms_ndvi"

TEMPERATURE: Final = "air_temperature_2m"
PRECIPITATION: Final = "total_precipitation"
RADIATION: Final = "surface_solar_radiation_downwards"
GREENUP: Final = "greenup_day_of_year"

T: Final = "T"
P: Final = "P"
R: Final = "R"
G: Final = "G"

RADAR_PRE_SEASON: Final[tuple[int, int]] = (6, 7)
"""June and July, `phase2a-timing.md`'s window, the one its temperature is averaged over."""

CELL_DEG: Final = 1.0
"""The green-up grid. A site takes the cell it sits in."""

ARMS: Final[dict[str, tuple[str, ...]]] = {
    "T": (T,),
    "TP": (T, P),
    "TR": (T, R),
    "TG": (T, G),
}
"""The arms with a fixed driver list. Arm all is each record's own, from `Spec.drivers_of`."""
PAIR: Final = 2
"""An arm of two drivers is temperature plus one added cue; only those carry an added
coefficient."""


class Key(NamedTuple):
    """A unit's identity: its id and the label a reader sees."""

    unit: str
    label: str


@dataclass(frozen=True, slots=True)
class Spec:
    """What one record asks: its arms, its calibration target, its improvement bar, its interval."""

    name: str
    arms: tuple[str, ...]
    target: float
    improvement_bar: float
    clustered: bool
    """Year-clustered bootstrap intervals for a many-site unit; ordinary least squares for one."""

    def drivers_of(self, arm: str) -> tuple[str, ...]:
        """Arm all is temperature plus every cue this record asks: T+P+G for the radar, T+P+R+G
        for the butterflies. The first registered run gave arm all one shared list of four, and the
        radar, which never carries R, fitted no full model at any station."""
        if arm != "all":
            return ARMS[arm]
        return tuple(
            dict.fromkeys(name for other in self.arms if other != "all" for name in ARMS[other])
        )


RADAR_SPEC: Final = Spec(
    name="radar",
    arms=("T", "TP", "TG", "all"),
    target=RADAR_CALIBRATION,
    improvement_bar=RADAR_IMPROVEMENT_BAR,
    clustered=False,
)
BUTTERFLY_SPEC: Final = Spec(
    name="butterflies",
    arms=("T", "TP", "TR", "TG", "all"),
    target=BUTTERFLY_CALIBRATION,
    improvement_bar=BUTTERFLY_IMPROVEMENT_BAR,
    clustered=True,
)


@dataclass(frozen=True, slots=True)
class Panel:
    """One unit's rows as arrays: the response, the drivers by name, the year, the site codes."""

    site: np.ndarray
    """Dense integer site codes. A radar station is one site."""
    year: np.ndarray
    response: np.ndarray
    drivers: dict[str, np.ndarray]
    fixed: dict[str, np.ndarray]
    """Columns every arm carries beyond the intercept and the year: the radar's wind support and
    2012 step. Empty for the butterflies."""

    def columns(self, arm: tuple[str, ...]) -> np.ndarray:
        """The design's non-intercept columns, in a fixed order: drivers, fixed, year."""
        parts = [self.drivers[name] for name in arm]
        parts.extend(self.fixed.values())
        parts.append(self.year.astype(float))
        return np.column_stack(parts)

    def take(self, rows: np.ndarray) -> Panel:
        return Panel(
            site=self.site[rows],
            year=self.year[rows],
            response=self.response[rows],
            drivers={name: values[rows] for name, values in self.drivers.items()},
            fixed={name: values[rows] for name, values in self.fixed.items()},
        )

    def available(self, names: Sequence[str]) -> tuple[str, ...]:
        """The drivers with at least `MIN_YEARS` distinct years of finite values."""
        return tuple(
            name
            for name in names
            if name in self.drivers
            and np.unique(self.year[np.isfinite(self.drivers[name])]).size >= MIN_YEARS
        )

    def common(self, names: Sequence[str]) -> Panel:
        """The rows on which every named driver is finite -- the rows the arms are compared on."""
        keep = np.ones(self.site.size, dtype=bool)
        for name in names:
            keep &= np.isfinite(self.drivers[name])
        return self.take(np.flatnonzero(keep))


@dataclass(frozen=True, slots=True)
class ArmFit:
    """One unit under one arm."""

    arm: str
    coefficients: dict[str, float]
    """Per driver in the arm."""
    added: str | None
    """The driver this arm adds to arm T, or None for arm T and for arm all."""
    added_interval: tuple[float, float]
    held_out_rmse: float

    @property
    def added_clear(self) -> bool:
        low, high = self.added_interval
        return bool(np.isfinite(low) and np.isfinite(high) and (high < 0.0 or low > 0.0))


@dataclass(frozen=True, slots=True)
class UnitResult:
    """One unit, every arm."""

    unit: str
    label: str
    years: int
    sites: int
    arms: dict[str, ArmFit]

    def improvement(self, arm: str) -> float:
        if "T" not in self.arms or arm not in self.arms:
            return float("nan")
        base = self.arms["T"].held_out_rmse
        other = self.arms[arm].held_out_rmse
        return 1.0 - other / base if base > 0 and np.isfinite(other) else float("nan")


@dataclass(frozen=True, slots=True)
class DriverSummary:
    """One added driver across a record's units."""

    driver: str
    arm: str
    units: int
    clear: int
    bar: int
    median_coefficient: float
    coefficient_interval: tuple[float, float]
    median_improvement: float
    q_statistic: float
    q_bar: float

    @property
    def moves_more_than_chance(self) -> bool:
        return self.clear > self.bar

    @property
    def heterogeneous(self) -> bool:
        return bool(np.isfinite(self.q_statistic)) and self.q_statistic > self.q_bar


@dataclass(frozen=True, slots=True)
class Record:
    """The radar or the butterflies, pooled."""

    spec: Spec
    units: tuple[UnitResult, ...]
    calibration: float
    drivers: tuple[DriverSummary, ...]
    full_improvement: float
    """Median over units of arm all's improvement over arm T."""

    @property
    def calibrated(self) -> bool:
        return abs(self.calibration - self.spec.target) < CALIBRATION_TOLERANCE

    @property
    def temperature_dominant(self) -> bool:
        return self.full_improvement < self.spec.improvement_bar


@dataclass(frozen=True, slots=True)
class Phase2f:
    radar: Record | None
    butterflies: Record | None


def _seed(name: str) -> int:
    return (crc32(name.encode()) ^ SEED) & 0x7FFF_FFFF


# --- The fit --------------------------------------------------------------------------------


def _demean(values: np.ndarray, site: np.ndarray, counts: np.ndarray) -> np.ndarray:
    means = np.bincount(site, weights=values, minlength=counts.size) / counts
    return np.asarray(values - means[site], dtype=float)


def _design(panel: Panel, arm: tuple[str, ...]) -> tuple[np.ndarray, np.ndarray]:
    """The within-site demeaned response and design for one arm."""
    counts = np.bincount(panel.site).astype(float)
    counts[counts == 0] = np.nan
    y = _demean(panel.response, panel.site, counts)
    x = panel.columns(arm)
    design = np.column_stack([_demean(x[:, k], panel.site, counts) for k in range(x.shape[1])])
    return y, design


def fit(panel: Panel, arm: tuple[str, ...]) -> np.ndarray | None:
    """Within-site least squares on the arm's columns. Coefficients in `Panel.columns` order."""
    y, design = _design(panel, arm)
    if design.shape[0] <= design.shape[1] or np.linalg.matrix_rank(design) < design.shape[1]:
        return None
    solution, *_ = np.linalg.lstsq(design, y, rcond=None)
    return np.asarray(solution, dtype=float)


def _ols_interval(panel: Panel, arm: tuple[str, ...], index: int) -> tuple[float, float]:
    """A 95% interval on one coefficient from the residual variance -- for a single-site unit."""
    y, design = _design(panel, arm)
    dof = design.shape[0] - design.shape[1] - int(np.unique(panel.site).size)
    if dof < 1 or np.linalg.matrix_rank(design) < design.shape[1]:
        return (float("nan"), float("nan"))
    solution, *_ = np.linalg.lstsq(design, y, rcond=None)
    residuals = y - design @ solution
    sigma2 = float(residuals @ residuals) / dof
    covariance = sigma2 * np.linalg.pinv(design.T @ design)
    half = 1.96 * float(np.sqrt(covariance[index, index]))
    return (float(solution[index]) - half, float(solution[index]) + half)


def _year_interval(
    panel: Panel, arm: tuple[str, ...], index: int, *, name: str, draws: int
) -> tuple[float, float]:
    """A percentile interval on one coefficient, resampling years with all their rows."""
    rng = np.random.default_rng(_seed(f"{name}:{'+'.join(arm)}:years"))
    blocks = [np.flatnonzero(panel.year == value) for value in np.unique(panel.year)]
    values = np.empty(draws, dtype=float)
    for draw in range(draws):
        picked = rng.integers(0, len(blocks), size=len(blocks))
        rows = np.concatenate([blocks[i] for i in picked])
        solution = fit(panel.take(rows), arm)
        values[draw] = solution[index] if solution is not None else np.nan
    finite = values[np.isfinite(values)]
    if finite.size < draws // 2:
        return (float("nan"), float("nan"))
    low, high = np.percentile(finite, [2.5, 97.5])
    return (float(low), float(high))


def held_out_rmse(panel: Panel, arm: tuple[str, ...]) -> float:
    """Leave-one-year-out: refit without each year, predict its rows from the training means.

    A held-out row is predicted as its site's training mean response plus the coefficients times
    the row's departures from its site's training means, the year term included -- so the first and
    last years are predicted from one side of the trend, for every arm alike.
    """
    errors: list[np.ndarray] = []
    x_all = panel.columns(arm)
    width = int(panel.site.max()) + 1
    for year in np.unique(panel.year):
        test = panel.year == year
        training = panel.take(np.flatnonzero(~test))
        solution = fit(training, arm)
        if solution is None:
            continue
        counts = np.bincount(training.site, minlength=width).astype(float)
        counts[counts == 0] = np.nan
        mean_y = np.bincount(training.site, weights=training.response, minlength=width) / counts
        x_train = training.columns(arm)
        mean_x = np.column_stack(
            [
                np.bincount(training.site, weights=x_train[:, k], minlength=width) / counts
                for k in range(x_train.shape[1])
            ]
        )
        rows = np.flatnonzero(test)
        sites = panel.site[rows]
        known = np.isfinite(mean_y[sites])
        if not known.any():
            continue
        rows, sites = rows[known], sites[known]
        predicted = mean_y[sites] + (x_all[rows] - mean_x[sites]) @ solution
        errors.append(panel.response[rows] - predicted)
    if not errors:
        return float("nan")
    stacked = np.concatenate(errors)
    return float(np.sqrt(np.mean(stacked**2)))


def unit_result(panel: Panel, key: Key, spec: Spec, *, draws: int = DRAWS) -> UnitResult:
    """Every arm the record asks for, on one unit.

    Amendment A in the note: the green-up record runs 1982-2022 and the responses run past both
    ends, so the arms are fitted and compared on the rows every available driver has -- arm T
    included -- and a driver with fewer than `MIN_YEARS` finite years is not available to this unit.
    The calibration is arm T on the full panel, which is what the parent phases published.
    """
    wanted = spec.drivers_of("all")
    available = panel.available(wanted)
    common = panel.common(available)
    fits: dict[str, ArmFit] = {}
    full_t = fit(panel, (T,))
    if full_t is not None:
        fits["T_full"] = ArmFit(
            arm="T_full",
            coefficients={T: float(full_t[0])},
            added=None,
            added_interval=(float("nan"), float("nan")),
            held_out_rmse=float("nan"),
        )
    if np.unique(common.year).size < MIN_YEARS:
        return UnitResult(
            unit=key.unit,
            label=key.label,
            years=int(np.unique(panel.year).size),
            sites=int(np.unique(panel.site).size),
            arms=fits,
        )
    for arm in spec.arms:
        drivers = spec.drivers_of(arm)
        if any(name not in available for name in drivers):
            continue
        solution = fit(common, drivers)
        if solution is None:
            continue
        coefficients = {name: float(solution[k]) for k, name in enumerate(drivers)}
        added = drivers[-1] if len(drivers) == PAIR else None
        interval = (float("nan"), float("nan"))
        if added is not None:
            index = drivers.index(added)
            interval = (
                _year_interval(common, drivers, index, name=key.unit, draws=draws)
                if spec.clustered
                else _ols_interval(common, drivers, index)
            )
        fits[arm] = ArmFit(
            arm=arm,
            coefficients=coefficients,
            added=added,
            added_interval=interval,
            held_out_rmse=held_out_rmse(common, drivers),
        )
    return UnitResult(
        unit=key.unit,
        label=key.label,
        years=int(np.unique(common.year).size),
        sites=int(np.unique(common.site).size),
        arms=fits,
    )


# --- The panels -----------------------------------------------------------------------------


def _cell_of(latitude: float, longitude: float) -> str:
    """The green-up driver's own site id for the 1-degree cell containing a point."""
    lat = np.floor(latitude / CELL_DEG) * CELL_DEG + CELL_DEG / 2
    lon = np.floor(longitude / CELL_DEG) * CELL_DEG + CELL_DEG / 2
    return f"{lat:.1f},{lon:.1f}"


def greenup_by_cell() -> pl.DataFrame:
    """Green-up day per 1-degree cell per year, keyed by the driver's own site id."""
    return (
        scan_dataset("driver_samples", source_id=GREENUP_DRIVER)
        .filter(pl.col("variable") == GREENUP)
        .select(
            cell=pl.col("site_id").cast(pl.String),
            year=pl.col("period_start").dt.year().cast(pl.Int64),
            greenup=pl.col("value").cast(pl.Float64),
        )
        .collect()
    )


def radar_panels() -> tuple[list[tuple[Key, Panel]], int]:
    """One panel per claim-band station: Phase 2c's rows with June-July precipitation and the
    station's green-up day joined on. Returns the panels and how many lost the green-up."""
    from migratlas.reports import phase2c  # noqa: PLC0415 -- heavy
    from migratlas.reports.phase2a_timing import panel  # noqa: PLC0415 -- heavy

    frame = phase2c.claim_band(panel())
    rain = (
        scan_dataset("driver_samples", source_id=RADAR_DRIVER)
        .filter(
            pl.col("variable") == PRECIPITATION,
            pl.col("period_start").dt.month().is_between(*RADAR_PRE_SEASON),
        )
        .select(
            station_id=pl.col("site_id"),
            year=pl.col("period_start").dt.year(),
            value=pl.col("value"),
        )
        .group_by("station_id", "year")
        .agg(pl.col("value").mean().alias("precipitation"))
        .collect()
    )
    green = greenup_by_cell()
    out: list[tuple[Key, Panel]] = []
    without_green = 0
    for (station,), group in frame.sort("station_id").group_by(["station_id"], maintain_order=True):
        cell = _cell_of(float(group["station_latitude"][0]), float(group["station_longitude"][0]))
        rows = (
            group.join(rain, on=["station_id", "year"], how="inner")
            .join(green.filter(pl.col("cell") == cell).drop("cell"), on="year", how="left")
            .drop_nulls(["q50_doy", "temperature", "support", "precipitation"])
            .sort("year")
        )
        if rows.height < MIN_YEARS:
            continue
        years = rows["year"].to_numpy().astype(int)
        post = (years >= FLEET_MIDPOINT_YEAR).astype(float)
        fixed = {"support": rows["support"].to_numpy().astype(float)}
        if 0 < post.sum() < post.size:
            fixed["post_2012"] = post
        # The green-up rides along with its gaps -- the record ends in 2022 -- and `Panel.available`
        # decides per unit whether fifteen finite years remain; the first run demanded a value on
        # every row and lost the driver at all 78 stations over three missing years.
        drivers = {
            T: rows["temperature"].to_numpy().astype(float),
            P: rows["precipitation"].to_numpy().astype(float),
            G: rows["greenup"].to_numpy().astype(float),
        }
        if np.unique(years[np.isfinite(drivers[G])]).size < MIN_YEARS:
            without_green += 1
        out.append(
            (
                Key(unit=str(station), label=str(station)),
                Panel(
                    site=np.zeros(rows.height, dtype=int),
                    year=years,
                    response=rows["q50_doy"].to_numpy().astype(float),
                    drivers=drivers,
                    fixed=fixed,
                ),
            )
        )
    return out, without_green


def uk_drivers() -> pl.DataFrame:
    """Monthly temperature, precipitation and radiation per UK site, one row per site-year-month."""
    return (
        scan_dataset("driver_samples", source_id=UK_DRIVER)
        .filter(pl.col("variable").is_in([TEMPERATURE, PRECIPITATION, RADIATION]))
        .select(
            site_id=pl.col("site_id").cast(pl.String),
            year=pl.col("period_start").dt.year().cast(pl.Int64),
            month=pl.col("period_start").dt.month().cast(pl.Int64),
            variable=pl.col("variable"),
            value=pl.col("value").cast(pl.Float64),
        )
        .collect()
    )


def _cells_of_sites(flight: pl.DataFrame) -> pl.DataFrame:
    """Each site's 1-degree green-up cell, in the driver's own id format."""
    half = CELL_DEG / 2
    return (
        flight.select("site_id", "site_latitude", "site_longitude")
        .unique(subset=["site_id"])
        .with_columns(
            cell=pl.format(
                "{},{}",
                ((pl.col("site_latitude") / CELL_DEG).floor() * CELL_DEG + half).round(1),
                ((pl.col("site_longitude") / CELL_DEG).floor() * CELL_DEG + half).round(1),
            )
        )
        .select("site_id", "cell")
    )


def _seasonal(drivers: pl.DataFrame, window: tuple[int, int]) -> pl.DataFrame:
    """The three drivers averaged over one unit's pre-season, per site-year."""
    parts = [
        phase2d.pre_season(
            drivers.filter(pl.col("variable") == variable).select(
                "site_id", "year", "month", "value"
            ),
            window,
        ).rename({"temperature": name})
        for name, variable in ((T, TEMPERATURE), (P, PRECIPITATION), (R, RADIATION))
    ]
    seasonal = parts[0]
    for part in parts[1:]:
        seasonal = seasonal.join(part, on=["site_id", "year"], how="inner")
    return seasonal


def butterfly_panels() -> tuple[list[tuple[Key, Panel]], int]:
    """One panel per species-generation on Phase 2d's rows, windows and floors, with the three
    drivers over the unit's own pre-season and the site's green-up day joined on."""
    flight = phase2d.flights()
    drivers = uk_drivers()
    green = greenup_by_cell()
    if flight.is_empty() or drivers.is_empty():
        return [], 0
    sites = _cells_of_sites(flight)
    out: list[tuple[Key, Panel]] = []
    without_green = 0
    for (unit,), rows in flight.group_by(["unit"], maintain_order=True):
        window = phase2d.window_for(
            phase2d.flight_month(rows["flight_day"].to_numpy().astype(float))
        )
        if window is None:
            continue
        panel = (
            rows.join(_seasonal(drivers, window), on=["site_id", "year"], how="inner")
            .join(sites, on="site_id", how="left")
            .join(green, on=["cell", "year"], how="left")
            .sort(["site_id", "year"])
        )
        if (
            panel["year"].n_unique() < phase2d.MIN_YEARS
            or panel["site_id"].n_unique() < phase2d.MIN_SITES
        ):
            continue
        _, site = np.unique(panel["site_id"].to_numpy(), return_inverse=True)
        unit_years = panel["year"].to_numpy().astype(int)
        columns = {
            T: panel[T].to_numpy().astype(float),
            P: panel[P].to_numpy().astype(float),
            R: panel[R].to_numpy().astype(float),
            G: panel["greenup"].to_numpy().astype(float),
        }
        if np.unique(unit_years[np.isfinite(columns[G])]).size < MIN_YEARS:
            without_green += 1
        out.append(
            (
                Key(unit=str(unit), label=str(panel["label"][0])),
                Panel(
                    site=np.asarray(site, dtype=int),
                    year=panel["year"].to_numpy().astype(int),
                    response=panel["flight_day"].to_numpy().astype(float),
                    drivers=columns,
                    fixed={},
                ),
            )
        )
    return out, without_green


# --- Pooling --------------------------------------------------------------------------------


def _median_interval(values: np.ndarray, *, name: str, draws: int) -> tuple[float, float]:
    finite = values[np.isfinite(values)]
    if finite.size < MIN_POINTS:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(_seed(name))
    medians = np.array(
        [np.median(rng.choice(finite, size=finite.size, replace=True)) for _ in range(draws)]
    )
    low, high = np.percentile(medians, [2.5, 97.5])
    return (float(low), float(high))


def _heterogeneity(values: np.ndarray, halves: np.ndarray) -> tuple[float, float]:
    """Cochran's Q across units' coefficients, each weighted by its own interval half-width."""
    from scipy import stats  # noqa: PLC0415 -- one caller

    keep = np.isfinite(values) & np.isfinite(halves) & (halves > 0)
    if keep.sum() < MIN_POINTS:
        return (float("nan"), float("nan"))
    weights = 1.0 / (halves[keep] / 1.96) ** 2
    centre = float(np.sum(weights * values[keep]) / np.sum(weights))
    return (
        float(np.sum(weights * (values[keep] - centre) ** 2)),
        float(stats.chi2.ppf(0.95, int(keep.sum()) - 1)),
    )


def summarise(
    name: str, units: Sequence[UnitResult], arm: str, *, draws: int
) -> DriverSummary | None:
    """One added driver across a record."""
    fits = [(u, u.arms[arm]) for u in units if arm in u.arms and u.arms[arm].added is not None]
    if not fits:
        return None
    driver = fits[0][1].added or ""
    coefficients = np.array([f.coefficients[driver] for _, f in fits])
    halves = np.array([(f.added_interval[1] - f.added_interval[0]) / 2 for _, f in fits])
    improvements = np.array([u.improvement(arm) for u, _ in fits])
    q, bar = _heterogeneity(coefficients, halves)
    return DriverSummary(
        driver=driver,
        arm=arm,
        units=len(fits),
        clear=sum(1 for _, f in fits if f.added_clear),
        bar=int(binomial_bar(len(fits))),
        median_coefficient=float(np.nanmedian(coefficients)),
        coefficient_interval=_median_interval(coefficients, name=f"{name}:{arm}", draws=draws),
        median_improvement=float(np.nanmedian(improvements)),
        q_statistic=q,
        q_bar=bar,
    )


def record(spec: Spec, units: Sequence[UnitResult], *, calibration: float, draws: int) -> Record:
    """A record pooled: each added driver summarised, and the full model's gain."""
    summaries = tuple(
        summary
        for arm in spec.arms
        if arm not in ("T", "all")
        and (summary := summarise(spec.name, units, arm, draws=draws)) is not None
    )
    full = np.array([u.improvement("all") for u in units if "all" in u.arms])
    return Record(
        spec=spec,
        units=tuple(units),
        calibration=calibration,
        drivers=summaries,
        full_improvement=float(np.nanmedian(full)) if full.size else float("nan"),
    )


def _calibration(units: Sequence[UnitResult], *, mean: bool) -> float:
    """Arm T on each unit's full panel, pooled the way the parent phase pooled it."""
    values = np.array([u.arms["T_full"].coefficients[T] for u in units if "T_full" in u.arms])
    if values.size == 0:
        return float("nan")
    return float(np.mean(values)) if mean else float(np.median(values))


def collect(*, draws: int = DRAWS) -> Phase2f:
    """Both records, each calibrated against the response its parent phase published."""
    radar_panel_list, lost = radar_panels()
    radar_units = [
        unit_result(panel, key, RADAR_SPEC, draws=draws) for key, panel in radar_panel_list
    ]
    radar = None
    if radar_units:
        log.info("radar: %d stations, %d without fifteen green-up years", len(radar_units), lost)
        # Phase 2c pools its arms as a mean, so the radar calibrates on the mean.
        radar = record(
            RADAR_SPEC,
            radar_units,
            calibration=_calibration(radar_units, mean=True),
            draws=draws,
        )

    butterfly_panel_list, lost_b = butterfly_panels()
    butterfly_units = [
        unit_result(panel, key, BUTTERFLY_SPEC, draws=draws) for key, panel in butterfly_panel_list
    ]
    butterflies = None
    if butterfly_units:
        log.info(
            "butterflies: %d units, %d without fifteen green-up years",
            len(butterfly_units),
            lost_b,
        )
        # Phase 2d pools as a median, so the butterflies calibrate on the median.
        butterflies = record(
            BUTTERFLY_SPEC,
            butterfly_units,
            calibration=_calibration(butterfly_units, mean=False),
            draws=draws,
        )
    return Phase2f(radar=radar, butterflies=butterflies)


def _record_lines(item: Record) -> list[str]:
    out = [
        f"{item.spec.name} -- {len(item.units)} units; arm T {item.calibration:+.3f} against "
        f"{item.spec.target:+.3f}: {'PASS' if item.calibrated else 'FAIL'}",
    ]
    for d in item.drivers:
        out.append(
            f"  {d.arm}: {d.driver} clear of zero in {d.clear} of {d.units} (chance bar {d.bar}); "
            f"median coefficient {d.median_coefficient:+.3f} "
            f"[{d.coefficient_interval[0]:+.3f}, {d.coefficient_interval[1]:+.3f}]; "
            f"median held-out improvement {d.median_improvement:+.1%}; "
            f"Q {d.q_statistic:.1f} against {d.q_bar:.1f}"
        )
    dominant = "stays dominant" if item.temperature_dominant else "does NOT stay dominant"
    out += [
        f"  all: median held-out improvement over T {item.full_improvement:+.1%} against a bar "
        f"of {item.spec.improvement_bar:.0%} -- temperature {dominant}",
        "",
    ]
    return out


def render() -> str:
    """Both records, each calibrated first, and one verdict line."""
    out = [
        "Phase 2f -- does when an animal moves have more than one cue?",
        "=" * 78,
        "Pre-registered in docs/methods/phase2f-second-cue.md before any second driver was",
        "fitted. Each record's arm T must reproduce its parent's published response before",
        "anything else is read. Predictions are graded in the note.",
        "",
    ]
    read = collect()
    verdict: list[str] = []
    for item in (read.radar, read.butterflies):
        if item is None:
            continue
        out += _record_lines(item)
        if not item.calibrated:
            verdict.append(f"{item.spec.name} calibration FAILED")
            continue
        for d in item.drivers:
            moves = "moves" if d.moves_more_than_chance else "does not move"
            verdict.append(f"{item.spec.name} {d.driver} {moves} more than chance")
        verdict.append(f"{item.spec.name} full-model gain {item.full_improvement:+.1%}")
    if not verdict:
        verdict.append("nothing to read")
    return "\n".join([*out, "VERDICT: " + "; ".join(verdict)])
