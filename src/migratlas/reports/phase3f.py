"""Phase 3f: the ladder registered in `docs/methods/phase3f-response.md`.

Phase 3a fitted 143 separate ridges, each on about nineteen training rows against seven covariates,
and found autumn skill at 20 stations and spring at the false-positive rate. At 2.7 rows per
parameter that design returns very little whether or not there is anything there, so "timing is not
predictable" and "this instrument cannot see whether timing is predictable" were never separated.
This module puts the rows together and adds the one driver the hindcast harness never had, one
change per rung so a gain can be attributed to a cause.

Everything reusable is reused: `models.skill` supplies the era split, the Murphy score and the
per-station harness, and `phase3a` supplies the covariate assembly and the chance bar, so the
comparison against its published numbers is a comparison rather than a coincidence.

The pooled fit is closed-form on purpose. Rows are centred *within station* on training-era means,
which puts each station's own climatology in the intercept by construction and leaves the shared
slope vector nothing to explain about why Florida and Minnesota differ in level -- the same
within-station design Phase 2a used. What follows is one ridge solve, plus a leave-one-station-out
pass that is nearly free because dropping a station from a pooled Gram matrix is a subtraction.

Everything is stacked into one array with per-unit slices rather than held as a list of per-unit
blocks. That is not tidiness: the null refits a thousand times, and a spline expansion done once per
draw instead of once per station per draw is the difference between minutes and hours.
"""

import logging
import zlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np
import polars as pl

from migratlas.evidence import EvidenceType, spec_for
from migratlas.metrics.phenology import passage_quantiles
from migratlas.models.skill import Skill, era_split, hindcast, murphy_score
from migratlas.reports.phase1 import AUTUMN, MIN_COVERAGE, MIN_NIGHTS, SPRING, load_conus_nights
from migratlas.reports.phase1_robustness import FLEET_MIDPOINT_YEAR
from migratlas.reports.phase2a_timing import night_winds, support_nights

# The covariate assembly is imported rather than copied, private name and all: the ladder's whole
# claim is that its bottom rung reproduces Phase 3a, and two copies of a join are two things that
# can drift apart.
from migratlas.reports.phase3a import COLUMNS, binomial_bar
from migratlas.reports.phase3a import _covariates as phase3a_covariates

if TYPE_CHECKING:
    from collections.abc import Sequence

log = logging.getLogger(__name__)

# Fixed by the registration, which is the date it landed. Not tuned, not re-rolled.
SEED: Final = 20260819

# Wider than Phase 3a's five values, and the note says why: a ridge penalty competes with the
# number of rows, so a grid fixed for a 14-row fit would test pooling with the regularisation
# effectively switched off.
LAMBDAS: Final = tuple(np.logspace(-2, 4, 13))

PERMUTATIONS: Final = 1000
SIGNIFICANCE_PERCENTILE: Final = 95.0

# Registered: three interior knots at the training-era quartiles, boundary knots at its range.
INTERIOR_QUANTILES: Final = (0.25, 0.50, 0.75)
MIN_KNOTS: Final = 4

# Below this an arm publishes as a coverage statement rather than as a skill result.
MIN_UNITS: Final = 100

WIND: Final = "wind_support"
SHARE: Final = "favourable_share"
POST: Final = "post"
TEMPERATURE: Final = "temp_season"

# Every driver this phase adds is one a seasonal forecast cannot supply, so the projectable subset
# is Phase 3a's own list plus the instrument term -- projectable trivially, being a known constant
# for any future year. The split exists because a mechanism gain silently inflating a forecast
# claim is the failure Phase 3d's refusal was protecting against.
PROJECTABLE: Final = (*COLUMNS, POST)
ALL_COLUMNS: Final = (*COLUMNS, POST, WIND, SHARE)

# A two-valued column has no quartiles to put knots at, so the instrument term stays linear in the
# spline arm. Found while implementing and recorded in the note's amendment rather than silently.
UNSPLINED: Final = (POST,)

