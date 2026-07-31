"""The second counterfactual, and how far it disagrees with the first.

Pre-registered in `docs/methods/phase2a-attrici.md`. Four predictions, one of which is a stop
condition: if the factual half of ISIMIP does not reproduce the ERA5 warming already in the lake at
the same stations, the pair describes a different place and nothing here may be reported.

The two counterfactuals answer different questions and this module does not average them.

- **DAMIP** removes `f x S x W`, where `f` is the human share of the *ensemble-mean forced* warming.
  Averaging fifteen models suppresses internal variability by construction, so what is left is close
  to a pure forced response, and `f` came out at 0.98.
- **ATTRICI** removes `S x (W_obsclim - W_counterclim)`, where the difference is the part of each
  station's *actual* daily series that correlates with global mean temperature. A 25-year trend at
  one 0.5-degree cell contains a great deal of internal variability, and only the GMT-correlated
  part comes out.

So a gap between them is expected rather than a fault, and the useful output is two numbers with an
explanation of what each measures. The response function `S` is shared: it is fitted once in
`phase2a_timing` on observations and reused here rather than refitted, so the only thing that
differs between the two attributions is the warming term.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Final, NamedTuple

import numpy as np
import polars as pl

from migratlas.drivers import attrici, era5
from migratlas.drivers.schema import DRIVER_SAMPLES
from migratlas.lake.reader import scan_dataset
from migratlas.reports.phase1 import MIN_YEARS, load_conus_nights
from migratlas.reports.phase2a_timing import (
    CLAIM_BAND,
    PRE_SEASON,
    TEMPERATURE,
    sensitivities,
)

log = logging.getLogger(__name__)

WINDOW: Final[tuple[int, int]] = (1995, attrici.LAST_YEAR)
"""Where the two datasets overlap. `counterclim` ends in 2019; the radar record runs to 2025."""

COUNTERFACTUAL: Final = "air_temperature_2m_counterfactual"

MIN_FOR_INTERVAL: Final = 2
"""Below this there is a mean but no spread, so no interval can be put on it."""

CONTROL_TOLERANCE: Final = 1.0
"""How many combined intervals `obsclim` may differ from ERA5 by before the control fails.

One, not two: the point of a stop condition is that it can stop. A tolerance wide enough to pass
whatever arrives is not a control, and the pre-registration named this as the test that licenses
everything downstream.
"""


class Warming(NamedTuple):
    """A within-station June-July trend, averaged over the claim band."""

    label: str
    per_decade: float
    ci95: float
    stations: int


def _yearly(source: str, variable: str) -> pl.DataFrame:
    """Mean June-July temperature per station-year, exactly as `phase2a_timing` computes it.

    Same window, same months, same aggregation. Any difference in method between the two would show
    up as a difference in warming and be read as a property of the data.
    """
    return (
        scan_dataset(DRIVER_SAMPLES.name, source_id=source)
        .filter(
            pl.col("variable") == variable,
            pl.col("period_start").dt.month().is_in(PRE_SEASON),
            pl.col("period_start").dt.year().is_between(*WINDOW),
        )
        .select(
            station_id=pl.col("site_id"),
            year=pl.col("period_start").dt.year(),
            value=pl.col("value"),
        )
        .group_by("station_id", "year")
        .agg(pl.col("value").mean().alias("temperature"))
        .collect()
    )


def _trends(frame: pl.DataFrame) -> pl.DataFrame:
    """A within-station trend per decade. Across stations it would be a claim about geography."""
    rows = []
    for (station,), group in frame.group_by(["station_id"], maintain_order=True):
        series = group.sort("year")
        if series.height < MIN_YEARS:
            continue
        years = series["year"].to_numpy().astype(float)
        slope = float(np.polyfit(years, series["temperature"].to_numpy(), 1)[0])
        rows.append({"station_id": str(station), "trend": slope * 10.0})
    return pl.DataFrame(rows, schema={"station_id": pl.String, "trend": pl.Float64})


def _in_band(frame: pl.DataFrame) -> pl.DataFrame:
    """The claim band, from the radar's own station latitudes."""
    nights = load_conus_nights(quantity="reflectivity_traffic")
    sites = nights.group_by("station_id").agg(pl.col("station_latitude").first())
    return frame.join(sites, on="station_id", how="inner").filter(
        pl.col("station_latitude").is_between(*CLAIM_BAND, closed="left")
    )


