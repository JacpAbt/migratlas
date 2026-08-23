"""Phase 1k — what four idle monitoring schemes say alone, and what they say together.

Pre-registered in ``docs/methods/phase1k-idle-networks.md`` before any centroid or flight-date trend
was computed. Two legs, each opening on a calibration arm that must reproduce a number this project
already publishes, and a synthesis that fits nothing.

**The calibration arms call the published reports rather than reimplementing them.** Arm A is
``phase1b.analyse`` and arm D is ``phase1.station_slopes``, which is the only way "reproduces the
published median" can mean anything: a second copy of the pipeline would be a second thing that can
drift, and agreeing with a copy of itself proves nothing.

**Nothing here groups by realm.** ``Realm`` is the physical medium of the *observation* — it
routes drivers, so a route count is terrestrial and a radar aerial while both measure the same
animals. §1 of the note records why that axis cannot answer the question and what is used instead.
"""

import logging
from dataclasses import dataclass
from typing import Final

import numpy as np
import polars as pl

from migratlas.evidence.types import EvidenceType
from migratlas.lake.reader import scan
from migratlas.metrics import range as range_metrics
from migratlas.reports import phase1b

log = logging.getLogger(__name__)

# The three designed count networks the holdings audit found idle, and the phenology scheme Phase 1j
# ingested and never fitted. Named here so the ladder's arms are a property of this module.
COUNT_NETWORKS: Final[tuple[str, ...]] = ("bbs", "sbs_point_counts", "sbs_fixed_routes")
FLIGHT_NETWORK: Final = "ukbms_phenology"

# Leg 1's floor, on the unit rather than a proxy for it -- Phase 1j's recorded correction.
MIN_YEARS: Final = 20
# The registered sensitivity, reported always and never promoted.
MIN_YEARS_LOW: Final = 15
# Below this a network is published as a coverage statement and no trend is claimed from it.
MIN_UNITS: Final = 30

# Leg 2's floor, inherited from Phase 1j rather than re-derived: 10,941 site-species-generation
# units clear fifteen years inside its registered window.
FLIGHT_MIN_YEARS: Final = 15

# Calibration targets, quoted from the published findings they must reproduce.
MARINE_NULL_MEDIAN: Final = -0.011
AUTUMN_ADVANCE_SLOPE: Final = -0.56

# Three significant figures on the marine median and two on the aerial slope, which is what the
# registration promised and what the published findings state.
MARINE_TOLERANCE: Final = 5e-4
AERIAL_TOLERANCE: Final = 5e-3

SEED: Final = 1
PERMUTATIONS: Final = 1_000


@dataclass(frozen=True, slots=True)
class NetworkResult:
    """One network's distribution answer, and what it had to discard to give it."""

    source_id: str
    realm: str
    units: int
    """Qualifying species-network units — the count the stop condition reads."""
    median: float
    interval: tuple[float, float]
    """Bootstrap interval on the median, which is what the predictions turn on."""
    iqr: tuple[float, float]
    """The interquartile range, because a median alone hides the sign disagreement."""
    significant: int
    bar: int
    cells_kept: int
    cells_dropped: int


@dataclass(frozen=True, slots=True)
class TimingResult:
    """The flight-date leg: Phase 1j's leg, on the unit Phase 1j declared."""

    units: int
    median: float
    interval: tuple[float, float]
    iqr: tuple[float, float]
    significant: int
    bar: int


def load_counts(source_id: str) -> pl.DataFrame:
    """Count rows for one network, through the reader with an explicit source.

    The same columns ``phase1b`` selects, because leg 1's estimand is ``marine-null``'s and the
    metric functions are realm-general -- which `DATASETS.md` already calls the structural proof
    that the metric layer does not know which medium it is looking at.
    """
    return (
        scan(EvidenceType.SURVEY_INDEX, source_id=source_id)
        .select(
            "site_id",
            "period_start",
            "site_longitude",
            "site_latitude",
            "site_depth_m",
            "count",
            "effort",
            "protocol",
            "taxon_key",
            "taxon_label",
            "realm",
        )
        .collect()
    )


