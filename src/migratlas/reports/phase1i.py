"""Phase 1i — does a climate response measured in one place carry to another?

Pre-registered in `docs/methods/phase1i-transfer.md`. Every range-shift projection in the literature
assumes climate responses transfer between regions and realms; almost nobody tests it, because
almost nobody has three of them measured under one audit. This project does, and `coverage-bias`
has published a promise to go and check.

The common currency is the **thermal tracking ratio**: the observed shift over the shift that fully
following the local warming would have required. One is perfect tracking, zero is no response,
negative is movement against the warming. It is dimensionless *physically* rather than
statistically -- note §2 rejects standardising each realm by its own standard deviation, because two
systems with identical biology and different measurement noise would then report different
sensitivities.

The three legs are reduced here and graded in `grade`, which touches no lake. The split is the same
one `phase1h.from_fixes` makes and for the same reason: the arithmetic that decides the claim has to
be testable against inputs whose answer is known in advance.
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np
import polars as pl
from scipy import stats

if TYPE_CHECKING:
    from datetime import datetime

from migratlas.drivers import era5
from migratlas.drivers.schema import DRIVER_SAMPLES
from migratlas.lake.identifiers import cell_site_id
from migratlas.lake.reader import scan_dataset
from migratlas.metrics import range as range_metrics
from migratlas.reports import phase1b, phase1e, phase2a_timing

log = logging.getLogger(__name__)

AERIAL: Final = "aerial-north"
MARINE: Final = "marine-north"
TERRESTRIAL: Final = "terrestrial-south"

# Note amendment, rule one: the numerator is a latitudinal displacement, so the test only applies
# where poleward and cooler coincide.
MIN_LATITUDINAL_SHARE: Final = 0.5

# A survey too small or too short to carry a warming trend at all.
MIN_HAULS: Final = 500
MIN_SURVEY_YEARS: Final = 15

# Note §1: the southern claim is about the community, and a species in a handful of cells has a CTI
# that is about those cells.
MIN_CELLS: Final = 30

SOUTHERN_EPOCHS: Final = (range(1987, 1992), range(2008, 2013))

# Mid-month day of year. The aerial conversion needs a date for each monthly mean, and the 15th is
# the honest one -- a monthly mean is not the month's first day, which is what a naive stamp gives.
MID_MONTH: Final[dict[int, int]] = {6: 166, 7: 196, 9: 258, 10: 288, 11: 319}
SUMMER_MONTHS: Final = (6, 7)
AUTUMN_MONTHS: Final = (9, 10, 11)

# Below this the seasonal fit is noise, and dividing by it produces the wild ratios note §5
# stops on.
MIN_COOLING: Final = 0.01
MIN_SHARED_YEARS: Final = 15

COUPLING_NOISE: Final = 1e-9
"""An uncoupled station regresses to zero only up to floating-point luck.

