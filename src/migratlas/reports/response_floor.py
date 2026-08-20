"""How much of the passage-date wobble is even in principle explainable, and does pooling help?

Every modelling attempt so far -- Phase 3a, the 3d rehearsal, Phase 3f -- took the response as given
and hunted for better drivers. None of them asked whether the response is quiet enough to predict at
all. If the *measurement* of a station's passage date is noisier than its year-to-year signal, no
driver can ever explain it and the ceiling is the instrument rather than the ecology. That is a
different diagnosis with a different remedy, and it is cheap to bound.

Two measurements, and together they answer one question.

**The per-station bound.** Two radars a hundred and fifty kilometres apart see very nearly the same
migration in the same autumn, so their year-by-year disagreement is mostly measurement error. Half
their difference variance is therefore an *upper* bound on one station's error -- upper, because
genuine spatial variation over that distance inflates it. Which makes the implied explainable share
a *lower* bound.

**The pooled reliability.** Averaging stations into regions should cancel independent error while
leaving shared signal -- but only if the signal really is shared. If each station's year-to-year
movement is its own, pooling averages the signal away too and buys nothing. So this measures rather
than assumes, by splitting each region's stations into disjoint halves and correlating the two
halves' year series. Spearman-Brown scales that from a half-region to the whole.

Dividing a per-station error by the root of the station count would have been the easy route and
would have flattered the answer, because errors at neighbouring radars are not independent -- the
same weather systems and the same hardware generations pass through both.

Regions are the project's own vocabulary, `phase1.FLYWAYS` crossed with `phase1.LATITUDE_BANDS`,
rather than clusters invented here, so the result is not a statement about a partition somebody
tuned until it looked good.

This characterises the response variable. It reads no driver and touches no era split, which is why
it can run after Phase 3f spent the aerial test era.
"""

import logging
from dataclasses import dataclass
from typing import Final

import numpy as np
import polars as pl

from migratlas.constants import EARTH_KM, MIN_COVERAGE, MIN_NIGHTS
from migratlas.evidence import EvidenceType, spec_for
from migratlas.metrics.phenology import passage_quantiles
from migratlas.reports.phase1 import AUTUMN, FLYWAYS, LATITUDE_BANDS, SPRING, load_conus_nights

log = logging.getLogger(__name__)

NEIGHBOUR_KM: Final = 150.0
"""How close two stations must be to count as seeing the same migration. Wide enough to find pairs
across a network with roughly 200 km spacing, narrow enough that the two really do share a night."""

MIN_STATIONS: Final = 4
"""Fewest stations a region needs for a half-split to mean anything."""

MIN_YEARS: Final = 15
"""Phase 1's own floor, so a series here is a series there."""

SPLITS: Final = 200
SEED: Final = 20260820
NULL_SEED: Final = 20260821
"""The null draws from its own generator, so adding or resizing the null cannot move a measurement.

Learned in Phase 3f, where a shared generator consumed in traversal order made a published null
irreproducible. Here the same mistake was milder and no more acceptable: interleaving the null
into the measurement's generator moved the autumn ceiling from 65% to 63% with no data changing.
"""


def great_circle_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle kilometres between two positions in degrees.

    The scalar twin of `phase1h._haversine`, which is a polars expression and cannot be called on a
    pair of floats. Two call shapes for one formula rather than two formulas: both take their radius
    from `constants.EARTH_KM`, so the thing that could actually drift cannot.
    """
    first, second = np.radians(lat1), np.radians(lat2)
    delta_lat, delta_lon = second - first, np.radians(lon2 - lon1)
    inner = np.sin(delta_lat / 2) ** 2 + np.cos(first) * np.cos(second) * np.sin(delta_lon / 2) ** 2
    return float(2 * EARTH_KM * np.arcsin(np.sqrt(inner)))


def region_of(latitude: float, longitude: float) -> str | None:
    """Which flyway-and-band a station falls in, or None if it falls outside either."""
    flyway = next((name for name, west, east in FLYWAYS if west <= longitude < east), None)
    band = next((f"{low}-{high}N" for low, high in LATITUDE_BANDS if low <= latitude < high), None)
    return f"{flyway} {band}" if flyway and band else None


def pooled_series(members: list[dict[int, float]], years: list[int]) -> np.ndarray:
    """Mean passage date across a set of stations per year, NaN where none of them reported."""
    out = []
    for year in years:
        values = [member[year] for member in members if year in member]
        out.append(float(np.mean(values)) if values else np.nan)
    return np.array(out)


def split_half_reliability(
    members: list[dict[int, float]], rng: np.random.Generator, *, splits: int = SPLITS
) -> float:
    """Spearman-Brown reliability of a region's pooled series, from random disjoint half-splits.

    Returns the share of the pooled series' variance that is shared signal rather than noise, which
    is the ceiling on what any driver could ever explain. NaN where no split had enough shared years
    or where a half never moved.
    """
    years = sorted({year for member in members for year in member})
    correlations = []
    for _ in range(splits):
        order = rng.permutation(len(members))
        half = len(members) // 2
        first = pooled_series([members[i] for i in order[:half]], years)
        second = pooled_series([members[i] for i in order[half : half * 2]], years)
        both = np.isfinite(first) & np.isfinite(second)
        if both.sum() < MIN_YEARS or first[both].std() == 0 or second[both].std() == 0:
            continue
        correlations.append(float(np.corrcoef(first[both], second[both])[0, 1]))
    if not correlations:
        return float("nan")
    correlation = float(np.mean(correlations))
    # Two halves correlating at r imply the whole at 2r/(1+r): the classic correction for having
    # measured a half of the instrument rather than the instrument.
    return 2 * correlation / (1 + correlation) if correlation > -1 else float("nan")


NULL_DRAWS: Final = 200
NULL_PERCENTILE: Final = 95.0
"""The estimator has a null and it is wide, so every reliability is reported against it.

