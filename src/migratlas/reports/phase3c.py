"""Phase 3c: the four registered edges, run once, no novelty claimed.

Everything discretionary is in `docs/methods/phase3c-coupling.md`. The machinery here is one
function applied four times: detrend both series, condition on the four modes, read one
coefficient, test it against every circular rotation of its own driver, and publish the
bootstrap interval whether or not anything was detected.
"""

import logging
from dataclasses import dataclass
from typing import Final

import numpy as np
import polars as pl

from migratlas.evidence import EvidenceType, spec_for
from migratlas.lake.reader import scan, scan_dataset
from migratlas.metrics.phenology import passage_quantiles

log = logging.getLogger(__name__)

SEED: Final = 20260819
"""The registration date, like Phase 3a's before it."""

BOOTSTRAPS: Final = 1000

# The radar band: the claim band's latitudes over the stations' own longitude extent.
BAND_LAT: Final = (37.0, 50.0)
BAND_LON: Final = (-125.0, -66.0)

# The CPR product's own footprint, used to pick the surveys and the water that share it.
CPR_LAT: Final = (35.0, 65.0)
CPR_LON: Final = (-76.0, -22.0)

MODES: Final = ("oni", "nao", "ao", "pdo")

# Plankton abundance is normalised to each year's own maximum before the bloom metric runs, so
# the amplitude floor is relative: a year needs a 10% seasonal swing to carry a date. The same
# floor the NDVI metric uses, on the same 0-1 scale, by construction rather than coincidence.
BLOOM_FLOOR: Final = 0.1
MONTHS_PER_YEAR: Final = 12
MIN_EDGE_YEARS: Final = 15


@dataclass(frozen=True, slots=True)
class EdgeResult:
    """One registered edge, however it landed."""

    name: str
    years: int
    coefficient: float
    ci_low: float
    ci_high: float
    null_bar: float
    """The 95th percentile of |coefficient| under every circular rotation of the driver."""
    detected: bool


def edge(
    name: str,
    driver: dict[int, float],
    response: dict[int, float],
    modes: dict[str, dict[int, float]],
    *,
    seed: int = SEED,
) -> EdgeResult | None:
    """The registered machinery: detrend, condition, one coefficient, rotation null, bootstrap."""
    years = sorted(set(driver) & set(response))
    for mode in modes.values():
        years = [y for y in years if y in mode]
    if len(years) < MIN_EDGE_YEARS:
        return None
    axis = np.array(years, dtype=float)

    def detrend(series: dict[int, float]) -> np.ndarray:
        values = np.array([series[y] for y in years])
        slope, intercept = np.polyfit(axis, values, 1)
        residual: np.ndarray = values - (slope * axis + intercept)
        return residual

    x = detrend(driver)
    y = detrend(response)
    # The unconditioned H1 variant passes an empty dict; everything else passes all four modes.
    conditioners = [detrend(modes[m]) for m in modes]

    def coefficient(shifted: np.ndarray) -> float:
        design = np.column_stack([np.ones(len(years)), shifted, *conditioners])
        solution, *_ = np.linalg.lstsq(design, y, rcond=None)
        return float(solution[1])

    observed = coefficient(x)
    rotations = np.array([abs(coefficient(np.roll(x, shift))) for shift in range(1, len(years))])
    null_bar = float(np.percentile(rotations, 95))

    rng = np.random.default_rng(seed)
    draws = np.empty(BOOTSTRAPS)
    for i in range(BOOTSTRAPS):
        pick = rng.integers(0, len(years), len(years))
        design = np.column_stack([np.ones(len(pick)), x[pick], *[c[pick] for c in conditioners]])
        solution, *_ = np.linalg.lstsq(design, y[pick], rcond=None)
        draws[i] = solution[1]

    return EdgeResult(
        name=name,
        years=len(years),
        coefficient=observed,
        ci_low=float(np.percentile(draws, 2.5)),
        ci_high=float(np.percentile(draws, 97.5)),
        null_bar=null_bar,
        detected=abs(observed) > null_bar,
    )


def _mode_series() -> dict[str, dict[int, float]]:
    """Calendar-year means of each mode, the conditioning set of every edge."""
    frame = scan_dataset("driver_samples", source_id="noaa_climate_indices").collect()
    frame = frame.with_columns(year=pl.col("period_start").dt.year())
    out: dict[str, dict[int, float]] = {}
    for mode in MODES:
        rows = frame.filter(pl.col("variable") == mode).group_by("year").agg(pl.col("value").mean())
        out[mode] = {int(r["year"]): float(r["value"]) for r in rows.to_dicts()}
    return out


