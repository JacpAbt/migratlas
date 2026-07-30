"""Occupied temperature against available temperature: did an animal keep its niche or its place?

Pre-registered in docs/methods/phase2a-thermal.md. The first testable link of the trophic pathway
in phase2a-design.md, and the one needing no new source -- FISHGLOB records a temperature at the
haul, measured by the same gear that caught the fish.

The pairing is the whole method. An occupied-temperature trend on its own says nothing: holding a
constant temperature in an ocean that did not warm is not tracking, it is stillness. So every
occupied trend is reported against the *available* trend over the same footprint, and the ratio of
the two is what distinguishes an animal that moved to keep its water from one that stayed and
warmed.
"""

import logging
from typing import Final, NamedTuple

import numpy as np
import polars as pl

log = logging.getLogger(__name__)

# Bottom temperature, because these are demersal surveys and the bottom is the water the fish are
# in. Surface over a fish at 200 m is a different water mass, and is carried only as a check.
BOTTOM: Final = "sea_bottom_temperature"
SURFACE: Final = "sea_surface_temperature"

# A survey-year needs this share of its hauls to carry a temperature before its mean is used.
# Missingness is not random -- coverage runs from 99.8% to 0% across surveys -- so a year assembled
# from a tenth of its hauls is a different sample, not a noisier one.
MIN_TEMPERATURE_SHARE: Final = 0.5

MIN_YEARS: Final = 15


class Trend(NamedTuple):
    """A least-squares trend per decade, with its standard error and the years behind it."""

    per_decade: float
    stderr: float
    years: int

    @property
    def distinguishable(self) -> bool:
        """Whether the trend is separable from zero at roughly 95%.

        The tracking index divides by this, so "is there any thermal forcing to respond to" has
        to be answered before the ratio is formed. A magnitude floor was the first implementation
        and it was wrong: 0.05 degC/decade is not a test of anything, and a survey squeaking over
        it produced a mean index of +1.23 with an interval of +/-0.70 -- the ratio exploding on a
        denominator that was itself indistinguishable from no warming at all.
        """
        return abs(self.per_decade) > 1.96 * self.stderr


def _trend(years: np.ndarray, values: np.ndarray) -> Trend | None:
    """Decadal trend with its standard error, or None if there is not enough to fit one."""
    usable = np.isfinite(values)
    if usable.sum() < MIN_YEARS:
        return None
    year = years[usable].astype(float)
    value = values[usable].astype(float)
    if np.ptp(year) == 0:
        return None

    slope, intercept = np.polyfit(year, value, 1)
    residual = value - (slope * year + intercept)
    degrees = value.size - 2
    if degrees <= 0:
        return None
    variance = float((residual**2).sum() / degrees) / float(((year - year.mean()) ** 2).sum())
    return Trend(
        per_decade=float(slope) * 10.0,
        stderr=float(np.sqrt(variance)) * 10.0,
        years=int(usable.sum()),
    )


def occupied(cells: pl.DataFrame, temperature: str = BOTTOM) -> pl.DataFrame:
    """CPUE-weighted mean temperature of the cells a species was caught in, per year.

    Weighted the same way the distribution centroids are, so occupied temperature and occupied
    latitude are the same kind of number and can be read against each other.
    """
    if temperature not in cells.columns:
        return pl.DataFrame()
    caught = cells.filter(pl.col("cpue") > 0, pl.col(temperature).is_not_null())
    if caught.is_empty():
        return pl.DataFrame()

    return (
        caught.group_by("taxon_key", "taxon_label", "year")
        .agg(
            ((pl.col(temperature) * pl.col("cpue")).sum() / pl.col("cpue").sum()).alias("occupied"),
            pl.len().alias("hauls"),
        )
        .sort("taxon_key", "year")
    )


def available(cells: pl.DataFrame, temperature: str = BOTTOM) -> pl.DataFrame:
    """Unweighted mean temperature over the footprint per year: the water on offer.

    Unweighted on purpose. This is the thermal environment the survey sampled, and weighting it by
    any species' catch would make it a property of that species rather than of the ocean.

    Also returns the share of hauls carrying a temperature, and the mean day of year -- the second
    because a survey that drifted later in the season samples warmer water for that reason alone,
    which is a confound rather than a signal.
    """
    if temperature not in cells.columns:
        return pl.DataFrame()

    hauls = cells.select(
        "year",
        "site_id",
        pl.col(temperature).alias("temperature"),
        pl.col("period_start").dt.ordinal_day().alias("doy"),
    ).unique(subset=["year", "site_id"])

    return (
        hauls.group_by("year")
        .agg(
            pl.col("temperature").mean().alias("available"),
            pl.col("temperature").is_not_null().mean().alias("share"),
            pl.col("doy").mean().alias("mean_doy"),
            pl.len().alias("hauls"),
        )
        .filter(pl.col("share") >= MIN_TEMPERATURE_SHARE)
        .sort("year")
    )


class Tracking(NamedTuple):
    """One species' thermal response in one survey, against that survey's ambient."""

    taxon_key: int
    taxon_label: str
    occupied_per_decade: float
    ambient_per_decade: float
    held: float
    """1 - occupied/ambient. Near 1 is tracking, near 0 is staying, below 0 is moving warmer.

    Not called `index`: a NamedTuple field of that name silently overrides `tuple.index`,
    which mypy caught and which would have broken any caller that used it.
    """
    years: int


def tracking(
    occupied_series: pl.DataFrame, available_series: pl.DataFrame
) -> tuple[list[Tracking], Trend | None]:
    """Per-species tracking indices, and the survey's ambient trend they are measured against.

    Returns an empty list if the ambient trend is absent or too small to divide by: a survey whose
    water did not warm poses no thermal question, and saying so is an answer rather than a gap.
    """
    if available_series.is_empty() or occupied_series.is_empty():
        return [], None

    ambient = _trend(
        available_series["year"].to_numpy(),
        available_series["available"].to_numpy().astype(float),
    )
    if ambient is None or not ambient.distinguishable:
        return [], ambient

    # Restricted to the years the ambient itself is defined for, so a species is never credited
    # with tracking across a year whose thermal environment is unknown.
    usable_years = set(available_series["year"].to_list())
    results: list[Tracking] = []
    for (key, label), group in occupied_series.group_by(["taxon_key", "taxon_label"]):
        series = group.filter(pl.col("year").is_in(usable_years)).sort("year")
        fitted = _trend(series["year"].to_numpy(), series["occupied"].to_numpy().astype(float))
        if fitted is None:
            continue
        results.append(
            Tracking(
                taxon_key=int(key),
                taxon_label=str(label),
                occupied_per_decade=fitted.per_decade,
                ambient_per_decade=ambient.per_decade,
                held=1.0 - (fitted.per_decade / ambient.per_decade),
                years=fitted.years,
            )
        )
    return results, ambient


def date_drift(available_series: pl.DataFrame) -> Trend | None:
    """Trend in the survey's mean sampling day of year, in days per decade.

    Confound number one from the method note: a survey that moved later in the season samples
    warmer water whether or not the ocean warmed. Reported alongside every thermal trend so a
    reader can see whether the thermal signal is a calendar signal.
    """
    if available_series.is_empty():
        return None
    return _trend(
        available_series["year"].to_numpy(),
        available_series["mean_doy"].to_numpy().astype(float),
    )