def _mean_ci(values: np.ndarray) -> tuple[float, float]:
    """Mean and a 95% interval. An interval needs two points; one is a number, not an estimate."""
    if len(values) < MIN_FOR_INTERVAL:
        return (float(values.mean()) if len(values) else float("nan"), float("nan"))
    return float(values.mean()), 1.96 * float(values.std(ddof=1)) / float(np.sqrt(len(values)))


def warming(source: str, variable: str, label: str) -> Warming:
    """One dataset's claim-band warming."""
    trends = _in_band(_trends(_yearly(source, variable)))
    mean, ci = _mean_ci(trends["trend"].to_numpy())
    return Warming(label=label, per_decade=mean, ci95=ci, stations=trends.height)


@lru_cache(maxsize=1)
def control() -> tuple[Warming, Warming, bool]:
    """Prediction 2: does the factual half reproduce the reanalysis already in the lake?

    Returns both warmings and whether the control passes. A failure means the two datasets describe
    different places, and the pre-registration says the whole comparison stops rather than being
    reported with a caveat.

    Cached because three callers gate on it and each call is two full scans of the driver panel.
    """
    reanalysis = warming(era5.SOURCE_ID, TEMPERATURE, "ERA5 reanalysis")
    factual = warming(attrici.SOURCE_ID, TEMPERATURE, "ISIMIP obsclim")
    gap = abs(factual.per_decade - reanalysis.per_decade)
    passes = gap <= CONTROL_TOLERANCE * (reanalysis.ci95 + factual.ci95)
    return reanalysis, factual, passes


def paired_removal() -> tuple[float, float]:
    """Warming ATTRICI removes, from the per-station paired difference.

    Paired, not a difference of means. Both scenarios come from the same 0.5-degree cells, so the
    per-station difference cancels almost all of the between-station spread, which is what an
    unpaired interval would be dominated by. The wider interval would understate a disagreement the
    pre-registration asks about.
    """
    factual = _trends(_yearly(attrici.SOURCE_ID, TEMPERATURE)).rename({"trend": "factual"})
    counter = _trends(_yearly(attrici.SOURCE_ID, COUNTERFACTUAL)).rename({"trend": "counter"})
    both = _in_band(factual.join(counter, on="station_id", how="inner"))
    differences = (both["factual"] - both["counter"]).to_numpy()
    return _mean_ci(differences)


class Attributed(NamedTuple):
    """What the second counterfactual attributes, and the terms behind it."""

    window: tuple[int, int]
    stations: int
    warming_removed: float
    warming_removed_ci95: float
    share_of_factual: float
    """Fraction of the factual trend the detrending removes. What DAMIP's `f` is compared to."""

    advance: float
    advance_ci95: float
    control_gap: float
    """How far obsclim lands from ERA5, in C/decade. What the stop condition was applied to."""


def attributed(per_degree: float, per_degree_ci95: float) -> Attributed | None:
    """The second counterfactual's answer, or None if its control did not pass.

    `S` is supplied rather than refitted here. The two attributions are meant to differ only in the
    warming term, so a second fit would make part of the gap between them a difference of method.
    """
    reanalysis, factual, passes = control()
    if not passes:
        log.warning(
            "ATTRICI control failed: obsclim %+.3f against ERA5 %+.3f C/decade",
            factual.per_decade,
            reanalysis.per_decade,
        )
        return None

    removed, removed_ci = paired_removal()
    advance = per_degree * removed
    # Relative errors in quadrature: S and the warming difference come from the same stations but
    # different quantities, so treating them as independent is the honest default.
    ci = abs(advance) * float(
        np.sqrt((per_degree_ci95 / per_degree) ** 2 + (removed_ci / removed) ** 2)
    )
    return Attributed(
        window=WINDOW,
        stations=factual.stations,
        warming_removed=removed,
        warming_removed_ci95=removed_ci,
        share_of_factual=removed / factual.per_decade,
        advance=advance,
        advance_ci95=ci,
        control_gap=abs(factual.per_decade - reanalysis.per_decade),
    )


