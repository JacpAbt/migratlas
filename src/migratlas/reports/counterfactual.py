"""The world without us: observed passage dates against the counterfactual.

`phase2a_attribution` reduced the causal chain to one number, `f = 0.98`. This draws it. Two
trajectories over the radar record: what the birds -- and bats, and insects -- actually did, and
what the same arithmetic says they would have done without human forcing.

**The counterfactual is not a flat line, and that is the point.** It removes only the part that was
attributed: `f x S x W`, the human-driven share of the thermally-explained advance. About half the
observed advance does not track temperature at all and was never attributed to anything, so it stays
in the counterfactual. A counterfactual that flattened the trend would be claiming the unexplained
half is natural, which nothing here establishes.

**And the divergence is small, which is the honest shape of an attributed signal.** Over the
thirty-year window the two lines part by under a day, inside year-to-year scatter of several days.
Drawing that faithfully -- the scatter behind the lines, the axis in days rather than stretched --
teaches something a dramatic diverging ribbon would not: this is what a real attributed trend looks
like, a fraction of a small signal sitting inside large natural variability. It is still a signal.
The alternative is a chart that flatters the result and misleads about every other result like it.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Final

import numpy as np
import polars as pl

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)

SCHEMA_VERSION: Final = 1


@dataclass(frozen=True, slots=True)
class YearPoint:
    """One year's observed passage date, averaged across the claim band's stations."""

    year: int
    observed: float
    """Median passage day-of-year, meaned over stations. Lower is earlier."""
    stations: int
    spread: float
    """95% interval on the mean across stations -- the *sampling* spread, not the year-to-year
    variability, which is what the scatter of the points themselves shows."""


@dataclass(frozen=True, slots=True)
class Line:
    """A fitted trajectory, anchored so the two lines are comparable rather than offset."""

    key: str
    label: str
    per_decade: float
    start: float
    end: float
    note: str


@dataclass(frozen=True, slots=True)
class Ribbon:
    schema_version: int
    window: tuple[int, int]
    unit: str
    anchor: float
    """The mean observed date over the window. Both lines pass through it at the midpoint, because
    the attribution constrains the *slopes* and says nothing about the level."""
    years: list[YearPoint]
    lines: list[Line]
    terms: dict[str, float]
    divergence: float
    """Days between the two lines at the end of the window. Small on purpose -- see the module
    docstring."""
    caveat: str
    method: str
    supporting: list[str] = field(default_factory=list)


def observed_series(max_year: int = 2025) -> list[YearPoint]:
    """Mean passage date per year across the stations the claim is made from."""
    from migratlas.evidence import EvidenceType, spec_for  # noqa: PLC0415
    from migratlas.metrics.phenology import passage_quantiles  # noqa: PLC0415
    from migratlas.reports.phase1 import (  # noqa: PLC0415
        AUTUMN,
        MIN_COVERAGE,
        MIN_NIGHTS,
        load_conus_nights,
    )
    from migratlas.reports.sandbox import CLAIM_BAND  # noqa: PLC0415

    nights = load_conus_nights(quantity="reflectivity_traffic")
    quantiles = passage_quantiles(
        nights.filter(pl.col("timestamp").dt.year() <= max_year),
        spec_for(EvidenceType.FLUX),
        seasons=[AUTUMN],
        quantiles=[0.5],
        min_coverage=MIN_COVERAGE,
        min_observations=MIN_NIGHTS,
    ).filter(pl.col("q50_doy").is_not_null())

    sites = nights.group_by("station_id").agg(pl.col("station_latitude").first())
    band = quantiles.join(sites, on="station_id", how="inner").filter(
        pl.col("station_latitude").is_between(*CLAIM_BAND, closed="left")
    )

    per_year = (
        band.group_by("year")
        .agg(
            observed=pl.col("q50_doy").mean(),
            deviation=pl.col("q50_doy").std(),
            stations=pl.len(),
        )
        .sort("year")
    )
    return [
        YearPoint(
            year=int(row["year"]),
            observed=float(row["observed"]),
            stations=int(row["stations"]),
            spread=(
                1.96 * float(row["deviation"]) / np.sqrt(row["stations"])
                if row["deviation"] is not None and row["stations"] > 1
                else 0.0
            ),
        )
        for row in per_year.iter_rows(named=True)
    ]


def collect(max_year: int = 2025) -> Ribbon:
    """Build the ribbon from the attribution's own terms, recomputed rather than quoted."""
    from migratlas.reports import phase2a_attribution as attribution  # noqa: PLC0415

    years = observed_series(max_year)
    if not years:
        msg = "no claim-band station has a passage series; run the radar ingest first"
        raise RuntimeError(msg)

    simulations = attribution.simulated()
    windows = [
        found
        for window in attribution.WINDOWS
        if (found := attribution.fraction(simulations, window)) is not None
    ]
    seen = attribution.observed()
    if not windows or seen is None:
        msg = "the attribution has no fraction or no observed terms; run its ingests first"
        raise RuntimeError(msg)
    primary = attribution.chosen(windows)

    human = primary.ensemble * seen.explained
    window = (years[0].year, years[-1].year)
    midpoint = (window[0] + window[1]) / 2
    anchor = float(np.mean([point.observed for point in years]))
    span = window[1] - window[0]

    def line(key: str, label: str, per_decade: float, note: str) -> Line:
        return Line(
            key=key,
            label=label,
            per_decade=per_decade,
            start=anchor + per_decade / 10 * (window[0] - midpoint),
            end=anchor + per_decade / 10 * (window[1] - midpoint),
            note=note,
        )

    lines = [
        line(
            "observed",
            "what happened",
            seen.advance,
            "The fitted trend at the claim-band stations, and the number the ledger publishes.",
        ),
        line(
            "counterfactual",
            "without human forcing",
            seen.advance - human,
            "The observed trend with the attributed human share removed. It still advances, "
            "because about half the observed advance does not track temperature at all and was "
            "never attributed to anything; flattening it would claim that half is natural.",
        ),
        line(
            "no-thermal",
            "with no warming at all",
            seen.advance - seen.explained,
            "A second reference: the trend with the entire temperature response removed, human "
            "or not. It sits almost on top of the counterfactual, and that near-coincidence is "
            "what f = 0.98 looks like -- almost none of the warming was natural.",
        ),
    ]

    return Ribbon(
        schema_version=SCHEMA_VERSION,
        window=window,
        unit="day of year",
        anchor=anchor,
        years=years,
        lines=lines,
        terms={
            "sensitivity_days_per_degree": seen.sensitivity,
            "warming_degrees_per_decade": seen.warming,
            "thermal_days_per_decade": seen.explained,
            "human_share_of_warming": primary.ensemble,
            "human_days_per_decade": human,
            "observed_days_per_decade": seen.advance,
            "stations": float(seen.stations),
            "models": float(primary.models),
        },
        divergence=abs(human) / 10 * span,
        caveat=(
            "The two lines part by under a day across thirty years, inside a year-to-year scatter "
            "of several days. That is the honest size of the signal: the attribution is of the "
            "*trend*, not of any single year, and no year's date can be called human-caused. The "
            "counterfactual also inherits every limit of the response function it is built on: it "
            "attributes the warming the animals tracked, not the animals."
        ),
        method="docs/methods/counterfactual.md",
        supporting=[
            f"The human share of the modelled warming is {primary.ensemble:.2f} across "
            f"{primary.models} CMIP6 models with both a historical and a natural-forcing-only run.",
            "A synthetic null on two halves of one experiment returns 3% of the forced difference.",
            "Shuffling the years destroys the observed trend entirely (-0.56 to -0.001 days per "
            "decade), so the line being drawn is order and not arithmetic.",
        ],
    )


def render(ribbon: Ribbon) -> str:
    return json.dumps(asdict(ribbon), indent=1)


def write(destination: Path, computed: Ribbon | None = None) -> int:
    payload = render(computed if computed is not None else collect())
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(payload + "\n", encoding="utf-8")
    return len(payload)