Measured rather than assumed, because the first version of this module reported reliabilities with
no bar and a pure-noise test then came back at 0.33. It turned out not to be bias -- across two
hundred noise-only realisations the estimator is centred near zero -- but its 95th percentile sits
between 0.33 and 0.41 at these station counts and this record length, and its maximum draw reached
0.56. So a single region reporting 0.40 is not distinguishable from nothing, and a number printed
without that bar invites exactly the reading it cannot support. Phase 3a's chance bar, arriving at a
different quantity for the same reason.
"""


def null_reliability(stations: int, years: int) -> float:
    """What this estimator returns on the same shape of data with no shared signal at all.

    Pure independent noise at the region's own station count and record length, so the bar is the
    bar for *this* region rather than a global constant that flatters the small ones.
    """
    # Keyed by the shape it is a null *for*, so each region's bar is stable no matter which other
    # regions exist or what order they are visited in.
    rng = np.random.default_rng([NULL_SEED, stations, years])
    span = list(range(years))
    draws = []
    for _ in range(NULL_DRAWS):
        members = [
            dict(zip(span, rng.normal(0.0, 1.0, size=years), strict=True)) for _ in range(stations)
        ]
        # Fewer splits than the observed estimate uses: this is a percentile over many draws, so
        # per-draw precision costs more than it buys.
        value = split_half_reliability(members, rng, splits=40)
        if np.isfinite(value):
            draws.append(value)
    return float(np.percentile(draws, NULL_PERCENTILE)) if draws else float("nan")


@dataclass(frozen=True, slots=True)
class RegionFloor:
    """One flyway-and-band: how much its pooled series moves, and how much of that is real."""

    region: str
    stations: int
    years: int
    interannual_sd: float
    reliability: float
    null_threshold: float
    """The 95th percentile of this estimator on pure noise at this region's size."""

    @property
    def above_null(self) -> bool:
        return bool(np.isfinite(self.reliability) and self.reliability > self.null_threshold)


@dataclass(frozen=True, slots=True)
class SeasonFloor:
    """One season's answer to both questions."""

    season: str
    stations: int
    station_sd: float
    """Median per-station interannual sd of passage date, days. The thing to be explained."""
    neighbour_pairs: int
    station_error_bound: float
    """Upper bound on one station's measurement error, days, from neighbour disagreement."""
    regions: list[RegionFloor]

    @property
    def station_ceiling(self) -> float:
        """Lower bound on the share of a single station's variance a driver could reach."""
        if not np.isfinite(self.station_error_bound) or self.station_sd == 0:
            return float("nan")
        return max(0.0, 1.0 - (self.station_error_bound / self.station_sd) ** 2)

    @property
    def pooled_ceiling(self) -> float:
        """Median reliability across the regions that clear their own null.

        Regions below their bar are excluded rather than averaged in: a reliability inside the
        estimator's noise range is not a small ceiling, it is no measurement.
        """
        values = [r.reliability for r in self.regions if r.above_null]
        return float(np.median(values)) if values else float("nan")

    @property
    def regions_above_null(self) -> int:
        return sum(1 for r in self.regions if r.above_null)


def _by_station(panel: pl.DataFrame) -> dict[str, dict[int, float]]:
    return {
        str(name): dict(zip(group["year"].to_list(), group["q50_doy"].to_list(), strict=True))
        for (name,), group in panel.group_by(["station_id"])
    }