SEASONS: Final = {"spring": SPRING, "autumn": AUTUMN}


@dataclass(frozen=True, slots=True)
class Arm:
    """One rung: an estimator and a covariate list, differing from its predecessor in one thing."""

    key: str
    label: str
    columns: tuple[str, ...]
    pooled: bool
    spline: bool = False


LADDER: Final[tuple[Arm, ...]] = (
    Arm("A", "per-station ridge, Phase 3a verbatim", COLUMNS, pooled=False),
    Arm("B", "pooled, + instrument shift", (*COLUMNS, POST), pooled=True),
    Arm("B'", "pooled, no instrument shift", COLUMNS, pooled=True),
    Arm("C", "pooled, + seasonal-mean wind", (*COLUMNS, POST, WIND), pooled=True),
    Arm("D", "pooled, + favourable-night share", ALL_COLUMNS, pooled=True),
    Arm("E", "pooled, spline basis on D", ALL_COLUMNS, pooled=True, spline=True),
)


@dataclass(frozen=True, slots=True)
class Unit:
    """One station-season, rows in year order, and where the era split falls."""

    station_id: str
    season: str
    years: np.ndarray
    y: np.ndarray
    x: np.ndarray
    """One column per `ALL_COLUMNS` entry, in that order."""
    train: np.ndarray
    test: np.ndarray


@dataclass(frozen=True, slots=True)
class ArmResult:
    """One arm's verdict for one season and one driver scope."""

    arm: str
    label: str
    season: str
    scope: str
    """`all` or `projectable`: which driver subset the number was earned with."""
    units: int
    significant: int
    bar: int
    median_skill: float
    ridge_lambda: float
    skills: dict[str, Skill]


def unit_key(station_id: str) -> int:
    """A per-unit null seed that depends on the unit and on nothing else.

    Found by measuring twice: the first run drew every unit's permutations from one generator in
    list order, and `units()` does not return a stable order -- 142 of 143 autumn stations changed
    position between two calls in one process. Observed skill was identical across orders, as it
    must be, and the *null thresholds* were not, so the significant-unit count wobbled by three
    across reruns of the same seed. Keying the stream to the station makes a unit's null a property
    of that unit rather than of the list it arrived in.

    crc32 rather than `hash`, which is salted per process for strings and would reintroduce exactly
    the irreproducibility this closes.
    """
    return zlib.crc32(station_id.encode("utf-8"))


def nightly_support(season_name: str) -> pl.DataFrame:
    """Per-night wind support for one season, from the term Phase 2a registered."""
    season = SEASONS[season_name]
    nights = load_conus_nights(quantity="reflectivity_traffic").filter(
        pl.col("timestamp").dt.ordinal_day().is_between(season.start_doy, season.end_doy),
        pl.col("coverage_fraction") >= MIN_COVERAGE,
        pl.col("direction_deg").is_not_null(),
        pl.col("magnitude") > 0,
    )
    return support_nights(nights, night_winds())


def favourable_share(nightly: pl.DataFrame, train_years: set[int]) -> pl.DataFrame:
    """Share of each year's nights whose support beat the station's training-era median.

    The threshold is per station and drawn from the training era alone, so it needs no arbitrary
    physical constant and cannot read the test years. By construction the share sits near a half in
    training, and what carries information is how far a given year departs from that.

    A station with no training-era nights has no threshold and returns nothing, rather than
    borrowing one from its neighbours.
    """
    train = nightly.filter(pl.col("year").is_in(train_years))
    if train.is_empty():
        return pl.DataFrame()
    threshold = float(np.median(train["support"].to_numpy()))
    return (
        nightly.with_columns(favourable=(pl.col("support") > threshold).cast(pl.Float64))
        .group_by("year")
        .agg(pl.col("favourable").mean().alias(SHARE))
    )