def winter_nao() -> dict[int, float]:
    """DJF mean ending in each year: December of the year before, January and February of it."""
    frame = scan_dataset("driver_samples", source_id="noaa_climate_indices").collect()
    nao = frame.filter(pl.col("variable") == "nao").with_columns(
        year=pl.col("period_start").dt.year(),
        month=pl.col("period_start").dt.month(),
    )
    winter = nao.with_columns(
        season_year=pl.when(pl.col("month") == MONTHS_PER_YEAR)
        .then(pl.col("year") + 1)
        .otherwise(pl.col("year"))
    ).filter(pl.col("month").is_in([12, 1, 2]))
    rows = winter.group_by("season_year").agg(pl.col("value").mean())
    return {int(r["season_year"]): float(r["value"]) for r in rows.to_dicts()}


def greenup_band() -> dict[int, float]:
    """The radar band's mean green-up day per year, from the lake's own series."""
    frame = scan_dataset("driver_samples", source_id="pku_gimms_ndvi").collect()
    band = frame.filter(
        pl.col("latitude").is_between(*BAND_LAT),
        pl.col("longitude").is_between(*BAND_LON),
    ).with_columns(year=pl.col("period_start").dt.year())
    rows = band.group_by("year").agg(pl.col("value").mean())
    return {int(r["year"]): float(r["value"]) for r in rows.to_dicts()}


def spring_passage() -> dict[int, float]:
    """The band's median spring passage day per year, through Phase 1's own machinery."""
    from migratlas.reports.phase1 import (  # noqa: PLC0415 -- heavy, report sibling
        AUTUMN,
        MIN_COVERAGE,
        MIN_NIGHTS,
        SPRING,
        load_conus_nights,
    )

    quantiles = passage_quantiles(
        load_conus_nights(),
        spec_for(EvidenceType.FLUX),
        seasons=[SPRING, AUTUMN],
        quantiles=(0.5,),
        min_coverage=MIN_COVERAGE,
        min_observations=MIN_NIGHTS,
    ).drop_nulls("q50_doy")
    spring = quantiles.filter(pl.col("season") == "spring")
    rows = spring.group_by("year").agg(pl.col("q50_doy").median())
    return {int(r["year"]): float(r["q50_doy"]) for r in rows.to_dicts()}


def plankton_bloom() -> dict[int, float]:
    """The bloom day per year: the green-up metric on the year's normalised monthly abundance."""
    from migratlas.drivers.greenup import greenup_day  # noqa: PLC0415 -- one metric, two kingdoms

    samples = (
        scan(EvidenceType.SURVEY_INDEX, source_id="cpr_bcodmo")
        .select("period_start", "count")
        .collect()
        .with_columns(
            year=pl.col("period_start").dt.year(),
            month=pl.col("period_start").dt.month(),
        )
    )
    monthly = samples.group_by("year", "month").agg(pl.col("count").mean())
    out: dict[int, float] = {}
    for (year,), months in monthly.group_by(["year"], maintain_order=True):
        if months.height < MONTHS_PER_YEAR:
            continue
        values = months.sort("month")["count"].to_numpy().astype(float)
        peak = values.max()
        if peak <= 0:
            continue
        day = greenup_day(values / peak, bins=MONTHS_PER_YEAR, min_amplitude=BLOOM_FLOOR)
        if day is not None:
            out[int(year)] = day
    return out


def spring_sst_cpr() -> dict[int, float]:
    """March-May in-situ surface temperature over the CPR footprint, from the haul record."""
    frame = scan_dataset("driver_samples", source_id="fishglob").collect()
    spring = frame.filter(
        pl.col("variable") == "sea_surface_temperature",
        pl.col("latitude").is_between(*CPR_LAT),
        pl.col("longitude").is_between(*CPR_LON),
        pl.col("period_start").dt.month().is_in([3, 4, 5]),
    ).with_columns(year=pl.col("period_start").dt.year())
    rows = spring.group_by("year").agg(pl.col("value").mean())
    return {int(r["year"]): float(r["value"]) for r in rows.to_dicts()}


