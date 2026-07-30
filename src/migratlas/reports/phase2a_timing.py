"""Phase 2a, second link: does warming explain the autumn advance?

Pre-registered in docs/methods/phase2a-timing.md, including the three predictions, before the
temperature was fetched.

The test is arithmetic rather than a coefficient. Sensitivity S (days per degC, fitted within each
station across years) times warming W (degC per decade, from ERA5) should reproduce the observed
advance A (days per decade, from Phase 1a) if the advance is thermally driven. S x W is the
explained share, and the honest halfway house to the DAMIP counterfactual that phase2a-design
reserves the causal claim for.
"""

import logging
from typing import Final, NamedTuple

import numpy as np
import polars as pl

from migratlas.drivers import era5, narr
from migratlas.drivers.schema import DRIVER_SAMPLES
from migratlas.evidence import EvidenceType, spec_for
from migratlas.lake.reader import scan_dataset
from migratlas.metrics.phenology import passage_quantiles
from migratlas.reports.phase1 import (
    AUTUMN,
    LATITUDE_BANDS,
    MIN_COVERAGE,
    MIN_NIGHTS,
    MIN_YEARS,
    load_conus_nights,
)
from migratlas.reports.phase1_robustness import FLEET_MIDPOINT_YEAR

log = logging.getLogger(__name__)

# June and July. Before the August-November passage window and not touching it: a predictor that
# overlapped the response would partly be the response.
PRE_SEASON: Final[tuple[int, ...]] = (6, 7)

# Where the surviving Phase 1a claim lives, and so the only band an attribution is claimed for.
CLAIM_BAND: Final[tuple[int, int]] = (37, 50)

TEMPERATURE: Final = "air_temperature_2m"


class Sensitivity(NamedTuple):
    """One station's response of passage date to its own year-to-year conditions."""

    station_id: str
    latitude: float
    driver_correlation: float
    """Correlation between the two predictors at this station.

    Confound 1 from the method note: warm years are not meteorologically independent of windy ones,
    and where the two are collinear beyond separating, the honest output is to say so rather than
    to credit one with the other's work.
    """
    per_degree: float
    """Days of passage-date shift per degC of pre-season warmth. Negative is earlier."""
    per_wind: float
    """Days per m/s of wind support, so the thermal term is not credited with the wind's work."""
    warming_per_decade: float
    observed_per_decade: float
    years: int

    @property
    def explained_per_decade(self) -> float:
        """S x W: the advance the fitted response predicts from the observed warming."""
        return self.per_degree * self.warming_per_decade