def _panel(season_name: str, nightly: pl.DataFrame) -> pl.DataFrame:
    """Response and every registered covariate except the split-dependent share."""
    quantiles = (
        passage_quantiles(
            load_conus_nights(),
            spec_for(EvidenceType.FLUX),
            seasons=[SPRING, AUTUMN],
            quantiles=(0.5,),
            min_coverage=MIN_COVERAGE,
            min_observations=MIN_NIGHTS,
        )
        .drop_nulls("q50_doy")
        .filter(pl.col("season") == season_name)
    )
    wind = nightly.group_by("station_id", "year").agg(pl.col("support").mean().alias(WIND))
    return (
        quantiles.join(phase3a_covariates(season_name), on=["station_id", "year"])
        .join(wind, on=["station_id", "year"], how="inner")
        .with_columns(pl.col("year").ge(FLEET_MIDPOINT_YEAR).cast(pl.Float64).alias(POST))
    )


def units(season_name: str) -> tuple[list[Unit], list[str]]:
    """Every station-season clearing the era split with every registered column present.

    One unit set for the whole ladder, deliberately. A rung fitted on a different set of stations
    from the rung below would report a difference that was partly the stations, and the ladder's
    only purpose is that each difference means one thing.
    """
    nightly = nightly_support(season_name)
    panel = _panel(season_name, nightly)
    by_station = nightly.partition_by("station_id", as_dict=True, include_key=True)

    built: list[Unit] = []
    dropped: list[str] = []
    for (station,), group in panel.group_by(["station_id"], maintain_order=True):
        name = str(station)
        rows = group.sort("year")
        split = era_split(rows.height)
        if split is None:
            dropped.append(f"{name}: {rows.height} years, under the split's floor")
            continue

        years = rows["year"].to_numpy()
        nights = by_station.get((name,))
        if nights is None:
            dropped.append(f"{name}: no nightly wind")
            continue
        shares = favourable_share(nights, {int(year) for year in years[split.train]})
        if shares.is_empty():
            dropped.append(f"{name}: no training-era nights to take a threshold from")
            continue

        joined = rows.join(shares, on="year", how="left")
        missing = joined[SHARE].null_count()
        if missing:
            dropped.append(f"{name}: {missing} years without a share")
            continue

        built.append(
            Unit(
                station_id=name,
                season=season_name,
                years=years,
                y=joined["q50_doy"].to_numpy().astype(float),
                x=joined.select(ALL_COLUMNS).to_numpy().astype(float),
                train=split.train,
                test=split.test,
            )
        )
    log.info("%s: %d units, %d dropped", season_name, len(built), len(dropped))
    # Sorted, because the panel's row order is not stable across calls and an unsorted table is a
    # table that changes between rebuilds. The fits no longer depend on the order; the report does.
    return sorted(built, key=lambda unit: unit.station_id), sorted(dropped)


def natural_spline(values: np.ndarray, knots: np.ndarray) -> np.ndarray:
    """Natural cubic spline basis, without its intercept column.

    The truncated-power basis of ESL 5.2.1: a linear term plus one column per interior knot, each
    built so the fit is *linear beyond the boundary knots*. That last property is the whole reason
    for a natural spline rather than a plain cubic one here -- the test era is later than the
    training era and may sit outside its range, and an unconstrained cubic extrapolates into
    nonsense exactly there.
    """
    last = float(knots[-1])
    penultimate = float(knots[-2])

    def ramp(cut: float) -> np.ndarray:
        return np.asarray(np.clip(values - cut, 0.0, None) ** 3, dtype=float)

    def difference(cut: float) -> np.ndarray:
        return np.asarray((ramp(cut) - ramp(last)) / (last - cut), dtype=float)

    tail = difference(penultimate)
    columns = [values, *[difference(float(knot)) - tail for knot in knots[:-2]]]
    return np.asarray(np.column_stack(columns), dtype=float)


