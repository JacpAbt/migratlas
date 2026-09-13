"""Phase 2j -- does an animal answer a hard winter by staying less, or by moving faster?

Pre-registered in ``docs/methods/phase2j-two-states.md`` before any state model was fitted to any
track here. A displacement measures the product of how long an animal moved and how fast it moved,
so an animal that covers the same ground by stopping less and one that covers it by moving faster
are the same number to every fit this project has published. Phase 1h measured the displacement;
this splits it.

**Phase 1h's refusal is this module's hardest problem, and it is answered rather than ignored.** It
chose displacement over path length because a path length tracks how often the collar fired. Three
things are done about that and none is a fix: steps are kept only where the interval is within 20%
of the source's own modal interval, the model is fitted per source so no interval is compared across
sources, and the registered control asks whether an animal-year's travelling fraction correlates
with that year's median fix interval at all. If it does, nothing here is read.
"""

import logging
from dataclasses import dataclass
from typing import Final
from zlib import crc32

import numpy as np
import polars as pl
from scipy import stats

from migratlas.evidence.types import EvidenceType
from migratlas.lake.reader import scan, scan_dataset
from migratlas.models import statespace

log = logging.getLogger(__name__)

SEED: Final = 1
DRAWS: Final = 1_000

SOURCES: Final[tuple[str, ...]] = (
    "movebank_yahatinda_elk",
    "movebank_mountain_caribou_bc",
    "movebank_missouri_bison",
    "movebank_bylot_fox_gps",
    "movebank_svalbard_reindeer",
    "movebank_hebblewhite_wolves",
)
"""The Argos fox is excluded by registration: a 24-hour interval and kilometres of Doppler error."""

SNOW_SOURCE: Final = "era5_land"
SNOW_VARIABLE: Final = "snow_depth_true_m"
SNOW_HERDS: Final[tuple[str, ...]] = ("movebank_yahatinda_elk", "movebank_svalbard_reindeer")
WINTER_MONTHS: Final[tuple[int, ...]] = (1, 2, 3)
"""Phase 3a's own winter window, so the two fits ask the same season."""

INTERVAL_TOLERANCE: Final = 0.2
"""A step counts if its gap is within this share of the source's modal interval."""
MIN_SEQUENCE: Final = 10
MIN_STEPS_PER_YEAR: Final = 200
MIN_ANIMAL_YEARS: Final = 30
MIN_HERD_ANIMALS: Final = 5
MIN_HERD_YEARS: Final = 10
MIN_SOURCES: Final = 4
MIN_SLOPE_POINTS: Final = 3
"""Three years make a slope."""
MIN_SLOPE_ANIMALS: Final = 3
SEPARATION_BAR: Final = 3.0
"""Prediction 2: the travelling state's mean step must be this many times the encamped state's."""
TRAVELLING_BAR: Final = 0.5
"""Prediction 3: below this, most of an animal's time is spent still."""
FIX_RATE_BAR: Final = 0.2
"""Prediction 4: Phase 1h's own bar, on the correlation with the collar."""

EARTH_KM: Final = 6371.0088


def _seed(name: str) -> int:
    return (crc32(name.encode()) ^ SEED) & 0x7FFF_FFFF


@dataclass(frozen=True, slots=True)
class AnimalYear:
    """One animal in one year: how much of its time moved, and how far each move went."""

    source: str
    individual_id: str
    year: int
    steps: int
    travelling_fraction: float
    travelling_step_km: float
    median_gap_hours: float


@dataclass(frozen=True, slots=True)
class Response:
    """A driver's effect on one quantity, pooled over animals with an animal-resampled interval."""

    slope: float
    interval: tuple[float, float]
    animals: int
    q_statistic: float
    q_bar: float

    @property
    def clear(self) -> bool:
        low, high = self.interval
        return bool(np.isfinite(low) and np.isfinite(high)) and (high < 0.0 or low > 0.0)

    @property
    def heterogeneous(self) -> bool:
        return bool(np.isfinite(self.q_statistic)) and self.q_statistic > self.q_bar