def _unit_seed(name: str) -> int:
    """A unit's null is a property of that unit, not of its position in a list.

    Phase 3f's correction 1, inherited rather than rediscovered.
    """
    from zlib import crc32  # noqa: PLC0415 -- one caller, and the import documents the mixing

    return (crc32(name.encode()) ^ SEED) & 0x7FFF_FFFF


def _null_percentile(series: pl.DataFrame, column: str, group: str) -> pl.DataFrame:
    """The 95th percentile of each unit's own year-shuffle null.

    Shuffles the year against the value inside one unit, so any structure the unit has other than
    its trend survives under the null.
    """
    out: list[dict[str, object]] = []
    for (key,), unit in series.group_by([group], maintain_order=True):
        name = str(key)
        values = unit[column].to_numpy().astype(float)
        years = unit["year"].to_numpy().astype(float)
        # A slope through two points has no null worth taking.
        if values.size < 3:  # noqa: PLR2004
            continue
        rng = np.random.default_rng(_unit_seed(name))
        centred = years - years.mean()
        denominator = float((centred**2).sum())
        if denominator == 0.0:
            continue
        draws = np.empty(PERMUTATIONS, dtype=float)
        for draw in range(PERMUTATIONS):
            shuffled = rng.permutation(values)
            draws[draw] = float((centred * (shuffled - shuffled.mean())).sum()) / denominator
        out.append({group: name, "null_95": float(np.percentile(np.abs(draws), 95)) * 10.0})
    return pl.DataFrame(out) if out else pl.DataFrame({group: [], "null_95": []})


def _binomial_bar(units: int) -> int:
    """The count chance alone reaches, from `phase3a` rather than a second implementation."""
    from migratlas.reports.phase3a import binomial_bar  # noqa: PLC0415 -- avoids an import cycle

    return int(binomial_bar(units))


def _median_interval(values: np.ndarray, *, name: str) -> tuple[float, float]:
    """A percentile bootstrap interval on the median across units.

    §3 of the registration specified the median and the interquartile range as each network's
    reported quantity, and put its bootstrap on the *per-unit* slope. Predictions 2, 5 and 8 then
    asked whether network medians exclude zero and whether two networks agree "within each other's
    intervals" -- a quantity the design had not defined. Resampling units is the right clustering
    for a median over units, and the gap is recorded as an amendment rather than closed silently.
    """
    if values.size < 2:  # noqa: PLR2004 -- one unit has no interval
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(_unit_seed(name))
    draws = np.empty(PERMUTATIONS, dtype=float)
    for draw in range(PERMUTATIONS):
        draws[draw] = float(np.median(rng.choice(values, size=values.size, replace=True)))
    return (float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5)))


def _iqr(values: np.ndarray) -> tuple[float, float]:
    if values.size == 0:
        return (float("nan"), float("nan"))
    return (float(np.percentile(values, 25)), float(np.percentile(values, 75)))


def distribution(source_id: str, *, min_years: int = MIN_YEARS) -> NetworkResult | None:
    """One network's species-level latitude trends, by the pipeline that produced `marine-null`.

    Returns None where the network holds no qualifying unit at all, which is a coverage statement
    rather than a result.
    """
    frame = load_counts(source_id)
    if frame.is_empty():
        log.info("%s: no rows in the lake", source_id)
        return None
    realm = str(frame["realm"][0])

    cells = range_metrics.to_cells(frame)
    kept, footprint = range_metrics.consistent_footprint(cells)
    if kept.is_empty():
        log.info("%s: no cell survives the consistency rule", source_id)
        return None

    series = range_metrics.centroids(kept)
    if series.is_empty():
        return None
    shifts = range_metrics.shift_per_decade(series, column="mean_latitude", min_years=min_years)
    if shifts.is_empty():
        log.info("%s: no unit clears %d years", source_id, min_years)
        return None

    # A unit is one species in one network, as `marine-null`'s unit is one species in one survey.
    keyed = series.with_columns(unit=pl.col("taxon_key").cast(pl.String)).select(
        "unit", "year", "mean_latitude"
    )
    qualifying = set(shifts["taxon_key"].cast(pl.String).to_list())
    nulls = _null_percentile(
        keyed.filter(pl.col("unit").is_in(qualifying)), "mean_latitude", "unit"
    )
    graded = shifts.with_columns(unit=pl.col("taxon_key").cast(pl.String)).join(
        nulls, on="unit", how="left"
    )
    beat = graded.filter(pl.col("per_decade").abs() > pl.col("null_95"))

    values = shifts["per_decade"].to_numpy().astype(float)
    return NetworkResult(
        source_id=source_id,
        realm=realm,
        units=shifts.height,
        median=float(np.median(values)),
        interval=_median_interval(values, name=f"{source_id}:median"),
        iqr=_iqr(values),
        significant=beat.height,
        bar=_binomial_bar(shifts.height),
        cells_kept=footprint.cells,
        cells_dropped=footprint.cells_dropped,
    )