def spline_knots(column: np.ndarray) -> np.ndarray | None:
    """Boundary knots at the pooled training range, interior ones at its quartiles.

    Pooled rather than per-station: nineteen points do not locate a quartile. Returns None for a
    column with too few distinct values to knot, which the caller leaves linear.
    """
    interior = np.quantile(column, INTERIOR_QUANTILES)
    knots = np.unique(np.concatenate([[column.min()], interior, [column.max()]]))
    return knots if knots.size >= MIN_KNOTS else None


class Pooled:
    """One arm's stacked, within-station-centred design, and the verdicts read off it."""

    def __init__(self, unit_list: Sequence[Unit], columns: Sequence[str], *, spline: bool) -> None:
        self.units = list(unit_list)
        self.columns = list(columns)
        self._spline = spline

        index = [ALL_COLUMNS.index(name) for name in self.columns]
        self._raw = np.vstack([unit.x[:, index] for unit in self.units])
        self._y = np.concatenate([unit.y for unit in self.units])

        offset = 0
        self._rows: list[np.ndarray] = []
        train_parts, test_parts = [], []
        for unit in self.units:
            span = np.arange(offset, offset + unit.y.size)
            self._rows.append(span)
            train_parts.append(span[unit.train])
            test_parts.append(span[unit.test])
            offset += unit.y.size
        self._train = train_parts
        self._test = test_parts
        self._train_all = np.concatenate(train_parts)

        # The response is centred once: the shuffle permutes covariates, never the response, so
        # each unit's training climatology is the same in the observed fit and in every null draw.
        self._climatology = np.array([self._y[rows].mean() for rows in self._train])
        self._y_centred = self._y.copy()
        for position, rows in enumerate(self._rows):
            self._y_centred[rows] -= self._climatology[position]

        centred = self._centre(self._raw)
        self._knot_sets: list[np.ndarray | None] = []
        if spline:
            self._knot_sets = [
                None if name in UNSPLINED else spline_knots(centred[self._train_all, position])
                for position, name in enumerate(self.columns)
            ]
        expanded = self._expand(centred)
        scale = expanded[self._train_all].std(axis=0)
        scale[scale == 0.0] = 1.0
        self._scale: np.ndarray = scale

    def _centre(self, raw: np.ndarray) -> np.ndarray:
        """Subtract each unit's training-era column means from all of its rows."""
        out = raw.copy()
        for rows, train in zip(self._rows, self._train, strict=True):
            out[rows] -= raw[train].mean(axis=0)
        return out

    def _expand(self, centred: np.ndarray) -> np.ndarray:
        """The spline basis, or the columns unchanged. Called once per fit, not once per unit."""
        if not self._spline:
            return centred
        pieces = []
        for position, knots in enumerate(self._knot_sets):
            column = centred[:, position]
            pieces.append(column[:, None] if knots is None else natural_spline(column, knots))
        # The one registered interaction, on the raw centred columns rather than on their bases,
        # so it stays a single column and the design does not explode combinatorially.
        if WIND in self.columns and TEMPERATURE in self.columns:
            wind = centred[:, self.columns.index(WIND)]
            temperature = centred[:, self.columns.index(TEMPERATURE)]
            pieces.append((wind * temperature)[:, None])
        return np.asarray(np.column_stack(pieces), dtype=float)

    def _design(self, raw: np.ndarray) -> np.ndarray:
        return np.asarray(self._expand(self._centre(raw)) / self._scale, dtype=float)

    def _solve(self, design: np.ndarray, lam: float) -> np.ndarray:
        """Ridge with no intercept column: the within-station centring already removed it."""
        x = design[self._train_all]
        gram = x.T @ x
        moment = x.T @ self._y_centred[self._train_all]
        return np.linalg.solve(gram + lam * np.eye(gram.shape[0]), moment)

    def _scores(self, design: np.ndarray, weights: np.ndarray) -> np.ndarray:
        fitted = design @ weights
        return np.array(
            [
                murphy_score(
                    self._y[test],
                    self._climatology[position] + fitted[test],
                    self._climatology[position],
                )
                for position, test in enumerate(self._test)
            ]
        )

    def choose_lambda(self, design: np.ndarray) -> float:
        """Leave-one-station-out over the training era, in closed form.

        Dropping a station from a pooled fit is a subtraction on the Gram matrix, so the pass costs
        one solve per station per lambda rather than a refit. Phase 3a chose lambda by
        leave-one-*year*-out, which is right for a single-station fit and wrong here: with rows
        pooled, the question is whether shared coefficients reach a station the fit has not seen.
        """
        blocks = [design[train] for train in self._train]
        targets = [self._y_centred[train] for train in self._train]
        grams = [block.T @ block for block in blocks]
        moments = [block.T @ target for block, target in zip(blocks, targets, strict=True)]
        total = sum(grams)
        moment = sum(moments)
        eye = np.eye(total.shape[0])

        best, best_error = float(LAMBDAS[0]), np.inf
        for lam in LAMBDAS:
            error = 0.0
            for position, block in enumerate(blocks):
                weights = np.linalg.solve(
                    total - grams[position] + lam * eye, moment - moments[position]
                )
                error += float(np.sum((targets[position] - block @ weights) ** 2))
            if error < best_error:
                best, best_error = float(lam), error
        return best

    def _shuffled(self, generators: list[np.random.Generator]) -> np.ndarray:
        """Each unit's whole record permuted, exactly as `models.skill.hindcast` does it.

        The pairing between a year's drivers and its passage date breaks; both marginals survive;
        and the rows that were test rows stay test rows.

        One generator per unit, keyed by `unit_key`, so the draw a station gets does not depend on
        the order the units arrived in. See that function for what this cost to find.
        """
        out = np.empty_like(self._raw)
        for rows, rng in zip(self._rows, generators, strict=True):
            out[rows] = self._raw[rng.permutation(rows)]
        return out

    def skills(self, *, seed: int) -> tuple[dict[str, Skill], float]:
        """Every unit's verdict, and the lambda they were all fitted under."""
        design = self._design(self._raw)
        lam = self.choose_lambda(design)
        observed = self._scores(design, self._solve(design, lam))

        generators = [
            np.random.default_rng([seed, unit_key(unit.station_id)]) for unit in self.units
        ]
        null = np.empty((PERMUTATIONS, len(self.units)))
        for draw in range(PERMUTATIONS):
            null_design = self._design(self._shuffled(generators))
            null[draw] = self._scores(null_design, self._solve(null_design, lam))
            if draw and draw % 250 == 0:
                log.info("    null draw %d/%d", draw, PERMUTATIONS)

        thresholds = np.percentile(null, SIGNIFICANCE_PERCENTILE, axis=0)
        return {
            unit.station_id: Skill(
                score=float(observed[position]),
                null_threshold=float(thresholds[position]),
                significant=bool(observed[position] > thresholds[position]),
                train_years=len(unit.train),
                test_years=len(unit.test),
                ridge_lambda=lam,
            )
            for position, unit in enumerate(self.units)
        }, lam