@dataclass(frozen=True, slots=True)
class SourceResult:
    """One tracking source, fitted."""

    source: str
    animals: int
    animal_years: int
    interval_hours: float
    separation: float
    median_travelling_fraction: float
    median_travelling_step_km: float
    fix_rate_rho: float
    dropped: str | None

    @property
    def passes(self) -> bool:
        return self.dropped is None

    @property
    def separates(self) -> bool:
        return bool(np.isfinite(self.separation)) and self.separation >= SEPARATION_BAR

    @property
    def mostly_still(self) -> bool:
        return (
            bool(np.isfinite(self.median_travelling_fraction))
            and self.median_travelling_fraction < TRAVELLING_BAR
        )

    @property
    def tracks_the_collar(self) -> bool:
        return bool(np.isfinite(self.fix_rate_rho)) and abs(self.fix_rate_rho) >= FIX_RATE_BAR


@dataclass(frozen=True, slots=True)
class HerdSnow:
    """One herd's answer to snow, in both states."""

    herd: str
    herd_years: int
    fraction: Response | None
    step: Response | None

    @property
    def stays_less(self) -> bool:
        return self.fraction is not None and self.fraction.clear and self.fraction.slope > 0

    @property
    def moves_faster(self) -> bool:
        return self.step is not None and self.step.clear and self.step.slope > 0


@dataclass(frozen=True, slots=True)
class Phase2j:
    sources: tuple[SourceResult, ...]
    herds: tuple[HerdSnow, ...]

    @property
    def passing(self) -> tuple[SourceResult, ...]:
        return tuple(s for s in self.sources if s.passes and s.separates)

    @property
    def controlled(self) -> bool:
        """Prediction 4, as the note's stop condition words it.

        Correction 1: the first run's gate refused to read anything if the control fired anywhere,
        where the registration drops *that source* and reads the rest. The note is the authority,
        so a source that fires is excluded from `readable` and the others stand.
        """
        return bool(self.readable)

    @property
    def readable(self) -> tuple[SourceResult, ...]:
        """Passing sources whose split does not track the collar."""
        return tuple(s for s in self.passing if not s.tracks_the_collar)


# --- The steps ------------------------------------------------------------------------------


def _haversine(
    lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray
) -> np.ndarray:
    """Great-circle distance in kilometres between consecutive fixes."""
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = phi2 - phi1
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2) ** 2
    return np.asarray(2 * EARTH_KM * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0))), dtype=float)


