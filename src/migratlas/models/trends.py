"""Hierarchical trend in passage date: one estimate, with stations as a random effect.

The per-station slopes in ``metrics.phenology.passage_trends`` are the right shape for a
replication -- they are what Horton et al. fit -- but averaging them treats a station with
31 years and one with 15 as equally informative, and treats each slope as if it carried no
uncertainty of its own. A mixed model estimates the population trend directly, with station
random effects absorbing the fact that each site has its own baseline timing and its own
sampling history.

Nothing here is taxon-aware: the input is a passage-date panel keyed by site and year, which
a radar network, a survey scheme or an acoustic array can all produce.
"""

import logging
import warnings
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np
import polars as pl

if TYPE_CHECKING:
    from collections.abc import Sequence

log = logging.getLogger(__name__)

DAYS_PER_DECADE: Final = 10
MIN_SITES: Final = 10
MIN_YEARS: Final = 2

# Latitude is centred here rather than at its sample mean so the intercept means the same thing
# across seasons and across subsets. Roughly mid-CONUS.
LATITUDE_ORIGIN: Final = 40.0


class NotEnoughDataError(ValueError):
    """Too few sites or years to identify a hierarchical trend."""


@dataclass(frozen=True, slots=True)
class Estimate:
    """One coefficient, on the scale it is reported in."""

    name: str
    value: float
    stderr: float
    pvalue: float

    @property
    def ci95(self) -> float:
        return 1.96 * self.stderr

    def __str__(self) -> str:
        return f"{self.name:<28} {self.value:+.3f} +/- {self.ci95:.3f}  p={self.pvalue:.3g}"


@dataclass(frozen=True, slots=True)
class TrendFit:
    """A fitted passage-date trend."""

    season: str
    sites: int
    observations: int
    years: tuple[int, int]
    per_decade: Estimate
    """Days per decade at ``LATITUDE_ORIGIN``. Negative means earlier passage."""
    per_decade_per_degree: Estimate | None
    """Extra days per decade for each degree of latitude north, if latitude was included."""
    break_shift: Estimate | None
    """Level shift in days attributed to the instrument change, if a break was modelled."""
    curvature: Estimate | None
    """Quadratic term in decades, if one was fitted. Nonzero means the trend is not linear."""
    site_sd: float
    """Between-site spread in baseline passage date, in days."""
    converged: bool

    def __str__(self) -> str:
        lines = [
            f"{self.season}: {self.sites} sites, {self.observations} site-years, "
            f"{self.years[0]}-{self.years[1]}",
            f"  {self.per_decade}",
        ]
        if self.per_decade_per_degree:
            lines.append(f"  {self.per_decade_per_degree}")
        if self.curvature:
            lines.append(f"  {self.curvature}")
        if self.break_shift:
            lines.append(f"  {self.break_shift}")
        lines.append(f"  between-site sd {self.site_sd:.1f} d")
        if not self.converged:
            lines.append("  DID NOT CONVERGE -- do not report this estimate")
        return "\n".join(lines)


