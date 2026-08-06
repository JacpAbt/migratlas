"""Phase 1c: does the radar measurement mean the same thing in 2025 as in 1995?

Pre-registered in docs/methods/phase1c-homogeneity.md, including the predictions, before any
of this was run. Two of the three tests live here; the third needs a wind field and waits on
the driver panel.

Test A asks whether the Phase 1a trend survives dropping the speed weighting, since
``traffic`` integrates reflectivity x speed x height and ``reflectivity_hours`` does not.
Test B asks whether the unexplained 2012 step is the precipitation screening working less
hard, which the newly ingested ``rain_fraction`` can answer directly.
"""

import logging
from typing import Final, NamedTuple

import numpy as np
import polars as pl

from migratlas.drivers import era5, narr
from migratlas.drivers.schema import DRIVER_SAMPLES
from migratlas.evidence import EvidenceType, spec_for
from migratlas.lake.reader import scan_dataset
from migratlas.metrics.phenology import Season, passage_quantiles
from migratlas.reports.phase1 import (
    AUTUMN,
    LATITUDE_BANDS,
    MIN_COVERAGE,
    MIN_NIGHTS,
    MIN_YEARS,
    SPRING,
    load_conus_nights,
    station_slopes,
)
from migratlas.reports.phase1_robustness import FLEET_MIDPOINT_YEAR

log = logging.getLogger(__name__)

# The metric Horton et al. used, and the one every Phase 1a number is computed on.
CLAIM_QUANTITY: Final = "reflectivity_traffic"

# The same biomass without the speed weighting. Not a better metric in general -- a
# different one, whose only job here is to say whether the trend needs the speed term.
CONTROL_QUANTITY: Final = "reflectivity_hours"

# Where the Phase 1a autumn result actually lives, after the hierarchical model undercut the
# continent-wide version. Named so Test A is judged on the surviving claim, not a wider one.
CLAIM_BANDS: Final[tuple[tuple[int, int], ...]] = ((37, 42), (42, 50))

# How large a paired difference has to be before the speed weighting is doing real work.
# Set to the Phase 1a interval half-width: a shift the size of the existing uncertainty is
# not a robustness failure, and one larger than it is.
MATERIAL_DIFFERENCE: Final = 0.3

# Below this many stations a correlation across stations is not worth printing.
MIN_STATIONS: Final = 3

# Years a station must have on each side of the break to join the fixed panel.
PANEL_MARGIN: Final = 5

# Upper end of the insect airspeed range, against 8-15 m/s for nocturnal migrant songbirds
# (Shi et al. 2025). A reflectivity-weighted mean below this is a night whose traffic was not
# dominated by migrating birds. Not a classifier -- a flag on a mixture summary.
INSECT_AIRSPEED_MAX: Final = 5.0

# The exclusion check needs both the all-nights and bird-nights fits to compare.
BOTH_FITS: Final = 2

# Above this, the station-to-station variation in screening is tracking rainfall rather than
# noise. Modest on purpose: this is a sensitivity check on the test, not a claim of its own.
WEATHER_SIGNAL: Final = 0.2


class Paired(NamedTuple):
    """One latitude band's trend under both quantities, and the within-station difference."""

    label: str
    stations: int
    claim: float
    control: float
    difference: float
    ci95: float

    def __str__(self) -> str:
        return (
            f"{self.label:<10} n={self.stations:>3}  "
            f"traffic {self.claim:+.2f}   hours {self.control:+.2f}   "
            f"diff {self.difference:+.2f} +/- {self.ci95:.2f}"
        )


class BreakFit(NamedTuple):
    trend: float
    step: float


def _fit_break(years: np.ndarray, response: np.ndarray, break_year: int) -> BreakFit | None:
    """Least squares ``response ~ 1 + year + post_break``, returning both coefficients.

    ``phase1_robustness._slope`` fits the same design but returns only the trend, because
    there the step is a nuisance to absorb. Here the step *is* the object of study, so both
    come back.
    """
    post = (years >= break_year).astype(float)
    if not 0 < post.sum() < post.size:
        return None
    design = np.column_stack([np.ones_like(years, dtype=float), years.astype(float), post])
    if np.linalg.matrix_rank(design) < design.shape[1]:
        return None
    coefficients, *_ = np.linalg.lstsq(design, response, rcond=None)
    return BreakFit(trend=float(coefficients[1]), step=float(coefficients[2]))