def render() -> str:
    """The comparison, or the reason there is not one."""
    out: list[str] = []
    reanalysis, factual, passes = control()

    band = f"{CLAIM_BAND[0]}-{CLAIM_BAND[1]}N"
    out.append(f"June-July warming, {WINDOW[0]}-{WINDOW[1]}, within-station, {band}")
    out.append("")
    for item in (reanalysis, factual):
        out.append(
            f"  {item.label:<22} {item.per_decade:+.3f} +/- {item.ci95:.3f} C/decade"
            f"   ({item.stations} stations)"
        )

    gap = factual.per_decade - reanalysis.per_decade
    tolerance = CONTROL_TOLERANCE * (reanalysis.ci95 + factual.ci95)
    out += [
        "",
        f"CONTROL  obsclim - ERA5 = {gap:+.3f} against a combined interval of {tolerance:.3f}",
        f"         prediction 2 {'PASSES' if passes else 'FAILS'}",
    ]
    if not passes:
        out += [
            "",
            "The factual halves disagree, so the two datasets are describing different places and",
            "the counterfactual cannot be trusted either. Pre-registered as a stop condition: no",
            "comparison is reported from here.",
        ]
        return "\n".join(out)

    counterfactual = warming(attrici.SOURCE_ID, COUNTERFACTUAL, "ISIMIP counterclim")
    fitted = sensitivities()
    fitted_band = [item for item in fitted if CLAIM_BAND[0] <= item.latitude < CLAIM_BAND[1]]
    if not fitted_band:
        out.append("\nNo claim-band station has a fitted response, so there is no S to apply.")
        return "\n".join(out)

    per_degree, per_degree_ci = _mean_ci(np.array([item.per_degree for item in fitted_band]))
    observed, observed_ci = _mean_ci(np.array([item.observed_per_decade for item in fitted_band]))

    answer = attributed(per_degree, per_degree_ci)
    if answer is None:  # unreachable: the control passed above, and it is cached
        return "\n".join(out)

    out += [
        "",
        f"  {counterfactual.label:<22} {counterfactual.per_decade:+.3f}"
        f" +/- {counterfactual.ci95:.3f} C/decade",
        "",
        f"ATTRICI removes {answer.warming_removed:+.3f} +/-"
        f" {answer.warming_removed_ci95:.3f} C/decade of warming,"
        f" {answer.share_of_factual:.1%} of the factual trend",
        f"S = {per_degree:+.3f} +/- {per_degree_ci:.3f} days per degree (from phase2a_timing)",
        f"so the advance it attributes is {answer.advance:+.3f} +/-"
        f" {answer.advance_ci95:.3f} days/decade",
        f"against an observed {observed:+.3f} +/- {observed_ci:.3f}",
        "",
        "=" * 78,
        "the two counterfactuals",
        "=" * 78,
        "  DAMIP     f = 0.98 of the ensemble-mean forced warming -> -0.296 +/- 0.090 d/decade",
        f"  ATTRICI   {answer.share_of_factual:.0%} of each station's own trend"
        f" -> {answer.advance:+.3f} +/- {answer.advance_ci95:.3f} d/decade",
        "",
        "Not averaged, and not adjudicated. A ratio of ensemble-mean forced signals and a",
        "detrending of one cell's actual series are different quantities; the gap between them is",
        "the share of a local 25-year trend that does not move with the global mean. Mostly that",
        "is variability, but it also holds any forcing that does not scale with the global",
        "average, so the gap is an upper bound on the chance part rather than a reading of it.",
        "",
        "What neither establishes: both attribute the warming the animals tracked, through a",
        "response function fitted on observations. A confounder common to both temperature and",
        "passage date survives either one.",
        "",
        f"Window: this covers {WINDOW[1] - WINDOW[0] + 1} of the radar record's 31 years, because",
        f"counterclim ends in {attrici.LAST_YEAR}. It says nothing about 2020-2025.",
    ]
    return "\n".join(out)