def fit_passage_trend(  # noqa: PLR0913 -- every argument is an analysis choice that belongs
    # in a method note; folding them into a config object would hide them from the reader
    panel: pl.DataFrame,
    *,
    site: str = "station_id",
    response: str = "q50_doy",
    latitude: str | None = "station_latitude",
    break_year: int | None = None,
    curvature: bool = False,
    random_slopes: bool = True,
) -> TrendFit:
    """Fit ``response ~ year (x latitude) (+ break)`` with site random effects.

    Args:
        panel: One row per site, season and year. A ``season`` column, if present, must hold a
            single value -- seasons are fitted separately because spring and autumn passage are
            different phenomena with different drivers, and pooling them estimates neither.
        site: Column identifying a site.
        response: Passage-date column, in day of year.
        latitude: Site latitude column, for the trend-by-latitude interaction. ``None`` fits a
            single trend, which is the right model when sites span little latitude.
        break_year: First year on the new instrument. Included as a level shift, because an
            instrument change that raises measured passage everywhere would otherwise be read
            as a trend. Its coefficient is reported so a reader can see how much the fit
            attributes to hardware rather than to animals.
        curvature: Add a quadratic in time. Worth fitting whenever a break term is large,
            because a linear-plus-step model fitted to a curved series parks a spurious step
            near the middle of the record -- and a mid-record break year is exactly where an
            instrument-upgrade dummy tends to sit.
        random_slopes: Let each site have its own trend as well as its own baseline. On by
            default: without it, a site whose timing genuinely moved differently is forced to
            share the population slope, and the population standard error comes out too small.

    Raises:
        NotEnoughDataError: with fewer than ``MIN_SITES`` sites or fewer than two years.
    """
    # Imported here, not at module scope: statsmodels is the `stats` extra, and a lean install
    # must still be able to import this package.
    import statsmodels.formula.api as smf  # noqa: PLC0415
    from statsmodels.tools.sm_exceptions import ConvergenceWarning  # noqa: PLC0415

    frame = panel.filter(pl.col(response).is_not_null())
    seasons = frame["season"].unique().to_list() if "season" in frame.columns else ["unnamed"]
    if len(seasons) > 1:
        msg = f"Fit one season at a time; got {sorted(seasons)}."
        raise NotEnoughDataError(msg)

    sites = frame[site].n_unique()
    years = frame["year"].unique().sort()
    if sites < MIN_SITES or years.len() < MIN_YEARS:
        msg = f"{sites} sites and {years.len()} years is not enough to identify a trend."
        raise NotEnoughDataError(msg)

    # Centred on the panel's own midpoint, so the intercept is the passage date in a typical
    # year rather than an extrapolation back to year zero.
    midpoint = float(np.mean(years.to_numpy()))
    design = frame.with_columns(
        decade=(pl.col("year") - midpoint) / DAYS_PER_DECADE,
        y=pl.col(response).cast(pl.Float64),
    )

    terms = ["decade"]
    if latitude is not None:
        design = design.with_columns(lat=pl.col(latitude) - LATITUDE_ORIGIN)
        terms += ["lat", "decade:lat"]
    if curvature:
        design = design.with_columns(decade2=pl.col("decade") ** 2)
        terms.append("decade2")
    if break_year is not None:
        design = design.with_columns(post=(pl.col("year") >= break_year).cast(pl.Float64))
        terms.append("post")

    pandas = design.select([site, "y", *_columns_for(terms)]).to_pandas()
    model = smf.mixedlm(
        f"y ~ {' + '.join(terms)}",
        pandas,
        groups=pandas[site],
        re_formula="~decade" if random_slopes else None,
    )
    # lbfgs first, Nelder-Mead as the fallback: the default nm alone is slow on a panel this
    # size and stops on a loose tolerance, and lbfgs on its own fails on the flatter fits.
    #
    # statsmodels raises a ConvergenceWarning for the failed first attempt even when the retry
    # succeeds, so the warning would report a problem that is not there. Convergence is carried
    # on the result instead, where a reader of the number can see it.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        result = model.fit(method=["lbfgs", "nm"], maxiter=400)
    if not result.converged:
        log.warning("mixed model did not converge for %s; the estimate is not reportable", seasons)

    def estimate(term: str, label: str, scale: float = 1.0) -> Estimate | None:
        if term not in result.params:
            return None
        return Estimate(
            label,
            float(result.params[term]) * scale,
            float(result.bse[term]) * scale,
            float(result.pvalues[term]),
        )

    per_decade = estimate("decade", "days per decade")
    if per_decade is None:
        msg = "The year term dropped out of the design, which means it was collinear."
        raise NotEnoughDataError(msg)

    return TrendFit(
        season=str(seasons[0]),
        sites=sites,
        observations=frame.height,
        years=(int(years[0]), int(years[-1])),
        per_decade=per_decade,
        per_decade_per_degree=estimate("decade:lat", "d/decade per degree N"),
        break_shift=estimate("post", "instrument shift (days)"),
        curvature=estimate("decade2", "curvature (d/decade^2)"),
        # Variance of the random intercept, reported as a standard deviation in days.
        site_sd=float(np.sqrt(max(result.cov_re.iloc[0, 0], 0.0))),
        converged=bool(result.converged),
    )


def _columns_for(terms: Sequence[str]) -> list[str]:
    """The distinct design columns an interaction-bearing term list refers to."""
    seen = dict.fromkeys(part for term in terms for part in term.split(":"))
    return list(seen)