def fish_anomalies() -> dict[str, dict[int, float]]:
    """Cross-species latitude anomalies per CPR-footprint survey, full-period references.

    Full-period rather than train-era references, deliberately: an edge regression holds no
    test era to protect, and the detrending inside `edge` removes what a reference could leak.
    """
    from migratlas.metrics import range as range_metrics  # noqa: PLC0415 -- report sibling
    from migratlas.reports import phase1b  # noqa: PLC0415 -- report sibling
    from migratlas.reports.phase3a import _species_anomalies  # noqa: PLC0415 -- shared rule

    cells = range_metrics.to_cells(phase1b.survey_unit(phase1b.load()))
    out: dict[str, dict[int, float]] = {}
    for (unit,), survey in cells.group_by(["survey_unit"], maintain_order=True):
        centre_lat = float(np.median(survey["site_latitude"].to_numpy()))
        centre_lon = float(np.median(survey["site_longitude"].to_numpy()))
        inside_lat = CPR_LAT[0] <= centre_lat <= CPR_LAT[1]
        inside_lon = CPR_LON[0] <= centre_lon <= CPR_LON[1]
        if not (inside_lat and inside_lon):
            continue
        restricted, footprint = range_metrics.consistent_footprint(survey)
        if footprint.cells < range_metrics.MIN_CELLS:
            continue
        series = range_metrics.centroids(restricted)
        if series.is_empty():
            continue
        years = set(series["year"].to_list())
        anomalies = _species_anomalies(series, train_years=years)
        out[str(unit)] = {int(r["year"]): float(r["anomaly"]) for r in anomalies.to_dicts()}
    return out


def render() -> str:
    """All four edges, run exactly once, every prediction graded."""
    modes = _mode_series()
    lines: list[str] = []

    c1 = edge("C1 winter NAO -> green-up day", winter_nao(), greenup_band(), modes)
    bloom = plankton_bloom()
    c2 = edge("C2 spring SST -> plankton bloom day", spring_sst_cpr(), bloom, modes)
    for calibration in (c1, c2):
        if calibration is None:
            lines.append("A calibration edge had too few overlapping years to run at all.")
            continue
        lines.append(_line(calibration))

    calibrated = bool(c1 and c1.detected and c2 and c2.detected)
    lines.append(
        f"Prediction 1 ({'GRADED TRUE' if calibrated else 'GRADED FALSE'}): "
        "both calibration edges detect."
    )
    if not calibrated:
        lines.append(
            "STOP CONDITION: the instrument cannot see a known signal at these lengths, so "
            "the hypothesis edges below are printed but not interpreted, per §5."
        )

    greenup = greenup_band()
    passage = spring_passage()
    h1 = edge("H1 green-up day -> spring passage day", greenup, passage, modes)
    h1_bare = edge("H1 (unconditioned)", greenup, passage, {})
    if h1 and h1_bare:
        lines.append(_line(h1))
        lines.append(_line(h1_bare))
        shrunk = h1.coefficient > 0 and abs(h1.coefficient) < abs(h1_bare.coefficient)
        lines.append(
            f"Prediction 2 ({'GRADED TRUE' if shrunk else 'GRADED FALSE'}): the conditioned "
            "coefficient is positive and smaller than the unconditioned one."
        )
    else:
        lines.append("Prediction 2 (UNGRADEABLE): H1 had too few overlapping years.")

    h2_detected = False
    h2_ran = 0
    for survey, anomaly in sorted(fish_anomalies().items()):
        for lag in (0, 1):
            shifted = {year + lag: value for year, value in bloom.items()}
            result = edge(f"H2 bloom -> {survey} (lag {lag})", shifted, anomaly, modes)
            if result is None:
                continue
            h2_ran += 1
            h2_detected = h2_detected or result.detected
            lines.append(_line(result))
    if h2_ran:
        lines.append(
            f"Prediction 3 ({'GRADED FALSE' if h2_detected else 'GRADED TRUE'}): the "
            "plankton-to-fish edge is registered as an expected null; a detection grades it "
            "false and is the good kind of wrong."
        )
    else:
        lines.append("Prediction 3 (UNGRADEABLE): no survey overlapped the bloom series.")

    lines.append(
        "Prediction 4 (DEFERRED TO PUBLICATION): every interval above publishes on the site "
        "beside its caveat when the coupling page ships with #52."
    )
    return "\n".join(lines)


def _line(result: EdgeResult) -> str:
    verdict = "DETECTED" if result.detected else "not detected"
    return (
        f"{result.name}: coefficient {result.coefficient:+.3f} "
        f"[{result.ci_low:+.3f}, {result.ci_high:+.3f}], rotation bar {result.null_bar:.3f}, "
        f"{result.years} years -- {verdict}."
    )
