"""Phase 2c -- is the thermal sensitivity a response, or a co-trend?

Pre-registered in ``docs/methods/phase2c-timescale.md`` before any refit.
"""

import logging
from dataclasses import dataclass
from typing import Final

import numpy as np
import polars as pl

from migratlas.constants import CLAIM_BAND
from migratlas.reports.phase1 import MIN_YEARS
from migratlas.reports.phase1_robustness import FLEET_MIDPOINT_YEAR
from migratlas.reports.response_floor import MIN_STATIONS, region_of

log = logging.getLogger(__name__)

# The calibration target, quoted from the finding arm A must reproduce.
PUBLISHED_SENSITIVITY: Final = -0.659
# Three significant figures, which is what the registration promised.
TOLERANCE: Final = 5e-4

# The share bracket has two ends -- arm A's and arm B's -- and needs both to be a bracket.
BRACKET_ENDS: Final = 2

# Amendment B: arm C's floor. A station with n observations has at most n-1 usable differences, so
# requiring MIN_YEARS of them would exclude a station the other arms admit and make the ladder a
# comparison of panels. The natural analogue is one fewer.
MIN_DIFFERENCES: Final = MIN_YEARS - 1


@dataclass(frozen=True, slots=True)
class UnitFit:
    """One station's or one region's sensitivity under one arm, with its secular pair."""

    unit: str
    per_degree: float
    warming_per_decade: float
    observed_per_decade: float
    years: int

    @property
    def explained_per_decade(self) -> float:
        return self.per_degree * self.warming_per_decade


@dataclass(frozen=True, slots=True)
class ArmResult:
    """One rung of the ladder, pooled across units the way the published table pools."""

    arm: str
    label: str
    units: int
    per_degree: float
    per_degree_ci: float
    warming: float
    observed: float
    explained: float
    explained_ci: float

    @property
    def residual(self) -> float:
        """`b` -- what a time term absorbs, and what the share leaves unexplained."""
        return self.observed - self.explained

    @property
    def share(self) -> float:
        return self.explained / self.observed if self.observed else float("nan")

    @property
    def clears_zero(self) -> bool:
        return abs(self.per_degree) > self.per_degree_ci


def _series(group: pl.DataFrame, response: str) -> tuple[np.ndarray, ...] | None:
    """One unit's aligned series, or None if it is shorter than the floor every arm shares."""
    series = group.drop_nulls([response, "temperature", "support"]).sort("year")
    if series.height < MIN_YEARS:
        return None
    return (
        series["year"].to_numpy().astype(float),
        series["temperature"].to_numpy().astype(float),
        series["support"].to_numpy().astype(float),
        series[response].to_numpy().astype(float),
    )


def _level_sensitivity(
    years: np.ndarray,
    temperature: np.ndarray,
    support: np.ndarray,
    passage: np.ndarray,
    *,
    with_year: bool,
) -> float | None:
    """Arms A, B and D: the published design, optionally with a centred time term added."""
    from migratlas.reports.phase2a_timing import _fit  # noqa: PLC0415 -- see the note in `collect`

    post = (years >= FLEET_MIDPOINT_YEAR).astype(float)
    columns = [np.ones_like(years)]
    if with_year:
        columns.append(years - years.mean())
    columns += [temperature, support]
    if 0 < post.sum() < post.size:
        columns.append(post)
    fitted = _fit(np.column_stack(columns), passage)
    if fitted is None:
        return None
    return float(fitted[2] if with_year else fitted[1])


def _differenced_sensitivity(
    years: np.ndarray,
    temperature: np.ndarray,
    support: np.ndarray,
    passage: np.ndarray,
) -> float | None:
    """Arm C: first differences, over consecutive years only.

    Amendment A: a difference across a gap spans more than a year and is not a first difference, so
    only steps of exactly one year are used. The break dummy differences to a spike at the
    transition year, which is the correct differenced analogue of a level shift, and it is kept.
    """
    from migratlas.reports.phase2a_timing import _fit  # noqa: PLC0415 -- see the note in `collect`

    step = np.diff(years) == 1.0
    if int(step.sum()) < MIN_DIFFERENCES:
        return None
    d_temperature = np.diff(temperature)[step]
    d_support = np.diff(support)[step]
    d_passage = np.diff(passage)[step]
    d_post = np.diff((years >= FLEET_MIDPOINT_YEAR).astype(float))[step]

    columns = [np.ones_like(d_temperature), d_temperature, d_support]
    if d_post.any():
        columns.append(d_post)
    fitted = _fit(np.column_stack(columns), d_passage)
    if fitted is None:
        return None
    return float(fitted[1])


def _secular(
    years: np.ndarray, temperature: np.ndarray, passage: np.ndarray
) -> tuple[float, float] | None:
    """`W` and `A` for one unit, from the raw series, identically in every arm.

    Amendment D: §3 says `W` is not refitted, so the arms differ only in how `s` is estimated.
    Computing the secular pair once and reusing it is what makes the shares comparable.
    """
    from migratlas.reports.phase2a_timing import _fit  # noqa: PLC0415 -- see the note in `collect`

    warming = _fit(np.column_stack([np.ones_like(years), years]), temperature)
    observed = _fit(np.column_stack([np.ones_like(years), years]), passage)
    if warming is None or observed is None:
        return None
    return (float(warming[1]) * 10.0, float(observed[1]) * 10.0)