def _mean_ci(values: np.ndarray) -> tuple[float, float]:
    if values.size == 0:
        return (float("nan"), float("nan"))
    ci = 1.96 * float(values.std(ddof=1)) / np.sqrt(values.size) if values.size > 1 else 0.0
    return (float(values.mean()), ci)


def speed_weighting(*, max_year: int = 2025) -> list[str]:
    """Test A -- the same pipeline on both quantities, compared station by station.

    Paired rather than pooled: the two runs see the same stations under the same coverage
    filter, so the within-station difference has far less variance than the difference of two
    independent means, and it is the quantity the prediction was written about.
    """
    lines = [
        "TEST A -- is the trend an artefact of speed weighting?",
        "-" * 70,
        f"  {CLAIM_QUANTITY} integrates reflectivity x speed x height; "
        f"{CONTROL_QUANTITY} drops the speed term.",
    ]

    runs = {
        name: station_slopes(load_conus_nights(quantity=name), max_year=max_year)
        for name in (CLAIM_QUANTITY, CONTROL_QUANTITY)
    }
    for name, slopes in runs.items():
        lines.append(f"  {name}: {slopes.height} station-season-quantile slopes")

    paired = (
        runs[CLAIM_QUANTITY]
        .join(
            runs[CONTROL_QUANTITY].select("station_id", "season", "quantile", "days_per_decade"),
            on=("station_id", "season", "quantile"),
            how="inner",
            suffix="_control",
        )
        .with_columns(
            difference=pl.col("days_per_decade_control") - pl.col("days_per_decade"),
        )
    )

    for season in ("spring", "autumn"):
        median = paired.filter(pl.col("season") == season, pl.col("quantile") == "q50_doy")
        lines.append(f"\n  {season} q50, by latitude band")
        for low, high in LATITUDE_BANDS:
            band = median.filter(pl.col("latitude").is_between(low, high, closed="left"))
            if band.is_empty():
                continue
            claim = band["days_per_decade"].to_numpy().astype(float)
            control = band["days_per_decade_control"].to_numpy().astype(float)
            difference, ci = _mean_ci(control - claim)
            lines.append(
                "    "
                + str(
                    Paired(
                        label=f"{low}-{high}N",
                        stations=band.height,
                        claim=float(claim.mean()),
                        control=float(control.mean()),
                        difference=difference,
                        ci95=ci,
                    )
                )
            )

        claim_band = median.filter(
            pl.any_horizontal(
                [
                    pl.col("latitude").is_between(low, high, closed="left")
                    for low, high in CLAIM_BANDS
                ]
            )
        )
        if not claim_band.is_empty():
            difference, ci = _mean_ci(claim_band["difference"].to_numpy().astype(float))
            correlation = float(
                np.corrcoef(
                    claim_band["days_per_decade"].to_numpy().astype(float),
                    claim_band["days_per_decade_control"].to_numpy().astype(float),
                )[0, 1]
            )
            verdict = "SURVIVES" if abs(difference) < MATERIAL_DIFFERENCE else "CHANGES"
            # Only autumn at 37-50N is a Phase 1a claim. Spring has no detectable trend, so
            # its row is a comparison of two nulls and saying "survives" of it would be
            # claiming a result that was never made.
            note = (
                "the surviving Phase 1a claim"
                if season == "autumn"
                else "no Phase 1a claim here -- both are null"
            )
            lines.append(
                f"    37-50N pooled ({note}): "
                f"diff {difference:+.2f} +/- {ci:.2f}, r={correlation:.2f}  -> {verdict}"
            )
    return lines


def _weighted_mean(frame: pl.DataFrame, value: str, weight: str) -> pl.Expr:
    """Traffic-weighted mean, so busy migration nights dominate a station-season's summary.

    An unweighted mean over a season gives a quiet October night with a handful of insects the
    same say as the largest passage of the autumn, which is the opposite of what is wanted.
    """
    del frame
    return (pl.col(value) * pl.col(weight)).sum() / pl.col(weight).sum()