def per_station(unit_list: Sequence[Unit], columns: Sequence[str]) -> dict[str, Skill]:
    """Arm A: Phase 3a's own harness, one fit per station, unchanged."""
    index = [ALL_COLUMNS.index(name) for name in columns]
    out: dict[str, Skill] = {}
    for unit in unit_list:
        verdict = hindcast(unit.x[:, index], unit.y, seed=SEED)
        if verdict is not None:
            out[unit.station_id] = verdict
    return out


def run_arm(arm: Arm, unit_list: Sequence[Unit], season: str, *, scope: str) -> ArmResult:
    """One rung, on one driver scope."""
    columns = tuple(name for name in arm.columns if scope == "all" or name in PROJECTABLE)
    log.info("%s arm %s [%s]: %d columns", season, arm.key, scope, len(columns))
    if arm.pooled:
        skills, lam = Pooled(unit_list, columns, spline=arm.spline).skills(seed=SEED)
    else:
        skills, lam = per_station(unit_list, columns), float("nan")

    scores = [verdict.score for verdict in skills.values()]
    return ArmResult(
        arm=arm.key,
        label=arm.label,
        season=season,
        scope=scope,
        units=len(skills),
        significant=sum(1 for verdict in skills.values() if verdict.significant),
        bar=binomial_bar(len(skills)),
        median_skill=float(np.median(scores)) if scores else float("nan"),
        ridge_lambda=lam,
        skills=skills,
    )