def measure(season: str, panel: pl.DataFrame, sites: dict[str, tuple[float, float]]) -> SeasonFloor:
    """Both diagnostics for one season."""
    rng = np.random.default_rng(SEED)
    series = _by_station(panel.filter(pl.col("season") == season))
    usable = {name: s for name, s in series.items() if len(s) >= MIN_YEARS}

    station_sd = float(np.median([np.std(list(s.values()), ddof=1) for s in usable.values()]))

    gaps = []
    names = sorted(usable)
    for index, first in enumerate(names):
        if first not in sites:
            continue
        for second in names[index + 1 :]:
            if second not in sites:
                continue
            if not 0.0 < great_circle_km(*sites[first], *sites[second]) <= NEIGHBOUR_KM:
                continue
            shared = sorted(set(usable[first]) & set(usable[second]))
            if len(shared) < MIN_YEARS:
                continue
            gaps.append(
                float(np.std([usable[first][y] - usable[second][y] for y in shared], ddof=1))
            )
    # Half the difference variance: two independent errors of equal size make a difference of
    # sqrt(2) times one of them.
    bound = float(np.median(gaps)) / np.sqrt(2) if gaps else float("nan")

    grouped: dict[str, list[dict[int, float]]] = {}
    for name, one in usable.items():
        if name not in sites:
            continue
        region = region_of(*sites[name])
        if region:
            grouped.setdefault(region, []).append(one)

    regions = []
    for region, members in sorted(grouped.items()):
        if len(members) < MIN_STATIONS:
            continue
        years = sorted({y for member in members for y in member})
        pooled = pooled_series(members, years)
        finite = np.isfinite(pooled)
        if finite.sum() < MIN_YEARS:
            continue
        regions.append(
            RegionFloor(
                region=region,
                stations=len(members),
                years=int(finite.sum()),
                interannual_sd=float(np.std(pooled[finite], ddof=1)),
                reliability=split_half_reliability(members, rng),
                null_threshold=null_reliability(len(members), int(finite.sum())),
            )
        )

    return SeasonFloor(
        season=season,
        stations=len(usable),
        station_sd=station_sd,
        neighbour_pairs=len(gaps),
        station_error_bound=bound,
        regions=regions,
    )


def collect() -> list[SeasonFloor]:
    """Both seasons. Reads the lake."""
    nights = load_conus_nights()
    panel = passage_quantiles(
        nights,
        spec_for(EvidenceType.FLUX),
        seasons=[SPRING, AUTUMN],
        quantiles=(0.5,),
        min_coverage=MIN_COVERAGE,
        min_observations=MIN_NIGHTS,
    ).drop_nulls("q50_doy")
    sites = {
        str(row["station_id"]): (float(row["lat"]), float(row["lon"]))
        for row in nights.group_by("station_id")
        .agg(lat=pl.col("station_latitude").first(), lon=pl.col("station_longitude").first())
        .to_dicts()
    }
    return [measure(season, panel, sites) for season in ("autumn", "spring")]


def render() -> str:
    out = [
        "The response floor -- what any driver could reach, before choosing one",
        "=" * 92,
        "Characterises the passage-date measurement rather than any relationship. The per-station",
        "figure is a *lower* bound on the ceiling, because neighbour disagreement over 150 km",
        "includes real spatial variation as well as error. The pooled figure is measured by",
        "half-splitting each region's stations, so it assumes nothing about errors being",
        "independent.",
    ]
    for floor in collect():
        out += [
            "",
            "=" * 92,
            f"{floor.season}",
            "=" * 92,
            f"  stations with >= {MIN_YEARS} years        {floor.stations}",
            f"  median per-station interannual sd  {floor.station_sd:.2f} days   (what needs "
            f"explaining)",
            f"  neighbour pairs within {NEIGHBOUR_KM:.0f} km     {floor.neighbour_pairs}",
            f"  upper bound on station error      {floor.station_error_bound:.2f} days",
            f"  => per-station ceiling            {floor.station_ceiling:.0%}  (a lower bound)",
            "",
            f"  {'region':22s} {'stations':>8s} {'years':>6s} {'pooled sd':>10s} "
            f"{'reliability':>12s} {'its bar':>8s}",
        ]
        for region in floor.regions:
            mark = "" if region.above_null else "   below its bar"
            out.append(
                f"  {region.region:22s} {region.stations:8d} {region.years:6d} "
                f"{region.interannual_sd:9.2f}d {region.reliability:12.0%} "
                f"{region.null_threshold:7.0%}{mark}"
            )
        pooled_sd = float(np.median([r.interannual_sd for r in floor.regions]))
        out += [
            "",
            f"  median pooled interannual sd      {pooled_sd:.2f} days",
            f"  regions clearing their own bar    {floor.regions_above_null} of "
            f"{len(floor.regions)}",
            f"  => pooled ceiling                 {floor.pooled_ceiling:.0%}  (median of those)",
        ]

    out += [
        "",
        "=" * 92,
        "how to read this",
        "=" * 92,
        "A ceiling is not a result about birds. It is the share of year-to-year variance that is",
        "shared signal rather than measurement noise, so it is the most any driver could explain",
        "even if it were the true and only cause.",
        "",
        "Where the pooled ceiling clearly exceeds the per-station one, the earlier attempts were",
        "predicting a noisier target than they needed to, and the next one should predict the",
        "pooled series. Where it does not, the year-to-year movement is station-specific, pooling",
        "averages the signal away with the noise, and a better driver is the only route left.",
    ]
    return "\n".join(out)