def speed_drift(*, max_year: int = 2025) -> list[str]:
    """Test A's premise, and a composition screen that needs no external data.

    Test A showed the passage-date trend survives dropping the speed weighting. That says the
    result is insensitive; it does not say whether there was anything to be insensitive to. The
    direct question is whether mean flight speed drifted at all, and the lake already answers it.

    The night-minus-day gap is the second thing here. Daytime aerial biomass is
    insect-dominated -- that is what the July share established, and the day/night difference in
    ground speed says the same -- so a narrowing gap over thirty years would mean the night
    signal drifted towards the day one, which is a composition change.

    This is a screen and not a measurement, for a reason worth stating: ground speed is airspeed
    plus wind, and night and day do not share a wind climatology. The nocturnal low-level jet
    systematically raises night winds, so the gap's *level* is not a composition ratio. Only its
    stability over time is informative, and even then a trend could be a change in the day-night
    wind contrast rather than in what is flying. A flat gap is reassuring; a moving one means the
    airspeed work has to say why.
    """
    lines = [
        "TEST A' -- did flight speed drift at all, and did the night-day gap close?",
        "-" * 70,
        "  ground speed is airspeed plus wind, so this screens for composition drift rather",
        "  than measuring it. Traffic-weighted per station-season-year.",
    ]

    windows = {season.name: season for season in (SPRING, AUTUMN)}
    per_window: dict[str, pl.DataFrame] = {}
    for window_kind in ("night", "day"):
        frame = load_conus_nights(window_kind, quantity=CLAIM_QUANTITY).filter(
            pl.col("timestamp").dt.year() <= max_year,
            pl.col("coverage_fraction") >= MIN_COVERAGE,
            pl.col("speed_ms").is_not_null(),
            pl.col("magnitude") > 0,
        )
        per_window[window_kind] = frame.with_columns(
            year=pl.col("timestamp").dt.year(), doy=pl.col("timestamp").dt.ordinal_day()
        )

    for name, season in windows.items():
        summaries = {}
        for window_kind, frame in per_window.items():
            summaries[window_kind] = (
                frame.filter(pl.col("doy").is_between(season.start_doy, season.end_doy))
                .group_by("station_id", "year")
                .agg(_weighted_mean(frame, "speed_ms", "magnitude").alias("speed"))
            )

        paired = (
            summaries["night"]
            .join(summaries["day"], on=("station_id", "year"), how="inner", suffix="_day")
            .with_columns(gap=pl.col("speed") - pl.col("speed_day"))
        )

        lines.append(f"\n  {name}, n={paired.height} station-years")
        for column, label in (
            ("speed", "night ground speed"),
            ("speed_day", "day ground speed"),
            ("gap", "night minus day"),
        ):
            slopes = []
            for (_station,), group in paired.group_by(["station_id"]):
                if group.height < MIN_YEARS:
                    continue
                fit = _fit_break(
                    group["year"].to_numpy(),
                    group[column].to_numpy().astype(float),
                    FLEET_MIDPOINT_YEAR,
                )
                if fit is not None:
                    slopes.append(fit.trend * 10.0)
            if not slopes:
                continue
            mean, ci = _mean_ci(np.asarray(slopes, dtype=float))
            level = float(paired[column].to_numpy().astype(float).mean())
            verdict = "flat" if abs(mean) < abs(ci) else "MOVES"
            lines.append(
                f"    {label:<20} mean {level:5.2f} m/s   "
                f"trend {mean:+.3f} +/- {ci:.3f} m/s per decade  ({len(slopes)} stations) {verdict}"
            )

    lines.append("\n  Trends are net of a 2012 level shift, the same break Test B fits.")
    return lines