The same synthetic uncoupled station fitted a slope that was non-positive on one machine and
+2.5e-16 on CI's BLAS, and the positive one slipped a ``<= 0`` guard into dividing `per_degree`
by noise -- a ratio of -3.9e15. Every physically coupled station sits orders of magnitude above
this floor, so it cannot move a published ratio; it only closes the sign-of-noise hole.
"""

BOOTSTRAP: Final = 2000
SEED: Final = 20260807
"""Fixed, because a published interval that moves between builds is not an interval."""

QUARTILES: Final = (25, 75)


@dataclass(frozen=True, slots=True)
class Leg:
    """One realm's tracking-ratio distribution.

    Note §3 keeps the whole distribution rather than a centre: with three pooled numbers, "fit on
    two and predict the third" is arithmetic over two values with no degrees of freedom.
    """

    realm: str
    tracking: np.ndarray

    @property
    def n(self) -> int:
        return int(self.tracking.size)

    @property
    def median(self) -> float:
        return float(np.median(self.tracking))

    @property
    def quartiles(self) -> tuple[float, float]:
        low, high = np.percentile(self.tracking, QUARTILES)
        return float(low), float(high)

    @property
    def iqr(self) -> float:
        low, high = self.quartiles
        return high - low

    @property
    def median_se(self) -> float:
        """Bootstrapped, because none of these ratio distributions is normal.

        The closed form `1.253 s/sqrt(n)` assumes one, and the marine leg's deciles run from -1.9
        to +2.6.
        """
        rng = np.random.default_rng(SEED)
        draws = rng.integers(0, self.n, size=(BOOTSTRAP, self.n))
        return float(np.std(np.median(self.tracking[draws], axis=1), ddof=1))


def marine() -> Leg:
    """Latitudinal shift over the isotherm's own velocity, per species and survey.

    Both numerator and denominator come from one instrument: FISHGLOB carries a temperature at the
    haul, so the survey measures the water it fished in.
    """
    temperature = (
        scan_dataset("driver_samples", source_id="fishglob")
        .filter(pl.col("variable") == "sea_bottom_temperature")
        .select(
            survey=pl.col("site_id").str.split(":").list.first(),
            latitude=pl.col("latitude"),
            longitude=pl.col("longitude"),
            year=pl.col("period_start").dt.year(),
            value=pl.col("value"),
        )
        .drop_nulls()
        .collect()
    )

    rows = []
    for (survey,), group in temperature.group_by(["survey"]):
        if group.height < MIN_HAULS or group["year"].n_unique() < MIN_SURVEY_YEARS:
            continue
        latitude = group["latitude"].to_numpy()
        # Longitude scaled to distance at the survey's own latitude, so the two gradient components
        # are in the same units before their magnitude is taken.
        design = np.column_stack(
            [
                np.ones(group.height),
                latitude,
                group["longitude"].to_numpy() * np.cos(np.deg2rad(latitude.mean())),
                group["year"].to_numpy().astype(float),
            ]
        )
        fit, *_ = np.linalg.lstsq(design, group["value"].to_numpy(), rcond=None)
        gradient = float(np.hypot(fit[1], fit[2]))
        if not gradient:
            continue
        # Climate velocity: warming rate over the magnitude of the spatial gradient. Dividing by
        # `dT/dlat` alone assumes isotherms travel due north and gave BITS-1 -44 degrees per decade.
        velocity = (fit[3] * 10) / gradient
        rows.append(
            {
                "survey_unit": survey,
                "velocity": velocity,
                "latitudinal_share": abs(fit[1]) / gradient,
                # Rule two, against each survey's own extent so there is no threshold to
                # have chosen.
                "crosses": bool(abs(velocity) > float(latitude.max() - latitude.min())),
            }
        )

    isotherms = pl.DataFrame(rows)
    usable = isotherms.filter(
        (pl.col("latitudinal_share") > MIN_LATITUDINAL_SHARE) & ~pl.col("crosses")
    )
    log.info("marine: %d surveys measured, %d usable", isotherms.height, usable.height)

    _, pooled, _ = phase1b.analyse(range_metrics.to_cells(phase1b.survey_unit(phase1b.load())))
    joined = pooled.join(
        usable.select("survey_unit", "velocity"), on="survey_unit", how="inner"
    ).with_columns(tracking=pl.col("per_decade") / pl.col("velocity"))
    return Leg(MARINE, joined["tracking"].to_numpy())


def terrestrial() -> Leg:
    """Community temperature index against the footprint's own warming, per species.

    The cell's thermal position is fixed at its first-epoch temperature, so a species' CTI moves
    only when the animals move. Letting each epoch carry its own temperature would fold the warming
    into the answer and manufacture apparent tracking.
    """
    cells = phase1e.footprint(phase1e.EPOCH_2)
    cells = cells.with_columns(
        site_id=pl.Series(
            [
                cell_site_id(lat, lon)
                for lat, lon in cells.select("cell_lat", "cell_lon").iter_rows()
            ]
        )
    )

    def epoch_mean(years: range) -> pl.DataFrame:
        return (
            scan_dataset("driver_samples", source_id="era5_south")
            .filter(pl.col("period_start").dt.year().is_in(list(years)))
            .group_by("site_id")
            .agg(value=pl.col("value").mean())
            .collect()
        )

    first, second = SOUTHERN_EPOCHS
    grid = cells.join(epoch_mean(first).rename({"value": "first"}), on="site_id").join(
        epoch_mean(second).rename({"value": "second"}), on="site_id"
    )
    warming = float(np.mean((grid["second"] - grid["first"]).to_numpy()))
    log.info("terrestrial: %d cells, warming %+.4f degC", grid.height, warming)
    fixed = dict(zip(grid["site_id"].to_list(), grid["first"].to_list(), strict=True))

    def occupied(source_id: str, window: tuple[datetime, datetime]) -> pl.DataFrame:
        found = phase1e.detections(source_id, window, cells)
        found = found.with_columns(
            site_id=pl.Series(
                [
                    cell_site_id(lat, lon)
                    for lat, lon in found.select("cell_lat", "cell_lon").iter_rows()
                ]
            )
        )
        return found.filter(pl.col("k") > 0).select("taxon_key", "site_id").unique()

    def index(frame: pl.DataFrame) -> pl.DataFrame:
        return (
            frame.with_columns(value=pl.col("site_id").replace_strict(fixed, default=None))
            .group_by("taxon_key")
            .agg(cti=pl.col("value").mean(), cells=pl.len())
        )

    before = index(occupied("sabap1", phase1e.EPOCH_1)).rename({"cti": "before", "cells": "n1"})
    after = index(occupied("sabap2", phase1e.EPOCH_2)).rename({"cti": "after", "cells": "n2"})
    paired = (
        before.join(after, on="taxon_key")
        .filter((pl.col("n1") >= MIN_CELLS) & (pl.col("n2") >= MIN_CELLS))
        .with_columns(tracking=-(pl.col("after") - pl.col("before")) / warming)
    )
    return Leg(TERRESTRIAL, paired["tracking"].to_numpy())


def aerial() -> Leg:
    """Passage-date sensitivity over the date the thermal calendar itself moved, per station.

    Note §5 registered a stop condition here because turning a date shift into a fraction of the
    warming needs a seasonal slope. It needs two measured quantities rather than one guessed
    constant, since the driver is summer temperature and the response is an autumn date:

    - the coupling, degrees of autumn per degree of summer, regressed at each station;
    - the autumn cooling rate in degrees per day, from the monthly means themselves.

    Both come from ERA5, so no literature constant enters and the conversion can be re-run under a
    different autumn window -- which is exactly what the stop condition asks for.
    """
    monthly = (
        scan_dataset(DRIVER_SAMPLES.name, source_id=era5.SOURCE_ID)
        .filter(pl.col("variable") == phase2a_timing.TEMPERATURE)
        .select(
            site_id="site_id",
            value="value",
            year=pl.col("period_start").dt.year(),
            month=pl.col("period_start").dt.month(),
        )
        .collect()
    )
    low, high = phase2a_timing.CLAIM_BAND
    band = [s for s in phase2a_timing.sensitivities() if low <= s.latitude <= high]
    log.info("aerial: %d stations in the claim band", len(band))
    return Leg(AERIAL, np.array(_aerial_ratios(monthly, band, AUTUMN_MONTHS)))


def _aerial_ratios(
    monthly: pl.DataFrame, band: list[phase2a_timing.Sensitivity], autumn: tuple[int, ...]
) -> list[float]:
    """The per-station ratios for one choice of autumn window. Separated so §5 can vary it."""
    ratios = []
    for station in band:
        at = monthly.filter(pl.col("site_id") == station.station_id)
        if at.is_empty():
            continue

        def season(months: tuple[int, ...], frame: pl.DataFrame = at) -> pl.DataFrame:
            return (
                frame.filter(pl.col("month").is_in(list(months)))
                .group_by("year")
                .agg(value=pl.col("value").mean())
            )

        shared = season(autumn).join(season(SUMMER_MONTHS), on="year", suffix="_summer")
        if shared.height < MIN_SHARED_YEARS:
            continue
        coupling = float(
            np.polyfit(shared["value_summer"].to_numpy(), shared["value"].to_numpy(), 1)[0]
        )

        by_month = (
            at.filter(pl.col("month").is_in(list(autumn)))
            .group_by("month")
            .agg(value=pl.col("value").mean())
        )
        if by_month.height < 2:  # noqa: PLR2004 -- a slope needs two points
            continue
        days = np.array([MID_MONTH[m] for m in by_month["month"].to_list()], dtype=float)
        cooling = float(np.polyfit(days, by_month["value"].to_numpy(), 1)[0])
        if cooling >= -MIN_COOLING or coupling <= COUPLING_NOISE:
            continue

        # Days the thermal calendar moves per degree of summer warmth.
        ratios.append(station.per_degree / (coupling / abs(cooling)))
    return ratios


def aerial_window_spread() -> float:
    """How far the aerial median moves across reasonable autumn windows. Note §5's stop condition.

    Withdraw the leg above 0.2. Recomputed on every build rather than recorded once, because the
    condition is only meaningful if it can still fire.
    """
    monthly = (
        scan_dataset(DRIVER_SAMPLES.name, source_id=era5.SOURCE_ID)
        .filter(pl.col("variable") == phase2a_timing.TEMPERATURE)
        .select(
            site_id="site_id",
            value="value",
            year=pl.col("period_start").dt.year(),
            month=pl.col("period_start").dt.month(),
        )
        .collect()
    )
    low, high = phase2a_timing.CLAIM_BAND
    band = [s for s in phase2a_timing.sensitivities() if low <= s.latitude <= high]
    medians = [
        float(np.median(_aerial_ratios(monthly, band, window)))
        for window in ((9, 10, 11), (9, 10), (10, 11))
    ]
    return max(medians) - min(medians)


@dataclass(frozen=True, slots=True)
class Pair:
    """Two realms, and whether their tracking distributions can be told apart at all."""

    left: str
    right: str
    gap: float
    p_adjusted: float

    @property
    def differ(self) -> bool:
        return self.p_adjusted < 0.05  # noqa: PLR2004 -- the registered threshold


@dataclass(frozen=True, slots=True)
class HoldOut:
    """One realm predicted from the other two, scored the three ways note §3 registered."""

    realm: str
    predicted: float
    actual: float
    error: float
    median_se: float
    iqr_ratio: float
    """Predicted spread over observed. One would be right."""

    coverage: float
    """Share of the held-out realm inside the prediction's interquartile range.

    0.5 would be right.
    """

    @property
    def transfers(self) -> bool:
        """Note §4 prediction 2, graded exactly as registered.

        The criterion is n-dependent and the results section says so: marine fails here on an error
        of 0.056 while its coverage lands at 49.7% against a target of 50%. Left as registered
        because moving the goalposts after seeing the numbers is what the convention exists to stop.
        """
        return self.error <= self.median_se


@dataclass(frozen=True, slots=True)
class Transfer:
    """Every registered prediction, computed from the three distributions."""

    legs: tuple[Leg, ...]
    kruskal_p: float
    pairs: tuple[Pair, ...]
    held_out: tuple[HoldOut, ...]

    @property
    def realms_disagree(self) -> bool:
        """Note §4 prediction 1."""
        return self.kruskal_p < 0.05  # noqa: PLR2004 -- the registered threshold

    @property
    def indistinguishable(self) -> tuple[Pair, ...]:
        """The pairs the omnibus test hides. This is where the actual result lives."""
        return tuple(pair for pair in self.pairs if not pair.differ)

    @property
    def worst(self) -> HoldOut:
        """Note §4 prediction 4 predicted this would be the marine realm. It is not."""
        return max(self.held_out, key=lambda held: held.error)


def grade(legs: tuple[Leg, ...]) -> Transfer:
    """The whole test, over any set of legs. Reads no lake, so its answers can be known up front."""
    omnibus = stats.kruskal(*[leg.tracking for leg in legs])

    raw = [
        (left, right, float(stats.mannwhitneyu(left.tracking, right.tracking).pvalue))
        for index, left in enumerate(legs)
        for right in legs[index + 1 :]
    ]
    # Holm, so three pairwise tests do not buy a result the omnibus did not support.
    order = sorted(range(len(raw)), key=lambda i: raw[i][2])
    adjusted: list[Pair] = []
    for rank, i in enumerate(order):
        left, right, p = raw[i]
        adjusted.append(
            Pair(
                left=left.realm,
                right=right.realm,
                gap=abs(left.median - right.median),
                p_adjusted=min(1.0, p * (len(raw) - rank)),
            )
        )

    held_out = []
    for leg in legs:
        # Pooled rather than averaged: note §3 predicts a distribution from two distributions, and
        # a mean of two medians would throw away the spread the prediction is scored on.
        train = np.concatenate([other.tracking for other in legs if other.realm != leg.realm])
        low, high = (float(v) for v in np.percentile(train, QUARTILES))
        held_out.append(
            HoldOut(
                realm=leg.realm,
                predicted=float(np.median(train)),
                actual=leg.median,
                error=abs(float(np.median(train)) - leg.median),
                median_se=leg.median_se,
                iqr_ratio=(high - low) / leg.iqr,
                coverage=float(((leg.tracking >= low) & (leg.tracking <= high)).mean()),
            )
        )

    return Transfer(
        legs=legs,
        kruskal_p=float(omnibus.pvalue),
        pairs=tuple(adjusted),
        held_out=tuple(held_out),
    )


def summarise() -> Transfer:
    """The three legs from the lake, graded."""
    return grade((aerial(), marine(), terrestrial()))
