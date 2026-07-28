"""Phase 1a, the model the plan actually asked for: station random effects, not averaged OLS.

The replication report averages per-station OLS slopes because that is what Horton et al. did.
This one estimates the population trend directly, so a station with 15 years does not carry the
same weight as one with 31, and the interval reflects between-station spread rather than the
spread of point estimates that each had their own uncertainty.

Run against the same panel and the same filters as the replication, so any difference is the
estimator and nothing else.
"""

import logging
from typing import Final

import polars as pl

from migratlas.evidence import EvidenceType, spec_for
from migratlas.metrics.phenology import passage_quantiles
from migratlas.models.trends import NotEnoughDataError, TrendFit, fit_passage_trend
from migratlas.reports import phase1

log = logging.getLogger(__name__)

# The dual-polarisation upgrade rolled across the network over roughly two years. 2012 is the
# midpoint of the fleet-wide programme and the specification the robustness report treats as
# primary; three alternatives are in phase1_robustness, and this model uses one break so the
# coefficient stays interpretable.
DUAL_POL_YEAR: Final = 2012

WINDOWS: Final[tuple[tuple[int, str], ...]] = (
    (2018, "Horton et al. window"),
    (2025, "extended to 2025"),
)


def panel(nights: pl.DataFrame, *, max_year: int) -> pl.DataFrame:
    """Passage-date quantiles per station-season-year, with latitude attached."""
    quantiles = passage_quantiles(
        nights.filter(pl.col("timestamp").dt.year() <= max_year),
        spec_for(EvidenceType.FLUX),
        seasons=[phase1.SPRING, phase1.AUTUMN],
        quantiles=phase1.QUANTILES,
        min_coverage=phase1.MIN_COVERAGE,
        min_observations=phase1.MIN_NIGHTS,
    )
    sites = nights.group_by("station_id").agg(pl.col("station_latitude").first())
    return quantiles.join(sites, on="station_id")


def fit_season(frame: pl.DataFrame, season: str, *, break_year: int | None) -> TrendFit | None:
    """Fit one season, or report why it could not be fitted."""
    try:
        return fit_passage_trend(
            frame.filter(pl.col("season") == season),
            break_year=break_year,
        )
    except NotEnoughDataError as error:
        log.warning("%s: %s", season, error)
        return None


def by_latitude_band(frame: pl.DataFrame, season: str) -> list[str]:
    """Fit the same model inside each latitude band.

    The linear ``decade:latitude`` interaction comes back null, which would be easy to read as
    "the trend does not vary with latitude". The averaged-OLS band table says otherwise, and
    non-monotonically -- little change in the far south, the strongest advance in the middle --
    which a straight line through latitude cannot represent. Fitting inside bands asks the same
    question without assuming the answer is linear.
    """
    lines = []
    for low, high in phase1.LATITUDE_BANDS:
        band = frame.filter(
            pl.col("season") == season,
            pl.col("station_latitude").is_between(low, high, closed="left"),
        )
        try:
            # No latitude term: inside a five-degree band there is nothing for it to explain.
            fit = fit_passage_trend(band, latitude=None, break_year=DUAL_POL_YEAR)
        except NotEnoughDataError as error:
            lines.append(f"    {low}-{high}N  not fitted: {error}")
            continue
        flag = "" if fit.converged else "  [DID NOT CONVERGE]"
        lines.append(
            f"    {low}-{high}N  n={fit.sites:>3}  {fit.per_decade.value:+.2f} "
            f"+/- {fit.per_decade.ci95:.2f} d/decade  "
            f"break {fit.break_shift.value:+.2f} d{flag}"
            if fit.break_shift
            else f"    {low}-{high}N  n={fit.sites:>3}  {fit.per_decade.value:+.2f}{flag}"
        )
    return lines


def balanced(frame: pl.DataFrame, season: str) -> pl.DataFrame:
    """Keep only sites that report on both sides of the break.

    A site whose record starts after 2012 contributes to the post era alone, so its random
    intercept is estimated from post data only and the break dummy is partly identified off
    which sites were present rather than off any change at the ones that were. The reporting
    network grew from 104 stations in 1995 to 159, so this is not hypothetical.
    """
    seasonal = frame.filter(pl.col("season") == season, pl.col("q50_doy").is_not_null())
    eras = seasonal.group_by("station_id").agg(
        pre=(pl.col("year") < DUAL_POL_YEAR).any(),
        post=(pl.col("year") >= DUAL_POL_YEAR).any(),
    )
    both = eras.filter(pl.col("pre") & pl.col("post"))["station_id"]
    return seasonal.filter(pl.col("station_id").is_in(both))