def screening(*, max_year: int = 2025) -> list[str]:
    """Test B -- is the latitude-graded 2012 step the precipitation screening?

    Three things in order: whether the screening series itself steps, whether the step is
    graded by latitude the way rainfall climatology is, and whether a station's phenology
    step is predicted by its screening step. Only the third would make the mechanism the
    explanation rather than a coincidence in time.
    """
    lines = [
        "TEST B -- is the 2012 step the precipitation screening?",
        "-" * 70,
        f"  break at {FLEET_MIDPOINT_YEAR}; rain_fraction measured inside each season's own "
        "window, so it matches the phenology it is compared against.",
    ]

    nights = load_conus_nights(quantity=CLAIM_QUANTITY).filter(
        pl.col("timestamp").dt.year() <= max_year
    )
    quantiles = passage_quantiles(
        nights,
        spec_for(EvidenceType.FLUX),
        seasons=[SPRING, AUTUMN],
        quantiles=[0.5],
        min_coverage=MIN_COVERAGE,
        min_observations=MIN_NIGHTS,
    )

    rows: list[dict[str, object]] = []
    for season in (SPRING, AUTUMN):
        # Rain inside this season's window. Comparing a spring phenology step against an
        # autumn rain step would be a mismatch dressed up as a control.
        in_window = nights.filter(
            pl.col("timestamp").dt.ordinal_day().is_between(season.start_doy, season.end_doy)
        ).with_columns(year=pl.col("timestamp").dt.year())
        per_station_year = in_window.group_by("station_id", "year").agg(
            pl.col("rain_fraction").mean().alias("rain"),
            pl.col("station_latitude").first().alias("latitude"),
        )

        # Restrict to a fixed panel. The network grew from 103 to 159 stations and southern
        # stations carry more rain, so an unrestricted mean confounds a change in screening
        # with a change in who is being screened -- the confound the Phase 1b footprint rule
        # exists for.
        span = per_station_year.group_by("station_id").agg(
            pl.col("year").min().alias("first"), pl.col("year").max().alias("last")
        )
        panel = span.filter(
            pl.col("first") <= FLEET_MIDPOINT_YEAR - PANEL_MARGIN,
            pl.col("last") >= FLEET_MIDPOINT_YEAR + PANEL_MARGIN,
        )["station_id"]
        fixed = per_station_year.filter(pl.col("station_id").is_in(panel))

        eras = (
            fixed.group_by("year")
            .agg(pl.col("rain").mean().alias("rain"))
            .with_columns(
                era=pl.when(pl.col("year") < FLEET_MIDPOINT_YEAR)
                .then(pl.lit("pre"))
                .otherwise(pl.lit("post"))
            )
            .group_by("era")
            .agg(pl.col("rain").mean().alias("mean"), pl.len().alias("years"))
        )
        lines.append(
            f"\n  {season.name} window, fixed panel of {panel.len()} of "
            f"{per_station_year['station_id'].n_unique()} stations:"
        )
        for row in eras.sort("era", descending=True).iter_rows(named=True):
            lines.append(
                f"    {row['era']:<5} {row['years']:>2} years  mean rain_fraction {row['mean']:.4f}"
            )

        seasonal = quantiles.filter(
            pl.col("season") == season.name, pl.col("q50_doy").is_not_null()
        )
        for (station,), group in seasonal.group_by(["station_id"]):
            if group.height < MIN_YEARS:
                continue
            phenology = _fit_break(
                group["year"].to_numpy(),
                group["q50_doy"].to_numpy().astype(float),
                FLEET_MIDPOINT_YEAR,
            )
            rain_group = fixed.filter(pl.col("station_id") == station).sort("year")
            if phenology is None or rain_group.height < MIN_YEARS:
                continue
            rain = _fit_break(
                rain_group["year"].to_numpy(),
                rain_group["rain"].to_numpy().astype(float),
                FLEET_MIDPOINT_YEAR,
            )
            if rain is None:
                continue
            rows.append(
                {
                    "season": season.name,
                    "station_id": station,
                    "latitude": float(rain_group["latitude"][0]),
                    "phenology_step": phenology.step,
                    "rain_step": rain.step,
                    "mean_rain": float(rain_group["rain"].to_numpy().astype(float).mean()),
                }
            )

    if not rows:
        lines.append("  no station had enough years in both series to fit both steps")
        return lines

    steps = pl.DataFrame(rows)
    for name in (SPRING.name, AUTUMN.name):
        seasonal = steps.filter(pl.col("season") == name)
        if seasonal.height < MIN_STATIONS:
            continue
        lines.append(f"\n  {name}: per-station steps, n={seasonal.height}")
        phenology_step = seasonal["phenology_step"].to_numpy().astype(float)
        mean, ci = _mean_ci(phenology_step)
        lines.append(f"    mean phenology step  {mean:+.2f} +/- {ci:.2f} d")
        rain_mean, rain_ci = _mean_ci(seasonal["rain_step"].to_numpy().astype(float))
        lines.append(f"    mean screening step  {rain_mean:+.4f} +/- {rain_ci:.4f} rain fraction")
        for against in ("rain_step", "mean_rain", "latitude"):
            correlation = float(
                np.corrcoef(phenology_step, seasonal[against].to_numpy().astype(float))[0, 1]
            )
            lines.append(f"    corr(phenology step, {against:<11}) = {correlation:+.2f}")

    lines.append(
        "\n  The pre-registered reading: a positive corr(phenology step, rain_step or mean_rain)"
    )
    lines.append(
        "  that also flattens the latitude correlation would make screening the mechanism. A null"
    )
    lines.append("  rules the mechanism out and leaves the step unexplained -- see the note.")
    return lines