def calibrate_distribution() -> tuple[float, bool]:
    """Arm A: the estimator must reproduce `marine-null`'s published median.

    By calling `phase1b.analyse` itself. Agreeing with a reimplementation would prove that two
    copies of a method agree, which is not the thing the calibration is for.
    """
    _, pooled, _ = phase1b.analyse(range_metrics.to_cells(phase1b.survey_unit(phase1b.load())))
    if pooled.is_empty():
        return (float("nan"), False)
    median = float(np.median(pooled["per_decade"].to_numpy().astype(float)))
    return (median, abs(median - MARINE_NULL_MEDIAN) < MARINE_TOLERANCE)


def calibrate_timing() -> tuple[float, bool]:
    """Arm D: the estimator must reproduce `autumn-advance`'s published slope."""
    from migratlas.reports.phase1 import load_conus_nights, station_slopes  # noqa: PLC0415

    # The last radar year read from the record, which is what `findings.py` passes when it computes
    # the published slope. A different window is a different number, so it cannot be defaulted.
    nights = load_conus_nights()
    last_year = int(nights.select(pl.col("timestamp").dt.year().max()).item())
    slopes = station_slopes(nights, max_year=last_year)
    autumn = slopes.filter(
        pl.col("season") == "autumn",
        pl.col("quantile") == "q50_doy",
        pl.col("latitude").is_between(37, 50, closed="left"),
    )
    if autumn.is_empty():
        return (float("nan"), False)
    mean = float(autumn["days_per_decade"].to_numpy().astype(float).mean())
    return (mean, abs(mean - AUTUMN_ADVANCE_SLOPE) < AERIAL_TOLERANCE)


def timing() -> TimingResult | None:
    """Leg 2: the flight-date trend per site-species-generation, Phase 1j's declared unit."""
    frame = (
        scan(EvidenceType.SURVEY_INDEX, source_id=FLIGHT_NETWORK)
        .select("site_id", "period_start", "count", "protocol", "taxon_key", "year")
        .collect()
    )
    if frame.is_empty():
        log.info("%s: no rows in the lake", FLIGHT_NETWORK)
        return None

    # The unit carries the generation, which `protocol` holds -- a site's species can fly twice.
    series = frame.select(
        unit=(
            pl.col("site_id").cast(pl.String)
            + pl.lit(":")
            + pl.col("taxon_key").cast(pl.String)
            + pl.lit(":")
            + pl.col("protocol").cast(pl.String)
        ),
        year=pl.col("year"),
        # Reconstructed, because the lake does not store the flight date as a day number.
        # `ingest/ukbms.py` lands `period_start` as the first day of flight and `count` as the days
        # from there to the count-weighted mean, so the mean's day of year is their sum. Fitting
        # `count` alone -- which the first implementation did -- fits how far into a flight period
        # its mean falls, which is a shape and not a date, and would have graded a timing prediction
        # on the wrong quantity.
        flight_day=(pl.col("period_start").dt.ordinal_day().cast(pl.Float64) + pl.col("count")),
    ).drop_nulls()

    depth = series.group_by("unit").agg(pl.col("year").n_unique().alias("years"))
    qualifying = depth.filter(pl.col("years") >= FLIGHT_MIN_YEARS)["unit"]
    kept = series.filter(pl.col("unit").is_in(qualifying))
    if kept.is_empty():
        log.info("%s: no unit clears %d years", FLIGHT_NETWORK, FLIGHT_MIN_YEARS)
        return None

    slopes = range_metrics.shift_per_decade(
        kept.rename({"flight_day": "mean_latitude"}),
        column="mean_latitude",
        group_by=("unit",),
        min_years=FLIGHT_MIN_YEARS,
    )
    if slopes.is_empty():
        return None
    nulls = _null_percentile(kept.rename({"flight_day": "mean_latitude"}), "mean_latitude", "unit")
    graded = slopes.join(nulls, on="unit", how="left")
    beat = graded.filter(pl.col("per_decade").abs() > pl.col("null_95"))

    values = slopes["per_decade"].to_numpy().astype(float)
    return TimingResult(
        units=slopes.height,
        median=float(np.median(values)),
        interval=_median_interval(values, name=f"{FLIGHT_NETWORK}:median"),
        iqr=_iqr(values),
        significant=beat.height,
        bar=_binomial_bar(slopes.height),
    )