def pre_season_temperature() -> pl.DataFrame:
    """Mean June-July 2 m temperature per station per year."""
    return (
        scan_dataset(DRIVER_SAMPLES.name, source_id=era5.SOURCE_ID)
        .filter(
            pl.col("variable") == TEMPERATURE,
            pl.col("period_start").dt.month().is_in(PRE_SEASON),
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


def wind_support() -> pl.DataFrame:
    """Mean autumn-window wind support per station per year, in m/s.

    Support is the wind's component along the station's own mean autumn heading, so a station whose
    migrants leave south-west is not scored against a southward reference. The heading comes from
    the radar's own reflectivity-weighted direction, which is the only estimate of where the
    animals were actually going.
    """
    nights = load_conus_nights(quantity="reflectivity_traffic").filter(
        pl.col("timestamp").dt.ordinal_day().is_between(AUTUMN.start_doy, AUTUMN.end_doy),
        pl.col("coverage_fraction") >= MIN_COVERAGE,
        pl.col("direction_deg").is_not_null(),
        pl.col("magnitude") > 0,
    )
    if nights.is_empty():
        return pl.DataFrame()

    # Traffic-weighted mean heading per station, as a unit vector so a circular mean is correct.
    headings = (
        nights.with_columns(
            east=pl.col("direction_deg").radians().sin() * pl.col("magnitude"),
            north=pl.col("direction_deg").radians().cos() * pl.col("magnitude"),
        )
        .group_by("station_id")
        .agg(pl.col("east").sum(), pl.col("north").sum())
        .with_columns(
            norm=(pl.col("east") ** 2 + pl.col("north") ** 2).sqrt(),
        )
        .filter(pl.col("norm") > 0)
        .with_columns(
            heading_east=pl.col("east") / pl.col("norm"),
            heading_north=pl.col("north") / pl.col("norm"),
        )
        .select("station_id", "heading_east", "heading_north")
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
    if u_column not in winds.columns:
        return pl.DataFrame()

    autumn_nights = nights.select(
        "station_id", date=pl.col("timestamp").dt.date(), year=pl.col("timestamp").dt.year()
    )
    return (
        autumn_nights.join(winds, on=("station_id", "date"), how="inner")
        .join(headings, on="station_id", how="inner")
        .with_columns(
            support=pl.col(u_column) * pl.col("heading_east")
            + pl.col(v_column) * pl.col("heading_north")
        )
        .group_by("station_id", "year")
        .agg(pl.col("support").mean().alias("support"))
    )


def _fit(design: np.ndarray, response: np.ndarray) -> np.ndarray | None:
    if np.linalg.matrix_rank(design) < design.shape[1]:
        return None
    coefficients, *_ = np.linalg.lstsq(design, response, rcond=None)
    return np.asarray(coefficients, dtype=float)


def sensitivities() -> list[Sensitivity]:
    """Per station: the thermal and wind response of passage date, and the station's warming."""
    nights = load_conus_nights(quantity="reflectivity_traffic")
    quantiles = passage_quantiles(
        nights,
        spec_for(EvidenceType.FLUX),
        seasons=[AUTUMN],
        quantiles=[0.5],
        min_coverage=MIN_COVERAGE,
        min_observations=MIN_NIGHTS,
    ).filter(pl.col("q50_doy").is_not_null())

    sites = nights.group_by("station_id").agg(pl.col("station_latitude").first())
    panel = (
        quantiles.join(pre_season_temperature(), on=("station_id", "year"), how="inner")
        .join(wind_support(), on=("station_id", "year"), how="left")
        .join(sites, on="station_id", how="inner")
    )

    results: list[Sensitivity] = []
    for (station,), group in panel.group_by(["station_id"]):
        series = group.drop_nulls(["q50_doy", "temperature", "support"]).sort("year")
        if series.height < MIN_YEARS:
            continue

        years = series["year"].to_numpy().astype(float)
        temperature = series["temperature"].to_numpy().astype(float)
        support = series["support"].to_numpy().astype(float)
        passage = series["q50_doy"].to_numpy().astype(float)
        post = (years >= FLEET_MIDPOINT_YEAR).astype(float)

        columns = [np.ones_like(years), temperature, support]
        if 0 < post.sum() < post.size:
            columns.append(post)
        fitted = _fit(np.column_stack(columns), passage)
        if fitted is None:
            continue

        warming = _fit(np.column_stack([np.ones_like(years), years]), temperature)
        observed = _fit(np.column_stack([np.ones_like(years), years]), passage)
        if warming is None or observed is None:
            continue

        results.append(
            Sensitivity(
                station_id=str(station),
                latitude=float(series["station_latitude"][0]),
                driver_correlation=float(np.corrcoef(temperature, support)[0, 1]),
                per_degree=float(fitted[1]),
                per_wind=float(fitted[2]),
                warming_per_decade=float(warming[1]) * 10.0,
                observed_per_decade=float(observed[1]) * 10.0,
                years=series.height,
            )
        )
    return results


def _mean_ci(values: np.ndarray) -> tuple[float, float]:
    if values.size == 0:
        return (float("nan"), float("nan"))
    ci = 1.96 * float(values.std(ddof=1)) / np.sqrt(values.size) if values.size > 1 else 0.0
    return (float(values.mean()), ci)


def render() -> str:
    out = [
        "Phase 2a, second link -- does warming explain the autumn advance?",
        "=" * 78,
        "Pre-registered in docs/methods/phase2a-timing.md: the June-July pre-season window, the",
        "within-station design, wind support as a co-predictor and the S x W arithmetic were all",
        "fixed before the temperature was fetched.",
    ]

    fitted = sensitivities()
    if not fitted:
        out.append(
            "\nNo station had a passage series, a pre-season temperature and a wind support "
            "series together. Run `make ingest-era5` and `make ingest-narr` first."
        )
        return "\n".join(out)

    frame = pl.DataFrame(
        {
            "station_id": [item.station_id for item in fitted],
            "latitude": [item.latitude for item in fitted],
            "per_degree": [item.per_degree for item in fitted],
            "per_wind": [item.per_wind for item in fitted],
            "warming": [item.warming_per_decade for item in fitted],
            "observed": [item.observed_per_decade for item in fitted],
            "explained": [item.explained_per_decade for item in fitted],
            "years": [item.years for item in fitted],
            "driver_correlation": [item.driver_correlation for item in fitted],
        }
    )
    out.append(f"\n{frame.height} stations with at least {MIN_YEARS} usable autumns.")

    out += ["", "=" * 78, "by latitude band", "=" * 78]
    header = (
        f"  {'band':<10} {'n':>3}  {'S d/degC':>12}  {'W degC/dec':>12}  "
        f"{'S x W':>12}  {'observed':>12}"
    )
    out.append(header)
    bands = [*LATITUDE_BANDS, CLAIM_BAND]
    for low, high in bands:
        band = frame.filter(pl.col("latitude").is_between(low, high, closed="left"))
        if band.is_empty():
            continue
        pieces = []
        for column in ("per_degree", "warming", "explained", "observed"):
            mean, ci = _mean_ci(band[column].to_numpy().astype(float))
            pieces.append(f"{mean:+7.3f}+-{ci:.2f}")
        marker = "  <- the claim" if (low, high) == CLAIM_BAND else ""
        out.append(f"  {low}-{high}N{'':<4} {band.height:>3}  " + "  ".join(pieces) + marker)

    claim = frame.filter(pl.col("latitude").is_between(*CLAIM_BAND, closed="left"))
    if not claim.is_empty():
        out += ["", "=" * 78, f"the claim band, {CLAIM_BAND[0]}-{CLAIM_BAND[1]}N", "=" * 78]
        explained, explained_ci = _mean_ci(claim["explained"].to_numpy().astype(float))
        observed, observed_ci = _mean_ci(claim["observed"].to_numpy().astype(float))
        sensitivity, sensitivity_ci = _mean_ci(claim["per_degree"].to_numpy().astype(float))
        warming, warming_ci = _mean_ci(claim["warming"].to_numpy().astype(float))
        wind, wind_ci = _mean_ci(claim["per_wind"].to_numpy().astype(float))
        collinear, collinear_ci = _mean_ci(claim["driver_correlation"].to_numpy().astype(float))

        out += [
            f"\n  sensitivity S    {sensitivity:+.3f} +/- {sensitivity_ci:.3f} days per degC",
            f"  warming W        {warming:+.3f} +/- {warming_ci:.3f} degC per decade",
            f"  wind response    {wind:+.3f} +/- {wind_ci:.3f} days per m/s of support",
            f"  explained S x W  {explained:+.3f} +/- {explained_ci:.3f} days per decade",
            f"  observed A       {observed:+.3f} +/- {observed_ci:.3f} days per decade",
            f"  corr(temp, wind) {collinear:+.3f} +/- {collinear_ci:.3f}  -- how separable the "
            "two predictors are",
        ]
        if observed != 0:
            share = explained / observed
            out.append(f"\n  S x W accounts for {share:.0%} of the observed advance.")
        out.append(
            "  A share near 1 would mean warming is sufficient in magnitude; a small share means "
            "\n  the response function is real and is not the explanation."
        )

    out += [
        "",
        "=" * 78,
        "This is a response function and an order-of-magnitude check, not a causal claim. The",
        "causal step is the CMIP6 DAMIP counterfactual in phase2a-design.md, which this does not",
        "attempt. A local June-July temperature is also a crude stand-in for conditions across a",
        "whole flyway, which bounds how much S could ever explain.",
    ]
    return "\n".join(out)