def _airspeed_nights(max_year: int) -> pl.DataFrame:
    """Radar night velocity joined to the NARR night wind, with airspeed.

    The join is a plain equality on station and date because `drivers/narr.py` writes each wind
    row under the radar night it describes rather than under the UTC day its hours came from.
    That convention was established by measurement rather than assumed -- see
    `narr.UTC_DAY_TO_RADAR_NIGHT`.
    """
    nights = load_conus_nights(quantity=CLAIM_QUANTITY).filter(
        pl.col("timestamp").dt.year() <= max_year,
        pl.col("coverage_fraction") >= MIN_COVERAGE,
        pl.col("speed_ms").is_not_null(),
        pl.col("direction_deg").is_not_null(),
        pl.col("magnitude") > 0,
    )
    radar = nights.select(
        station_id=pl.col("station_id"),
        date=pl.col("timestamp").dt.date(),
        year=pl.col("timestamp").dt.year(),
        doy=pl.col("timestamp").dt.ordinal_day(),
        magnitude=pl.col("magnitude"),
        ground_speed=pl.col("speed_ms"),
        # Compass bearing, degrees clockwise from north, so east is sin and north is cos.
        u_radar=pl.col("speed_ms") * (pl.col("direction_deg").radians().sin()),
        v_radar=pl.col("speed_ms") * (pl.col("direction_deg").radians().cos()),
    )

    winds = (
        scan_dataset(DRIVER_SAMPLES.name, source_id=narr.SOURCE_ID)
        .filter(pl.col("variable").str.starts_with("wind_"))
        .select(
            station_id=pl.col("site_id"),
            date=pl.col("period_start").dt.date(),
            variable=pl.col("variable"),
            value=pl.col("value"),
        )
        .collect()
        .pivot(on="variable", index=("station_id", "date"), values="value")
    )
    u_column = f"wind_u_{narr.LEVEL_HPA}hPa"
    v_column = f"wind_v_{narr.LEVEL_HPA}hPa"
    if u_column not in winds.columns or v_column not in winds.columns:
        return pl.DataFrame()

    joined = radar.join(winds, on=("station_id", "date"), how="inner")
    return joined.with_columns(
        airspeed=(
            (pl.col("u_radar") - pl.col(u_column)) ** 2
            + (pl.col("v_radar") - pl.col(v_column)) ** 2
        ).sqrt(),
        wind_speed=(pl.col(u_column) ** 2 + pl.col(v_column) ** 2).sqrt(),
    )


class SpeedTrend(NamedTuple):
    """Per-decade drift in one speed measure, across the stations long enough to fit it."""

    mean: float
    ci95: float
    level: float
    """Reflectivity-weighted mean over every station-year, in m/s. The level, not the drift."""

    stations: int

    @property
    def flat(self) -> bool:
        """Indistinguishable from zero. The composition claim is only true while this holds."""
        return abs(self.mean) < abs(self.ci95)


def _per_station_year(nights: pl.DataFrame, season: Season) -> pl.DataFrame:
    """One row per station-year, each speed weighted by the traffic that produced it."""
    seasonal = nights.filter(pl.col("doy").is_between(season.start_doy, season.end_doy))
    if seasonal.is_empty():
        return seasonal
    return seasonal.group_by("station_id", "year").agg(
        _weighted_mean(seasonal, "airspeed", "magnitude").alias("airspeed"),
        _weighted_mean(seasonal, "wind_speed", "magnitude").alias("wind_speed"),
        _weighted_mean(seasonal, "ground_speed", "magnitude").alias("ground_speed"),
        pl.len().alias("nights"),
    )