def render() -> str:
    """The whole ladder, as text, with the calibration verdicts first."""
    out = [
        "Phase 1k -- four idle monitoring schemes, alone and in company",
        "=" * 78,
        "Pre-registered in docs/methods/phase1k-idle-networks.md before any fit. The calibration",
        "arms call the published reports themselves rather than reimplementing them.",
        "",
    ]

    marine, marine_ok = calibrate_distribution()
    out += [
        "Arm A -- calibration, distribution",
        f"  marine-null median: {marine:+.4f} deg/decade "
        f"(target {MARINE_NULL_MEDIAN:+.3f}) -- {'PASS' if marine_ok else 'FAIL'}",
        "",
    ]
    if not marine_ok:
        out += ["STOP: arm A missed its target, so leg 1 is not interpretable.", ""]

    out += ["Leg 1 -- distribution, per network", ""]
    for source_id in COUNT_NETWORKS:
        result = distribution(source_id)
        if result is None:
            out.append(f"  {source_id}: no qualifying unit -- coverage statement, no trend claimed")
            continue
        verdict = "trend claimed" if result.units >= MIN_UNITS else "COVERAGE ONLY"
        out += [
            f"  {source_id} ({result.realm})",
            f"    units {result.units} ({verdict}), cells kept {result.cells_kept}"
            f" / dropped {result.cells_dropped}",
            f"    median {result.median:+.4f} deg/decade, 95% CI "
            f"[{result.interval[0]:+.4f}, {result.interval[1]:+.4f}]",
            f"    IQR [{result.iqr[0]:+.4f}, {result.iqr[1]:+.4f}]",
            f"    beat own null: {result.significant} of {result.units}, chance bar {result.bar}",
        ]
    out.append("")

    aerial, aerial_ok = calibrate_timing()
    out += [
        "Arm D -- calibration, timing",
        f"  autumn-advance slope: {aerial:+.3f} days/decade "
        f"(target {AUTUMN_ADVANCE_SLOPE:+.2f}) -- {'PASS' if aerial_ok else 'FAIL'}",
        "",
        "Leg 2 -- flight-date timing",
    ]
    flight = timing()
    if flight is None:
        out.append("  no qualifying unit -- coverage statement, no trend claimed")
    else:
        out += [
            f"  units {flight.units}",
            f"  median {flight.median:+.3f} days/decade, 95% CI "
            f"[{flight.interval[0]:+.3f}, {flight.interval[1]:+.3f}]",
            f"  IQR [{flight.iqr[0]:+.3f}, {flight.iqr[1]:+.3f}]",
            f"  beat own null: {flight.significant} of {flight.units}, chance bar {flight.bar}",
        ]

    out += ["", "Predictions are graded in the method note, not here."]
    return "\n".join(out)
