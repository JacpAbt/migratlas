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

from migratlas.evidence import EvidenceType, spec_for
from migratlas.metrics.phenology import passage_quantiles
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
            lines.append(
                f"    37-50N pooled (the surviving Phase 1a claim): "
                f"diff {difference:+.2f} +/- {ci:.2f}, r={correlation:.2f}  -> {verdict}"
            )
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
        f"  break at {FLEET_MIDPOINT_YEAR}; rain_fraction measured in the autumn window only, "
        "so it matches the phenology it is being compared to.",
    ]

    nights = load_conus_nights(quantity=CLAIM_QUANTITY).filter(
        pl.col("timestamp").dt.year() <= max_year
    )

    # Restrict to a fixed panel. The network grew from 103 to 159 stations, and southern
    # stations carry more rain, so an unrestricted mean confounds a change in screening with
    # a change in who is being screened -- the same confound the Phase 1b footprint rule
    # exists for.
    autumn = nights.filter(
        pl.col("timestamp").dt.ordinal_day().is_between(AUTUMN.start_doy, AUTUMN.end_doy)
    ).with_columns(year=pl.col("timestamp").dt.year())
    per_station_year = autumn.group_by("station_id", "year").agg(
        pl.col("rain_fraction").mean().alias("rain"),
        pl.col("station_latitude").first().alias("latitude"),
    )
    span = per_station_year.group_by("station_id").agg(
        pl.col("year").min().alias("first"), pl.col("year").max().alias("last")
    )
    panel = span.filter(
        pl.col("first") <= FLEET_MIDPOINT_YEAR - 5, pl.col("last") >= FLEET_MIDPOINT_YEAR + 5
    )["station_id"]
    fixed = per_station_year.filter(pl.col("station_id").is_in(panel))
    lines.append(
        f"  fixed panel: {panel.len()} of {per_station_year['station_id'].n_unique()} stations "
        f"span {FLEET_MIDPOINT_YEAR - 5}-{FLEET_MIDPOINT_YEAR + 5}"
    )

    yearly = (
        fixed.group_by("year")
        .agg(pl.col("rain").mean())
        .sort("year")
        .with_columns(
            era=pl.when(pl.col("year") < FLEET_MIDPOINT_YEAR)
            .then(pl.lit("pre"))
            .otherwise(pl.lit("post"))
        )
    )
    eras = yearly.group_by("era").agg(pl.col("rain").mean().alias("mean"), pl.len().alias("years"))
    lines.append("  screening series on the fixed panel:")
    for row in eras.sort("era", descending=True).iter_rows(named=True):
        lines.append(
            f"    {row['era']:<5} {row['years']:>2} years  mean rain_fraction {row['mean']:.4f}"
        )

    # Per station: the screening step, and the phenology step, from the same design.
    quantiles = passage_quantiles(
        nights,
        spec_for(EvidenceType.FLUX),
        seasons=[SPRING, AUTUMN],
        quantiles=[0.5],
        min_coverage=MIN_COVERAGE,
        min_observations=MIN_NIGHTS,
    )

    rows: list[dict[str, object]] = []
    for season in ("spring", "autumn"):
        seasonal = quantiles.filter(pl.col("season") == season, pl.col("q50_doy").is_not_null())
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
                    "season": season,
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
    for season in ("spring", "autumn"):
        seasonal = steps.filter(pl.col("season") == season)
        if seasonal.height < MIN_STATIONS:
            continue
        lines.append(f"\n  {season}: per-station steps, n={seasonal.height}")
        phenology_step = seasonal["phenology_step"].to_numpy().astype(float)
        mean, ci = _mean_ci(phenology_step)
        lines.append(f"    mean phenology step  {mean:+.2f} +/- {ci:.2f} d")
        rain_mean, rain_ci = _mean_ci(seasonal["rain_step"].to_numpy().astype(float))
        lines.append(f"    mean screening step  {rain_mean:+.4f} +/- {rain_ci:.4f} rain fraction")
        for name in ("rain_step", "mean_rain", "latitude"):
            correlation = float(
                np.corrcoef(phenology_step, seasonal[name].to_numpy().astype(float))[0, 1]
            )
            lines.append(f"    corr(phenology step, {name:<11}) = {correlation:+.2f}")

    lines.append(
        "\n  The pre-registered reading: a positive corr(phenology step, rain_step or mean_rain)"
    )
    lines.append(
        "  that also flattens the latitude correlation would make screening the mechanism. A null"
    )
    lines.append("  rules the mechanism out and leaves the step unexplained -- see the note.")
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
    out += screening(max_year=max_year)
    out += [
        "",
        "=" * 70,
        "Test C (composition, from airspeed) needs a wind field and waits on the driver panel.",
    ]
    return "\n".join(out)