def _speed_trend(per_station_year: pl.DataFrame, column: str) -> SpeedTrend | None:
    """Mean per-decade slope across stations, each fitted with a break at the fleet midpoint."""
    slopes = []
    for (_station,), group in per_station_year.group_by(["station_id"]):
        if group.height < MIN_YEARS:
            continue
        fit = _fit_break(
            group["year"].to_numpy(),
            group[column].to_numpy().astype(float),
            FLEET_MIDPOINT_YEAR,
        )
        if fit is not None:
            slopes.append(fit.trend * 10.0)
    if not slopes:
        return None
    mean, ci = _mean_ci(np.asarray(slopes, dtype=float))
    level = float(per_station_year[column].to_numpy().astype(float).mean())
    return SpeedTrend(mean=mean, ci95=ci, level=level, stations=len(slopes))


def airspeed_trend(season: Season, *, max_year: int = 2025) -> SpeedTrend | None:
    """The airspeed drift for one season, as a number rather than as a line of a report.

    `reports/findings.py` publishes this, and publishes it only while it is flat -- the
    composition claim asserts the mixture did not change, so the claim and the fit have to be
    the same fit. Returning `None` when the wind is not in the lake is deliberate: a ledger
    entry is better absent than computed from a season that never joined.
    """
    nights = _airspeed_nights(max_year)
    if nights.is_empty():
        return None
    per_station_year = _per_station_year(nights, season)
    if per_station_year.is_empty():
        return None
    return _speed_trend(per_station_year, "airspeed")


def composition(*, max_year: int = 2025) -> list[str]:
    """Test C -- did the mixture drift, once the wind is taken out of the ground speed?

    Predictions were fixed in phase1c-homogeneity.md before the wind data existed, off the back
    of Test A': spring ground speed rose 0.572 +/- 0.118 m/s per decade and autumn barely moved,
    so spring airspeed should be flat with the wind carrying the rise, and autumn airspeed flat
    too. A rising autumn airspeed is the outcome that forces Phase 1a to be re-scoped.
    """
    lines = [
        "TEST C -- composition, from airspeed",
        "-" * 70,
        f"  airspeed = |radar velocity - NARR {narr.LEVEL_HPA} hPa night wind|, per station-night.",
        "  birds cruise 8-15 m/s, insects 0-5 (Shi et al. 2025, Ornithological Applications).",
    ]

    nights = _airspeed_nights(max_year)
    if nights.is_empty():
        lines.append("  no NARR winds in the lake yet -- run `make ingest-narr` first.")
        return lines

    years = nights["year"].to_numpy()
    lines.append(
        f"  {nights.height:,} station-nights matched to a wind, "
        f"{nights['station_id'].n_unique()} stations, "
        f"{int(years.min())}-{int(years.max())}"
    )

    for season in (SPRING, AUTUMN):
        seasonal = nights.filter(pl.col("doy").is_between(season.start_doy, season.end_doy))
        if seasonal.is_empty():
            continue
        per_station_year = _per_station_year(nights, season)
        lines.append(f"\n  {season.name}, {per_station_year.height} station-years")

        for column, label in (
            ("ground_speed", "ground speed"),
            ("wind_speed", "NARR wind speed"),
            ("airspeed", "AIRSPEED"),
        ):
            trend = _speed_trend(per_station_year, column)
            if trend is None:
                continue
            lines.append(
                f"    {label:<18} mean {trend.level:5.2f} m/s   "
                f"trend {trend.mean:+.3f} +/- {trend.ci95:.3f} m/s per decade  "
                f"({trend.stations} stations) {'flat' if trend.flat else 'MOVES'}"
            )

        # The level question, separate from the drift one: how much of the traffic is moving
        # slowly enough to be something other than a migrating bird?
        slow = seasonal.filter(pl.col("airspeed") < INSECT_AIRSPEED_MAX)["magnitude"].to_numpy()
        total = seasonal["magnitude"].to_numpy()
        share = float(slow.sum() / total.sum()) if total.sum() else 0.0
        lines.append(
            f"    traffic on nights with mean airspeed < {INSECT_AIRSPEED_MAX} m/s: {share:.1%}"
        )

    lines.append(
        "\n  The reanalysis control: a trend appearing in both airspeed and NARR wind speed is"
    )
    lines.append("  NARR's observing system changing, not the animals. Read the two rows together.")
    lines += _without_slow_nights(nights, max_year=max_year)
    return lines