def _bearing(lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    """Initial bearing of each step, radians, for the turning angle between consecutive steps."""
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dlambda = np.radians(lon2 - lon1)
    y = np.sin(dlambda) * np.cos(phi2)
    x = np.cos(phi1) * np.sin(phi2) - np.sin(phi1) * np.cos(phi2) * np.cos(dlambda)
    return np.asarray(np.arctan2(y, x), dtype=float)


def load_source(source: str) -> pl.DataFrame:
    """One source's fixes, sorted, through the lake's own reader."""
    return (
        scan(EvidenceType.TRACK, source_id=source)
        .select("individual_id", "timestamp", "latitude", "longitude")
        .collect()
        .sort("individual_id", "timestamp")
    )


def modal_interval(frame: pl.DataFrame) -> float:
    """The source's own fix interval, in hours: the most common gap rounded to a tenth."""
    gaps = (
        frame.with_columns(
            gap=(pl.col("timestamp").diff().dt.total_seconds() / 3600.0).over("individual_id")
        )
        .filter(pl.col("gap") > 0)["gap"]
        .round(1)
    )
    if gaps.is_empty():
        return float("nan")
    counts = gaps.value_counts(sort=True)
    return float(counts["gap"][0])


def steps_of(frame: pl.DataFrame, interval: float) -> pl.DataFrame:
    """Step length, turning angle and gap per consecutive pair, kept near the modal interval.

    A run of kept steps within one animal-year is a sequence: the turning angle needs two steps in
    a row, so a break in the interval breaks the sequence rather than joining across the gap.
    """
    ordered = frame.sort("individual_id", "timestamp")
    animal = ordered["individual_id"].to_numpy()
    times = ordered["timestamp"].to_numpy()
    lat = ordered["latitude"].to_numpy().astype(float)
    lon = ordered["longitude"].to_numpy().astype(float)

    same = animal[1:] == animal[:-1]
    gap = (times[1:] - times[:-1]).astype("timedelta64[s]").astype(float) / 3600.0
    length = _haversine(lat[:-1], lon[:-1], lat[1:], lon[1:])
    bearing = _bearing(lat[:-1], lon[:-1], lat[1:], lon[1:])
    keep = same & (np.abs(gap - interval) <= INTERVAL_TOLERANCE * interval) & (length > 0)

    years = ordered["timestamp"].dt.year().to_numpy()[:-1]
    return pl.DataFrame(
        {
            "individual_id": animal[:-1],
            "year": years,
            "km": length,
            "bearing": bearing,
            "gap": gap,
            "keep": keep,
        }
    ).filter(pl.col("keep"))


def sequences_of(steps: pl.DataFrame) -> list[tuple[np.ndarray, np.ndarray]]:
    """Contiguous runs per animal-year, as (step length, turning angle) pairs.

    The turning angle is the change in bearing between one step and the next, wrapped to
    [-pi, pi]. The first step of a run has no previous bearing and takes zero, which the von Mises
    treats as a directed turn -- one step in a run of at least ten.
    """
    out: list[tuple[np.ndarray, np.ndarray]] = []
    for (_individual, _year), group in steps.group_by(
        ["individual_id", "year"], maintain_order=True
    ):
        km = group["km"].to_numpy().astype(float)
        bearing = group["bearing"].to_numpy().astype(float)
        if km.size < MIN_SEQUENCE:
            continue
        turn = np.zeros_like(bearing)
        turn[1:] = np.arctan2(
            np.sin(bearing[1:] - bearing[:-1]), np.cos(bearing[1:] - bearing[:-1])
        )
        out.append((km, turn))
    return out


def animal_years(steps: pl.DataFrame, model: statespace.TwoState, source: str) -> list[AnimalYear]:
    """Decode each animal-year and read off its travelling fraction and travelling step."""
    out: list[AnimalYear] = []
    for (individual, year), group in steps.group_by(["individual_id", "year"], maintain_order=True):
        km = group["km"].to_numpy().astype(float)
        if km.size < MIN_STEPS_PER_YEAR:
            continue
        bearing = group["bearing"].to_numpy().astype(float)
        turn = np.zeros_like(bearing)
        turn[1:] = np.arctan2(
            np.sin(bearing[1:] - bearing[:-1]), np.cos(bearing[1:] - bearing[:-1])
        )
        posterior = statespace.decode(model, km, turn)
        weight = posterior[:, 1]
        total = float(weight.sum())
        out.append(
            AnimalYear(
                source=source,
                individual_id=str(individual),
                year=int(year),
                steps=int(km.size),
                travelling_fraction=float(weight.mean()),
                travelling_step_km=float((weight * km).sum() / total)
                if total > 0
                else float("nan"),
                median_gap_hours=float(np.median(group["gap"].to_numpy().astype(float))),
            )
        )
    return out


# --- The driver -----------------------------------------------------------------------------


def winter_snow() -> pl.DataFrame:
    """Mean winter snow depth per herd-year, in metres, from the registered driver."""
    return (
        scan_dataset("driver_samples", source_id=SNOW_SOURCE)
        .filter(
            pl.col("variable") == SNOW_VARIABLE,
            pl.col("period_start").dt.month().is_in(list(WINTER_MONTHS)),
        )
        .select(
            herd=pl.col("site_id"),
            year=pl.col("period_start").dt.year(),
            value=pl.col("value"),
        )
        .group_by("herd", "year")
        .agg(snow=pl.col("value").mean())
        .sort("herd", "year")
        .collect()
    )


def _slope(x: np.ndarray, y: np.ndarray) -> tuple[float, float] | None:
    """One animal's slope against the driver, and that slope's own standard error.

    Correction 2 in the note: the first run pooled a single spread across animals as every
    animal's error, which makes Cochran's Q equal `n(n-1)` identically -- 44 animals gave 1892 and
    40 gave 1560, exactly. A statistic that is a function of the sample size carries no
    information, so the error is now each animal's own, from its own residuals.
    """
    if x.size < MIN_SLOPE_POINTS or np.ptp(x) == 0:
        return None
    design = np.column_stack([np.ones_like(x), x])
    coefficients, *_ = np.linalg.lstsq(design, y, rcond=None)
    residuals = y - design @ coefficients
    dof = x.size - design.shape[1]
    if dof < 1:
        return None
    variance = float(residuals @ residuals) / dof
    centred = float(np.sum((x - x.mean()) ** 2))
    if centred <= 0 or variance < 0:
        return None
    return (float(coefficients[1]), float(np.sqrt(variance / centred)))


def response(
    rows: list[AnimalYear], snow: pl.DataFrame, column: str, *, draws: int
) -> Response | None:
    """One herd's per-animal slope against winter snow, pooled with an animal-resampled interval."""
    lookup = {int(r["year"]): float(r["snow"]) for r in snow.to_dicts()}
    per_animal: dict[str, list[tuple[float, float]]] = {}
    for row in rows:
        if row.year not in lookup:
            continue
        value = getattr(row, column)
        if not np.isfinite(value):
            continue
        per_animal.setdefault(row.individual_id, []).append((lookup[row.year], float(value)))

    slopes: list[float] = []
    errors_list: list[float] = []
    for pairs in per_animal.values():
        x = np.array([p[0] for p in pairs])
        y = np.array([p[1] for p in pairs])
        fitted = _slope(x, y)
        if fitted is None:
            continue
        slope, stderr = fitted
        if np.isfinite(slope) and np.isfinite(stderr) and stderr > 0:
            slopes.append(slope)
            errors_list.append(stderr)
    if len(slopes) < MIN_SLOPE_ANIMALS:
        return None

    values = np.array(slopes)
    rng = np.random.default_rng(_seed(f"{column}:{len(slopes)}"))
    draws_out = np.array(
        [float(np.mean(rng.choice(values, size=values.size, replace=True))) for _ in range(draws)]
    )
    low, high = np.percentile(draws_out, [2.5, 97.5])
    errors = np.array(errors_list)
    weights = 1.0 / np.square(errors)
    mean = float(np.sum(weights * values) / np.sum(weights))
    return Response(
        slope=float(values.mean()),
        interval=(float(low), float(high)),
        animals=values.size,
        q_statistic=float(np.sum(weights * np.square(values - mean))),
        q_bar=float(stats.chi2.ppf(0.95, values.size - 1)),
    )


# --- The phase ------------------------------------------------------------------------------


def source_result(source: str) -> tuple[SourceResult, list[AnimalYear]]:
    """Fit one source and decode its animal-years."""
    frame = load_source(source)
    if frame.is_empty():
        return _empty(source, "no rows in the lake"), []
    interval = modal_interval(frame)
    if not np.isfinite(interval) or interval <= 0:
        return _empty(source, "no modal interval"), []

    steps = steps_of(frame, interval)
    sequences = sequences_of(steps)
    if not sequences:
        return _empty(source, "no sequence of ten steps at the modal interval"), []

    model = statespace.fit(sequences)
    if model is None:
        return _empty(source, "the two-state fit did not converge"), []

    rows = animal_years(steps, model, source)
    if len(rows) < MIN_ANIMAL_YEARS:
        return (
            _empty(source, f"{len(rows)} animal-years with 200 steps, under {MIN_ANIMAL_YEARS}"),
            rows,
        )

    fractions = np.array([r.travelling_fraction for r in rows])
    gaps = np.array([r.median_gap_hours for r in rows])
    rho = float(stats.spearmanr(fractions, gaps).statistic) if np.ptp(gaps) > 0 else 0.0
    return (
        SourceResult(
            source=source,
            animals=len({r.individual_id for r in rows}),
            animal_years=len(rows),
            interval_hours=interval,
            separation=model.separation,
            median_travelling_fraction=float(np.median(fractions)),
            median_travelling_step_km=float(
                np.median([r.travelling_step_km for r in rows if np.isfinite(r.travelling_step_km)])
            ),
            fix_rate_rho=rho if np.isfinite(rho) else 0.0,
            dropped=None,
        ),
        rows,
    )


def _empty(source: str, why: str) -> SourceResult:
    return SourceResult(
        source=source,
        animals=0,
        animal_years=0,
        interval_hours=float("nan"),
        separation=float("nan"),
        median_travelling_fraction=float("nan"),
        median_travelling_step_km=float("nan"),
        fix_rate_rho=float("nan"),
        dropped=why,
    )


def collect(*, draws: int = DRAWS) -> Phase2j:
    """Every source's split, and the two herds' answer to snow."""
    snow = winter_snow()
    results: list[SourceResult] = []
    per_source: dict[str, list[AnimalYear]] = {}
    for source in SOURCES:
        result, rows = source_result(source)
        results.append(result)
        per_source[source] = rows
        log.info(
            "%s: %d animal-years, interval %.2f h, separation %.2f%s",
            source.removeprefix("movebank_"),
            result.animal_years,
            result.interval_hours,
            result.separation,
            "" if result.passes else f" -- DROPPED: {result.dropped}",
        )

    herds: list[HerdSnow] = []
    for herd in SNOW_HERDS:
        rows = per_source.get(herd, [])
        herd_snow = snow.filter(pl.col("herd") == herd)
        years = {r.year for r in rows} & set(herd_snow["year"].to_list())
        if len(years) < MIN_HERD_YEARS or not rows:
            herds.append(HerdSnow(herd=herd, herd_years=len(years), fraction=None, step=None))
            continue
        herds.append(
            HerdSnow(
                herd=herd,
                herd_years=len(years),
                fraction=response(rows, herd_snow, "travelling_fraction", draws=draws),
                step=response(rows, herd_snow, "travelling_step_km", draws=draws),
            )
        )
    return Phase2j(sources=tuple(results), herds=tuple(herds))


def _source_lines(result: SourceResult) -> list[str]:
    name = result.source.removeprefix("movebank_")
    if not result.passes:
        return [f"  {name}: DROPPED -- {result.dropped}"]
    return [
        f"  {name}: {result.animals} animals, {result.animal_years} animal-years, "
        f"interval {result.interval_hours:.2f} h",
        f"    separation {result.separation:.2f}x "
        f"({'SEPARATES' if result.separates else 'does NOT separate'}); "
        f"travelling fraction {result.median_travelling_fraction:.3f} "
        f"({'mostly still' if result.mostly_still else 'NOT mostly still'}); "
        f"travelling step {result.median_travelling_step_km:.3f} km; "
        f"fix-rate rho {result.fix_rate_rho:+.3f}"
        f" ({'FIRES' if result.tracks_the_collar else 'quiet'})",
    ]


def _herd_lines(herd: HerdSnow) -> list[str]:
    name = herd.herd.removeprefix("movebank_")
    if herd.fraction is None and herd.step is None:
        return [f"  {name}: no snow fit ({herd.herd_years} shared years)"]
    out = [f"  {name}: {herd.herd_years} shared years"]
    for label, fit in (("fraction", herd.fraction), ("step km", herd.step)):
        if fit is None:
            out.append(f"    {label}: not fitted")
            continue
        out.append(
            f"    {label} per metre of snow {fit.slope:+.4f} "
            f"[{fit.interval[0]:+.4f}, {fit.interval[1]:+.4f}]"
            f" ({'CLEARS' if fit.clear else 'covers zero'}) over {fit.animals} animals; "
            f"Q {fit.q_statistic:.1f} against {fit.q_bar:.1f}"
        )
    return out


def render() -> str:
    """Every source's split, the two herds' snow answer, and one verdict line."""
    read = collect()
    out = [
        "Phase 2j -- does an animal answer a hard winter by staying less, or by moving faster?",
        "=" * 78,
        "Pre-registered in docs/methods/phase2j-two-states.md before any state model was",
        "fitted to any track here. The fix-rate control decides whether any of it is read:",
        "Phase 1h refused path lengths because they track the collar. Predictions are",
        "graded in the note.",
        "",
    ]
    for result in read.sources:
        out += _source_lines(result)
    out += ["", "snow, at the two herds with a driver:"]
    for herd in read.herds:
        out += _herd_lines(herd)
    out.append("")

    passing = read.passing
    readable = read.readable
    verdict: list[str] = []
    if len(passing) < MIN_SOURCES:
        verdict.append(f"coverage: {len(passing)} separating sources, under {MIN_SOURCES}")
    firing = [s.source.removeprefix("movebank_") for s in passing if s.tracks_the_collar]
    if firing:
        verdict.append(f"fix-rate control fired and dropped {', '.join(firing)}")
    if not readable:
        verdict.append("no source survives the control -- nothing is read")
    else:
        still = sum(1 for s in readable if s.mostly_still)
        verdict.append(
            f"{still} of {len(readable)} readable sources spend most of their time still"
        )
        for herd in read.herds:
            name = herd.herd.removeprefix("movebank_")
            if herd.fraction is None:
                verdict.append(f"{name}: no snow fit")
            elif herd.stays_less and not herd.moves_faster:
                verdict.append(f"{name}: stays less")
            elif herd.moves_faster and not herd.stays_less:
                verdict.append(f"{name}: moves faster")
            elif herd.stays_less and herd.moves_faster:
                verdict.append(f"{name}: both")
            else:
                verdict.append(f"{name}: neither")
    return "\n".join([*out, "VERDICT: " + "; ".join(verdict)])