def collect() -> tuple[list[ArmResult], dict[str, list[str]]]:
    """The whole ladder, both seasons, both driver scopes. Runs once."""
    results: list[ArmResult] = []
    dropped: dict[str, list[str]] = {}
    for season in SEASONS:
        unit_list, why = units(season)
        dropped[season] = why
        if not unit_list:
            continue
        for arm in LADDER:
            for scope in ("all", "projectable"):
                # For an arm whose covariates are all projectable the two scopes are the same
                # fit, so it is reported once rather than twice under two names.
                if scope == "projectable" and set(arm.columns) <= set(PROJECTABLE):
                    continue
                results.append(run_arm(arm, unit_list, season, scope=scope))
    return results, dropped


def render() -> str:
    results, dropped = collect()
    out = [
        "Phase 3f -- is the ceiling the data, the drivers, or the model?",
        "=" * 98,
        "Pre-registered in docs/methods/phase3f-response.md: the ladder, the pooled estimator, the",
        "two new covariates, the spline basis, the lambda rule and the null were fixed before this",
        "ran. Arm A is a calibration rung -- it must reproduce Phase 3a's 20 of 143 in autumn, or",
        "nothing above it is interpreted.",
        "",
        f"Seed {SEED}. {PERMUTATIONS} year-shuffle draws per unit. Lambda grid "
        f"{LAMBDAS[0]:.2g} to {LAMBDAS[-1]:.2g} in {len(LAMBDAS)} steps.",
    ]

    for season in SEASONS:
        rows = [row for row in results if row.season == season]
        if not rows:
            out += ["", f"{season}: no units cleared the split", ""]
            continue
        out += [
            "",
            "=" * 98,
            season,
            "=" * 98,
            f"  {'arm':4s} {'scope':12s} {'units':>6s} {'signif':>7s} {'bar':>4s} "
            f"{'median':>9s} {'lambda':>9s}  what changed",
        ]
        for row in rows:
            flag = "*" if row.significant > row.bar else " "
            lam = "per-unit" if np.isnan(row.ridge_lambda) else f"{row.ridge_lambda:.3g}"
            floor = "  [UNDER THE UNIT FLOOR]" if row.units < MIN_UNITS else ""
            out.append(
                f" {flag}{row.arm:4s} {row.scope:12s} {row.units:6d} {row.significant:7d} "
                f"{row.bar:4d} {row.median_skill:9.4f} {lam:>9s}  {row.label}{floor}"
            )
        out.append(f"  stations dropped before the ladder: {len(dropped.get(season, []))}")
        out += [f"    {line}" for line in dropped.get(season, [])[:8]]

    out += [
        "",
        "=" * 98,
        "How to read this",
        "=" * 98,
        "A star marks an arm clearing its own binomial chance bar. The ladder *differences* are",
        "the result, not the levels: B-A is pooling, B-B' is the instrument term, C-B is the",
        "wind, D-C is the wind's form, E-D is the model class.",
        "",
        "Only the projectable rows may be cited toward a forecast. The all rows include wind,",
        "which no seasonal forecast supplies, so skill they earn is a mechanism claim.",
    ]
    return "\n".join(out)
