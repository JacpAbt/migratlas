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

    out += [
        "",
        "=" * 70,
        "How to read this",
        "=" * 70,
        "Against the averaged-OLS replication (make phase1-report): agreement in sign and",
        "rough size is corroboration; disagreement would mean the averaged estimate was",
        "carried by a subset of stations. The two agree closely on the replication window.",
        "",
        "The break coefficient is not constant across latitude bands -- it is largest in the",
        "south and near zero in the north. A hardware upgrade has no business behaving that",
        "way, so in the southern bands that dummy is absorbing something else. The likeliest",
        "candidate is the season window: 213-334 doy is a northern-migration window, and at",
        "24-32N autumn passage runs past its end, so any change in how the tail is captured",
        "lands on a year-2012 step. Until that is settled, the trend is separable from the",
        "instrument only where the break is small -- the 37-50N bands.",
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