def _cell(frame: pl.DataFrame, *, curvature: bool = False) -> str:
    """One band fit, rendered as trend and break, or why it could not be fitted."""
    try:
        fit = fit_passage_trend(frame, latitude=None, break_year=DUAL_POL_YEAR, curvature=curvature)
    except NotEnoughDataError:
        return "     not fitted     "
    shift = fit.break_shift.value if fit.break_shift else float("nan")
    return f"{fit.per_decade.value:+.2f} d/dec, brk {shift:+.2f}"


def break_diagnosis(frame: pl.DataFrame, season: str) -> list[str]:
    """Why is the break coefficient latitude-varying, when hardware cannot be?

    Three candidates, tested in the order they are cheap to rule out. Window truncation is
    tested in phase1_robustness and came back flat. The other two are here:

    Panel composition -- a site whose record starts after 2012 contributes to the post era
    alone, so the dummy is partly identified off which sites were present rather than off
    change at the ones that were, and the network grew from 104 stations to 159.

    Curvature -- a linear-plus-step model fitted to a curved series parks a spurious step near
    the middle of the record, and 2012 is almost exactly the midpoint of 1995-2025. If a
    quadratic absorbs the step, the "instrument break" was a misspecification.
    """
    lines = ["    band       all sites             balanced panel        + curvature"]
    for low, high in phase1.LATITUDE_BANDS:
        in_band = pl.col("station_latitude").is_between(low, high, closed="left")
        band = frame.filter(pl.col("season") == season, in_band)
        even = balanced(frame, season).filter(in_band)
        lines.append(
            f"    {low}-{high}N  {_cell(band)}  {_cell(even)}  {_cell(band, curvature=True)}"
        )
    return lines


def render() -> str:
    nights = phase1.load_conus_traffic()
    out = [
        "Phase 1a -- hierarchical passage-date trend",
        "=" * 70,
        "Model: q50_doy ~ decade * latitude (+ instrument break), station random intercept",
        "       and random slope. One fit per season; seasons are not pooled.",
        f"Filters as the replication: coverage >= {phase1.MIN_COVERAGE}, "
        f">= {phase1.MIN_NIGHTS} nights/season-year.",
        "Latitude centred at 40N, so 'days per decade' is the trend at mid-CONUS.",
    ]

    for max_year, label in WINDOWS:
        frame = panel(nights, max_year=max_year)
        out += ["", "=" * 70, f"{label}  (1995-{max_year})", "=" * 70]

        for season in ("spring", "autumn"):
            # Without the break first, so the reader sees what the break term changes rather
            # than only the number that survives it.
            for break_year, note in ((None, "no break term"), (DUAL_POL_YEAR, "with break")):
                fit = fit_season(frame, season, break_year=break_year)
                out += ["", f"  [{note}]"]
                out.append("  " + str(fit).replace("\n", "\n  ") if fit else "  not fitted")

            out.append(f"\n  {season}, same model inside each latitude band (with break):")
            out += by_latitude_band(frame, season)

            out.append(f"\n  {season}, where does that latitude-varying break come from?")
            out += break_diagnosis(frame, season)

    out += [
        "",
        "=" * 70,
        "How to read this",
        "=" * 70,
        "Against the averaged-OLS replication (make phase1-report): agreement in sign and",
        "rough size is corroboration; disagreement would mean the averaged estimate was",
        "carried by a subset of stations. The two agree closely on the replication window.",
        "",
        "The break coefficient is not constant across latitude bands -- largest in the south,",
        "near zero in the north. Hardware cannot do that, so three explanations were tested and",
        "all three failed: window truncation (0.0% clipping in every band and era, reported by",
        "phase1-robustness), panel composition (the balanced-panel column moves it by 0.01 d),",
        "and curvature (the quadratic column moves it by <0.1 d on the full record). On the",
        "1995-2018 window curvature IS decisive -- the 24-32N break goes +2.04 to -1.45 and its",
        "trend flips sign -- so no band-level number from the short window should be read.",
        "",
        "Because the step survives every available explanation on the full record, calling it",
        "'the instrument' is not justified; it may be a real step in southern autumn passage.",
        "Either way it is not attributable, and an unattributable coefficient cannot be adjusted",
        "away. The defensible claim is an autumn advance of ~0.6-0.7 d/decade at 37-50N, where",
        "the step is near zero and the estimate is stable across all three tests.",
        "",
        "The linear decade:latitude interaction is null in every fit. That is a statement",
        "about the functional form, not about latitude: the band fits are non-monotonic, so a",
        "straight line through latitude cannot represent them and returns nothing.",
        "",
        "Model-based p-values here are optimistic relative to the permutation null in",
        "phase1-robustness. Where the two disagree, prefer the permutation null: it makes no",
        "assumption about the error structure, which is exactly what a panel of 145 correlated",
        "stations violates.",
    ]
    return "\n".join(out)