def _without_slow_nights(nights: pl.DataFrame, *, max_year: int) -> list[str]:
    """The level half of Test C: drop the nights that were not bird-dominated, and refit.

    Separate question from the drift check above. Even with a flat airspeed trend, a passage-date
    quantile is a cumulative sum over every night in a season, so nights whose traffic was mostly
    something slower than a bird still contribute mass to it. If the trend is the same without
    them, they were not carrying it.
    """
    slow = nights.filter(pl.col("airspeed") < INSECT_AIRSPEED_MAX).select("station_id", "date")
    if slow.is_empty():
        return ["\n  No nights below the airspeed floor, so nothing to exclude."]

    full = load_conus_nights(quantity=CLAIM_QUANTITY)
    kept = full.with_columns(date=pl.col("timestamp").dt.date()).join(
        slow, on=("station_id", "date"), how="anti"
    )
    lines = [
        "",
        f"  Excluding the {slow.height:,} station-nights whose mean airspeed was under "
        f"{INSECT_AIRSPEED_MAX} m/s:",
    ]

    baseline = station_slopes(full, max_year=max_year)
    restricted = station_slopes(kept.drop("date"), max_year=max_year)
    for season in ("spring", "autumn"):
        pair = []
        for label, slopes in (("all nights", baseline), ("bird nights", restricted)):
            band = slopes.filter(
                pl.col("season") == season,
                pl.col("quantile") == "q50_doy",
                pl.any_horizontal(
                    [
                        pl.col("latitude").is_between(low, high, closed="left")
                        for low, high in CLAIM_BANDS
                    ]
                ),
            )
            if band.is_empty():
                continue
            mean, ci = _mean_ci(band["days_per_decade"].to_numpy().astype(float))
            pair.append((label, band.height, mean, ci))
        # Both the all-nights and bird-nights fits, or the comparison has nothing to say.
        if len(pair) == BOTH_FITS:
            (_, n_all, all_mean, all_ci), (_, n_bird, bird_mean, bird_ci) = pair
            moved = abs(bird_mean - all_mean)
            verdict = "unchanged" if moved < MATERIAL_DIFFERENCE else "CHANGES"
            lines.append(
                f"    {season} q50 37-50N: all nights {all_mean:+.2f} +/- {all_ci:.2f} "
                f"(n={n_all})  ->  bird nights {bird_mean:+.2f} +/- {bird_ci:.2f} "
                f"(n={n_bird})  {verdict}"
            )
    return lines


SEASON_MONTHS: Final[dict[str, tuple[int, ...]]] = {
    "spring": (3, 4, 5, 6),
    "autumn": (8, 9, 10, 11),
}
"""Which calendar months each phenology window covers, for joining to a monthly driver.
Spring is doy 60-181 and autumn 213-334, so these are those windows rounded to whole months."""