def _fit_units(frame: pl.DataFrame, *, unit_column: str, response: str, arm: str) -> list[UnitFit]:
    """Every unit's sensitivity under one arm."""
    out: list[UnitFit] = []
    for (key,), group in frame.sort(unit_column).group_by([unit_column], maintain_order=True):
        prepared = _series(group, response)
        if prepared is None:
            continue
        years, temperature, support, passage = prepared
        if arm == "C":
            per_degree = _differenced_sensitivity(years, temperature, support, passage)
        else:
            per_degree = _level_sensitivity(
                years, temperature, support, passage, with_year=arm != "A"
            )
        secular = _secular(years, temperature, passage)
        if per_degree is None or secular is None:
            continue
        warming, observed = secular
        out.append(
            UnitFit(
                unit=str(key),
                per_degree=per_degree,
                warming_per_decade=warming,
                observed_per_decade=observed,
                years=int(years.size),
            )
        )
    return out


def _pool(arm: str, label: str, fits: list[UnitFit]) -> ArmResult | None:
    """Mean across units with a 1.96 sigma/sqrt(n) interval -- the published table's aggregation."""
    from migratlas.reports.phase2a_timing import _mean_ci  # noqa: PLC0415 -- see `collect`

    if not fits:
        return None
    per_degree, per_degree_ci = _mean_ci(np.array([item.per_degree for item in fits]))
    warming, _ = _mean_ci(np.array([item.warming_per_decade for item in fits]))
    observed, _ = _mean_ci(np.array([item.observed_per_decade for item in fits]))
    explained, explained_ci = _mean_ci(np.array([item.explained_per_decade for item in fits]))
    return ArmResult(
        arm=arm,
        label=label,
        units=len(fits),
        per_degree=per_degree,
        per_degree_ci=per_degree_ci,
        warming=warming,
        observed=observed,
        explained=explained,
        explained_ci=explained_ci,
    )


def claim_band(frame: pl.DataFrame) -> pl.DataFrame:
    """The stations the published `S` is aggregated over, and the only band claimed for."""
    return frame.filter(
        pl.col("station_latitude").is_between(CLAIM_BAND[0], CLAIM_BAND[1], closed="left")
    )


def regional_panel(frame: pl.DataFrame) -> pl.DataFrame:
    """Arm D's units: flyway-and-band regions, built with Phase 3h's own `region_of`.

    Amendment C: the region assignment and the four-station floor are `response_floor`'s, called
    rather than reimplemented, and the panel is restricted to the claim band first so a region
    cannot be built partly out of stations no claim covers. The response and every covariate are
    averaged unweighted across member stations, which is Phase 3h's construction.
    """
    band = claim_band(frame)
    sites = band.group_by("station_id").agg(
        lat=pl.col("station_latitude").first(), lon=pl.col("station_longitude").first()
    )
    named = {
        str(row["station_id"]): region
        for row in sites.to_dicts()
        if (region := region_of(float(row["lat"]), float(row["lon"]))) is not None
    }
    if not named:
        return pl.DataFrame()

    tagged = band.with_columns(
        region=pl.col("station_id").replace_strict(named, default=None, return_dtype=pl.String)
    ).drop_nulls("region")
    members = tagged.group_by("region").agg(pl.col("station_id").n_unique().alias("stations"))
    for row in members.filter(pl.col("stations") < MIN_STATIONS).to_dicts():
        log.info(
            "%s: %d stations, under the floor of %d",
            row["region"],
            row["stations"],
            MIN_STATIONS,
        )
    kept = members.filter(pl.col("stations") >= MIN_STATIONS)["region"]
    return (
        tagged.filter(pl.col("region").is_in(kept))
        .group_by("region", "year")
        .agg(
            pl.col("q50_doy").mean(),
            pl.col("temperature").mean(),
            pl.col("support").mean(),
        )
        .sort("region", "year")
    )


def collect() -> list[ArmResult]:
    """The four arms, in the order the registration makes them."""
    # Private names, imported rather than duplicated: arm A has to reproduce the published `S`
    # exactly, and two copies of a panel or an aggregation are two things that drift. The same
    # precedent `reports/response.py` set, for the same reason.
    from migratlas.reports.phase2a_timing import panel  # noqa: PLC0415 -- heavy, and only here

    # Read once. The panel is the radar record joined to two reanalyses, and building it twice
    # would double the slowest part of this phase for two views of one frame.
    built = panel()
    frame = claim_band(built)
    results: list[ArmResult] = []
    for arm, label in (
        ("A", "as published, no time term"),
        ("B", "+ centred year term"),
        ("C", "first differences, consecutive years"),
    ):
        fits = _fit_units(frame, unit_column="station_id", response="q50_doy", arm=arm)
        pooled = _pool(arm, label, fits)
        if pooled is not None:
            results.append(pooled)

    regions = regional_panel(built)
    if regions.is_empty():
        log.warning("arm D: no region clears the floor, so it publishes as a coverage statement")
    else:
        pooled = _pool(
            "D",
            "+ year term, flyway-and-band regions",
            _fit_units(regions, unit_column="region", response="q50_doy", arm="B"),
        )
        if pooled is not None:
            results.append(pooled)
    return results


@dataclass(frozen=True, slots=True)
class Bracket:
    """The pair §3 registers as the deliverable: the share under each of the two specifications.

    Arms C and D are deliberately not in it. Arm C is a registered sensitivity and arm D is a
    cross-check at a different unit, and either one substituted for an end of the bracket would be
    a different quantity wearing the bracket's name.
    """

    published_share: float
    interannual_share: float
    interannual: float
    interannual_ci: float
    units: int

    @property
    def low(self) -> float:
        return min(self.published_share, self.interannual_share)

    @property
    def high(self) -> float:
        return max(self.published_share, self.interannual_share)

    @property
    def clears_zero(self) -> bool:
        return abs(self.interannual) > self.interannual_ci


def bracket() -> Bracket | None:
    """The bracket on the explained share, for the ledger to carry beside the point estimate.

    Goes through `collect` rather than fitting arms A and B a second time: two paths to one pair of
    numbers are two things that drift, and the extra arms cost a groupby on a panel already built.
    """
    results = collect()
    if not calibrated(results):
        log.warning("phase2c: arm A missed its calibration, so no bracket is published")
        return None
    arm_a = next((item for item in results if item.arm == "A"), None)
    arm_b = next((item for item in results if item.arm == "B"), None)
    if arm_a is None or arm_b is None:
        return None
    return Bracket(
        published_share=arm_a.share,
        interannual_share=arm_b.share,
        interannual=arm_b.per_degree,
        interannual_ci=arm_b.per_degree_ci,
        units=arm_b.units,
    )


def calibrated(results: list[ArmResult]) -> bool:
    """Arm A must reproduce the published `S` to three significant figures, or nothing is read."""
    arm_a = next((item for item in results if item.arm == "A"), None)
    return arm_a is not None and abs(arm_a.per_degree - PUBLISHED_SENSITIVITY) < TOLERANCE


def render() -> str:
    """The ladder, the bracket on the explained share, and one verdict line."""
    out = [
        "Phase 2c -- is the thermal sensitivity a response, or a co-trend?",
        "=" * 78,
        "Pre-registered in docs/methods/phase2c-timescale.md before any refit. The deliverable is",
        "an interval on the explained share, because a secular response and a non-thermal process",
        "that trends alike are the same column of this design matrix.",
        "",
    ]
    results = collect()
    if not results:
        out.append("VERDICT: no arm fitted -- nothing to read.")
        return "\n".join(out)

    header = (
        f"{'arm':<4} {'units':>5} {'S d/degC':>18} {'W':>8} "
        f"{'S x W':>18} {'observed':>9} {'residual':>9} {'share':>7}"
    )
    out.append(header)
    for item in results:
        out.append(
            f"{item.arm:<4} {item.units:>5} "
            f"{item.per_degree:>+9.3f} +/- {item.per_degree_ci:<5.3f} "
            f"{item.warming:>+8.3f} "
            f"{item.explained:>+9.3f} +/- {item.explained_ci:<5.3f} "
            f"{item.observed:>+9.3f} {item.residual:>+9.3f} {item.share:>7.2f}"
        )
    out += ["", "  " + "  ".join(f"{item.arm}: {item.label}" for item in results), ""]

    ok = calibrated(results)
    arm_a = next((item for item in results if item.arm == "A"), None)
    measured = f"{arm_a.per_degree:+.4f}" if arm_a else "not fitted"
    out.append(
        f"Calibration -- arm A against the published {PUBLISHED_SENSITIVITY:+.3f}: "
        f"{measured} -- {'PASS' if ok else 'FAIL'}"
    )
    if not ok:
        out += ["", "VERDICT: calibration FAILED -- no arm above A is interpreted."]
        return "\n".join(out)

    shares = {item.arm: item.share for item in results}
    bracket = sorted(value for arm, value in shares.items() if arm in {"A", "B"})
    span = (
        f"  {bracket[0]:.0%} to {bracket[-1]:.0%}"
        if len(bracket) == BRACKET_ENDS
        else "  incomplete -- one end of the bracket did not fit"
    )
    out += [
        "",
        "The bracket on the explained share, which is what this phase publishes:",
        span,
        "",
        "Predictions are graded in the method note, not here.",
    ]

    arm_b = next((item for item in results if item.arm == "B"), None)
    if arm_b is None:
        out.append("VERDICT: arm B did not fit.")
        return "\n".join(out)
    clears = "clears" if arm_b.clears_zero else "DOES NOT CLEAR"
    out.append(
        f"VERDICT: arm B S {arm_b.per_degree:+.3f} +/- {arm_b.per_degree_ci:.3f} {clears} zero;"
        f" share bracket {bracket[0]:.0%} to {bracket[-1]:.0%}"
    )
    return "\n".join(out)