def weather_or_instrument(*, max_year: int = 2025) -> list[str]:
    """Test D -- is the 2012 screening step the drought, or the radar upgrade?

    Predictions fixed in phase1c-homogeneity.md before the precipitation was fetched. If weather,
    ERA5 steps down too and the per-station steps correlate; if the instrument, ERA5 is flat and
    the correlation is null. ERA5 is the right arbiter because it shares no hardware, no
    processing and no NEXRAD with the radar product.
    """
    lines = [
        "TEST D -- is the 2012 screening step weather or the instrument?",
        "-" * 70,
        "  ERA5 monthly total precipitation at the same stations, same windows, same break.",
    ]

    rain = scan_dataset(DRIVER_SAMPLES.name, source_id=era5.SOURCE_ID)
    try:
        precipitation = (
            rain.filter(pl.col("variable") == era5.FIELDS["precipitation"].canonical)
            .select(
                station_id=pl.col("site_id"),
                year=pl.col("period_start").dt.year(),
                month=pl.col("period_start").dt.month(),
                mm=pl.col("value"),
            )
            .collect()
        )
    except FileNotFoundError, OSError:
        lines.append("  no ERA5 precipitation in the lake yet -- run `make ingest-era5` first.")
        return lines

    nights = load_conus_nights(quantity=CLAIM_QUANTITY).filter(
        pl.col("timestamp").dt.year() <= max_year
    )

    for season, months in SEASON_MONTHS.items():
        window = SPRING if season == "spring" else AUTUMN
        screening_series = (
            nights.filter(
                pl.col("timestamp").dt.ordinal_day().is_between(window.start_doy, window.end_doy)
            )
            .with_columns(year=pl.col("timestamp").dt.year())
            .group_by("station_id", "year")
            .agg(pl.col("rain_fraction").mean().alias("screened"))
        )
        weather = (
            precipitation.filter(pl.col("month").is_in(months))
            .group_by("station_id", "year")
            .agg(pl.col("mm").mean().alias("rainfall"))
        )
        paired = screening_series.join(weather, on=("station_id", "year"), how="inner")

        rows = []
        for (station,), group in paired.group_by(["station_id"]):
            if group.height < MIN_YEARS:
                continue
            ordered = group.sort("year")
            years = ordered["year"].to_numpy()
            screened = _fit_break(
                years, ordered["screened"].to_numpy().astype(float), FLEET_MIDPOINT_YEAR
            )
            rainfall = _fit_break(
                years, ordered["rainfall"].to_numpy().astype(float), FLEET_MIDPOINT_YEAR
            )
            if screened is None or rainfall is None:
                continue
            rows.append(
                {"station_id": station, "screened": screened.step, "rainfall": rainfall.step}
            )

        # The raw era means alongside the fitted step, because they answer subtly different
        # questions and here they diverge: a break coefficient is net of a linear trend, so it
        # can be positive while the plain pre/post difference is flat. The drought question is
        # about the plain difference, so both get printed rather than only the model's view.
        eras = (
            paired.with_columns(
                era=pl.when(pl.col("year") < FLEET_MIDPOINT_YEAR)
                .then(pl.lit("pre"))
                .otherwise(pl.lit("post"))
            )
            .group_by("era")
            .agg(pl.col("rainfall").mean().alias("mm"))
        )
        levels = dict(zip(eras["era"], eras["mm"], strict=True))

        if len(rows) < MIN_STATIONS:
            continue
        steps = pl.DataFrame(rows)
        screened_step = steps["screened"].to_numpy().astype(float)
        rainfall_step = steps["rainfall"].to_numpy().astype(float)
        screened_mean, screened_ci = _mean_ci(screened_step)
        rainfall_mean, rainfall_ci = _mean_ci(rainfall_step)
        correlation = float(np.corrcoef(screened_step, rainfall_step)[0, 1])

        lines.append(f"\n  {season}, n={steps.height} stations")
        lines.append(
            f"    screening step        {screened_mean:+.4f} +/- {screened_ci:.4f} rain fraction"
        )
        lines.append(
            f"    ERA5 rainfall step    {rainfall_mean:+.4f} +/- {rainfall_ci:.4f} mm/day"
            "  (net of trend)"
        )
        lines.append(
            f"    ERA5 raw era means    pre {levels.get('pre', float('nan')):.3f} -> "
            f"post {levels.get('post', float('nan')):.3f} mm/day  "
            f"({levels.get('post', 0.0) - levels.get('pre', 0.0):+.3f})"
        )
        lines.append(f"    corr(screening step, rainfall step) = {correlation:+.2f}")
        dried = rainfall_mean < 0 and abs(rainfall_mean) > rainfall_ci
        tracks = correlation > WEATHER_SIGNAL
        lines.append(
            f"    -> weather {'explains' if dried else 'does NOT explain'} the level shift; "
            f"per-station variation {'does' if tracks else 'does not'} track rainfall"
        )

    lines.append(
        "\n  Weather predicts a negative ERA5 step and a positive correlation; the instrument"
    )
    lines.append("  predicts neither. Mixed is a real answer and is reported as one.")
    return lines


def render(max_year: int = 2025) -> str:
    out = [
        "Phase 1c -- homogeneity of the 1995-2025 radar record",
        "=" * 70,
        "Pre-registered in docs/methods/phase1c-homogeneity.md before any of this ran.",
        "",
    ]
    out += speed_weighting(max_year=max_year)
    out += ["", ""]
    out += speed_drift(max_year=max_year)
    out += ["", ""]
    out += screening(max_year=max_year)
    out += ["", ""]
    out += composition(max_year=max_year)
    out += ["", ""]
    out += weather_or_instrument(max_year=max_year)
    return "\n".join(out)
