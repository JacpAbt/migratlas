"""Phase 3h, per `docs/methods/phase3h-pooled-response.md`: predict a region, not a station.

Three arms, and the ladder climbs one step only. Arm A is Phase 3a's per-station fit and exists to
calibrate the harness. Arm B changes the *response* to the regional mean and nothing else, which is
the one thing Phase 3a, the 3d rehearsal and Phase 3f all held fixed while varying the predictor.
Arm C adds the wind terms Phase 2a fitted and no skill harness in this project has ever seen.

The licence for changing the response is `reports/response_floor.py`: a station's passage date moves
4.37 days between years and up to 3.54 of that is measurement error, so at most a third of it was
ever explainable, while a region's series is 65% shared signal. Every earlier attempt was fitting to
a target that is mostly noise.

The estimator is `models.skill.hindcast` verbatim in every arm -- no pooling, no spline, no new
lambda rule. Phase 3f spent five rungs on estimator complexity and could interpret none of them;
changing the response *and* the estimator would produce a difference nobody could attribute.
"""

import logging
import zlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np

from migratlas.models.skill import Skill, era_split, hindcast
from migratlas.reports.phase1 import load_conus_nights
from migratlas.reports.phase3a import COLUMNS, binomial_bar
from migratlas.reports.phase3f import ALL_COLUMNS, SHARE, WIND, Unit, units
from migratlas.reports.response_floor import MIN_STATIONS, region_of, station_sites

if TYPE_CHECKING:
    from collections.abc import Sequence

log = logging.getLogger(__name__)

SEED: Final = 20260820
"""Registered in the note, named once, and not changed afterwards for any reason."""

PERMUTATIONS: Final = 1000
"""`hindcast`'s own draw count, restated here only so the report can print it."""

PROJECTABLE: Final = COLUMNS
"""Phase 3a's seven, every one of which a climate model can supply for a future year.

Arm C's extra columns are wind terms, which no seasonal forecast supplies skilfully -- so skill
that appears only in the all-drivers column licenses a mechanism claim and not a forecast. Phase
3f's one piece of design that worked exactly as intended.
"""

REGIONAL_COLUMNS: Final = (*COLUMNS, WIND, SHARE)

SEASONS: Final = ("autumn", "spring")

CALIBRATION: Final = {"autumn": 0.0055, "spring": -0.0308}
"""Phase 3a's per-station medians, which arm A must reproduce to three significant figures.

Medians rather than counts, because Phase 3f calibrated on a *seeded* count and fired its own stop
condition when one borderline station crossed the bar between two legitimate seeds. An observed
skill distribution's median does not depend on the seed at all.
"""

CALIBRATION_TOLERANCE: Final = 5e-5
"""Three significant figures on a quantity of order 0.01, which is what the note registered."""

DROPPED_SHOWN: Final = 12
"""How many exclusions are listed before the rest are counted. The count is always printed."""


@dataclass(frozen=True, slots=True)
class Arm:
    """One rung: a response scale and a covariate list, differing from its predecessor in one."""

    key: str
    label: str
    columns: tuple[str, ...]
    regional: bool


LADDER: Final[tuple[Arm, ...]] = (
    Arm("A", "per station, Phase 3a's seven", COLUMNS, regional=False),
    Arm("B", "per region, Phase 3a's seven", COLUMNS, regional=True),
    Arm("C", "per region, + wind support and favourable share", REGIONAL_COLUMNS, regional=True),
)


@dataclass(frozen=True, slots=True)
class ArmResult:
    """One arm on one season and one driver scope."""

    arm: str
    label: str
    season: str
    scope: str
    units: int
    significant: int
    bar: int
    median_skill: float
    skills: dict[str, Skill]


def unit_seed(name: str) -> int:
    """A unit's null stream, keyed to the unit rather than to its position in a list.

    Phase 3f published a null it could not reproduce because one generator served every unit in
    traversal order and the panel's order was not stable. Keying by name makes a unit's null a
    property of that unit, so the table cannot move when the iteration does.
    """
    return SEED ^ zlib.crc32(name.encode("utf-8"))


def regional_units(
    unit_list: Sequence[Unit], sites: dict[str, tuple[float, float]]
) -> tuple[list[Unit], list[str]]:
    """Pool station units into regions: the unweighted mean response and covariates per year.

    Unweighted deliberately. A traffic- or area-weighting is a free parameter, and this phase
    already spends its novelty on the pooling itself. The covariates are pooled the same way as the
    response: the scale-matched choice, a regional response explained by regional drivers.

    A region-year is the mean over whichever member stations reported that year, so the response's
    own error varies across years with the station count. Recorded in the note as a known problem
    rather than corrected, because correcting it needs the weighting scheme just refused.
    """
    grouped: dict[str, list[Unit]] = {}
    dropped: list[str] = []
    for unit in unit_list:
        position = sites.get(unit.station_id)
        if position is None:
            dropped.append(f"{unit.station_id}: no position")
            continue
        region = region_of(*position)
        if region is None:
            dropped.append(f"{unit.station_id}: outside every flyway-and-band cell")
            continue
        grouped.setdefault(region, []).append(unit)

    built: list[Unit] = []
    for region, members in sorted(grouped.items()):
        if len(members) < MIN_STATIONS:
            dropped.append(f"{region}: {len(members)} stations, under the floor of {MIN_STATIONS}")
            continue
        years = sorted({int(year) for member in members for year in member.years.tolist()})
        response, design = [], []
        for year in years:
            present = [
                (member, offset)
                for member in members
                for offset in np.flatnonzero(member.years == year).tolist()
            ]
            response.append(float(np.mean([member.y[offset] for member, offset in present])))
            design.append(
                np.mean(np.vstack([member.x[offset] for member, offset in present]), axis=0)
            )

        split = era_split(len(years))
        if split is None:
            dropped.append(f"{region}: {len(years)} years, under the split's floor")
            continue
        built.append(
            Unit(
                station_id=region,
                season=members[0].season,
                years=np.array(years),
                y=np.array(response, dtype=float),
                x=np.vstack(design).astype(float),
                train=split.train,
                test=split.test,
            )
        )
    return built, sorted(dropped)


def run_arm(arm: Arm, unit_list: Sequence[Unit], season: str, *, scope: str) -> ArmResult:
    """One rung on one driver scope: `hindcast` once per unit, nothing else."""
    columns = tuple(name for name in arm.columns if scope == "all" or name in PROJECTABLE)
    index = [ALL_COLUMNS.index(name) for name in columns]
    log.info(
        "%s arm %s [%s]: %d units, %d columns",
        season,
        arm.key,
        scope,
        len(unit_list),
        len(columns),
    )

    skills: dict[str, Skill] = {}
    for unit in unit_list:
        verdict = hindcast(unit.x[:, index], unit.y, seed=unit_seed(unit.station_id))
        if verdict is not None:
            skills[unit.station_id] = verdict

    scores = [verdict.score for verdict in skills.values()]
    return ArmResult(
        arm=arm.key,
        label=arm.label,
        season=season,
        scope=scope,
        units=len(skills),
        significant=sum(1 for verdict in skills.values() if verdict.significant),
        bar=binomial_bar(len(skills)) if skills else 0,
        median_skill=float(np.median(scores)) if scores else float("nan"),
        skills=skills,
    )


def collect() -> tuple[list[ArmResult], dict[str, list[str]]]:
    """The whole ladder, both seasons, both driver scopes. Reads the lake once per season."""
    sites = station_sites(load_conus_nights())
    results: list[ArmResult] = []
    dropped: dict[str, list[str]] = {}
    for season in SEASONS:
        stations, why = units(season)
        regions, region_why = regional_units(stations, sites)
        dropped[season] = [*why, *region_why]
        for arm in LADDER:
            unit_list = regions if arm.regional else stations
            if not unit_list:
                continue
            for scope in ("all", "projectable"):
                # An arm whose covariates are all projectable is the same fit under both scopes, so
                # it is reported once rather than twice under two names.
                if scope == "projectable" and set(arm.columns) <= set(PROJECTABLE):
                    continue
                results.append(run_arm(arm, unit_list, season, scope=scope))
    return results, dropped


def calibration_verdict(results: Sequence[ArmResult]) -> tuple[bool, list[str]]:
    """Does arm A reproduce Phase 3a's medians? Nothing above it is interpreted if not."""
    lines, passed = [], True
    for season in SEASONS:
        arm_a = next(
            (row for row in results if row.season == season and row.arm == "A"),
            None,
        )
        if arm_a is None:
            passed = False
            lines.append(f"  {season:7s} arm A did not run at all")
            continue
        expected = CALIBRATION[season]
        gap = abs(arm_a.median_skill - expected)
        ok = gap <= CALIBRATION_TOLERANCE
        passed = passed and ok
        lines.append(
            f"  {season:7s} arm A median {arm_a.median_skill:+.4f}  "
            f"registered {expected:+.4f}  {'reproduces' if ok else f'OFF by {gap:.4f}'}"
        )
    return passed, lines


def render() -> str:
    results, dropped = collect()
    calibrated, calibration_lines = calibration_verdict(results)

    out = [
        "Phase 3h -- was the thing being predicted the problem all along?",
        "=" * 92,
        "Pre-registered in docs/methods/phase3h-pooled-response.md. Three arms: A calibrates the",
        "harness against Phase 3a, B changes the response from a station to a region and nothing",
        "else, C adds the wind terms. The estimator is models.skill.hindcast verbatim throughout.",
        "",
        f"Seed {SEED}, keyed per unit by crc32 of its name. {PERMUTATIONS} shuffles each.",
        "",
        "calibration -- arm A must reproduce Phase 3a's medians, or nothing above it is read",
        "-" * 92,
        *calibration_lines,
        "",
    ]

    for season in SEASONS:
        rows = [row for row in results if row.season == season]
        if not rows:
            out += [f"{season}: no units cleared the split", ""]
            continue
        out += [
            "=" * 92,
            season,
            "=" * 92,
            f"  {'arm':4s} {'scope':12s} {'units':>6s} {'signif':>7s} {'bar':>4s} "
            f"{'median skill':>13s}  {'label'}",
        ]
        for row in rows:
            star = "*" if row.significant > row.bar else " "
            out.append(
                f"  {row.arm:4s} {row.scope:12s} {row.units:6d} {row.significant:6d}{star} "
                f"{row.bar:4d} {row.median_skill:+13.4f}  {row.label}"
            )

        arm_a = next((row for row in rows if row.arm == "A"), None)
        arm_b = next((row for row in rows if row.arm == "B"), None)
        if arm_a and arm_b:
            out += [
                "",
                f"  arm B minus arm A: {arm_b.median_skill - arm_a.median_skill:+.4f}"
                "   (registered prediction 2: at least +0.05 in both seasons)",
            ]

        if arm_b:
            out += ["", "  per region, arm B:"]
            for name, verdict in sorted(arm_b.skills.items()):
                mark = "  clears its null" if verdict.significant else ""
                out.append(
                    f"    {name:22s} skill {verdict.score:+.4f}  null 95th "
                    f"{verdict.null_threshold:+.4f}  train {verdict.train_years:2d} "
                    f"test {verdict.test_years:2d}{mark}"
                )
        out.append("")

    for season, why in dropped.items():
        if why:
            out.append(f"dropped in {season}: {len(why)}")
            out += [f"  {line}" for line in why[:DROPPED_SHOWN]]
            if len(why) > DROPPED_SHOWN:
                out.append(f"  ... and {len(why) - DROPPED_SHOWN} more")
            out.append("")

    out += [
        "=" * 92,
        "VERDICT: ladder run; "
        + (
            "arm A calibrated, arms B and C are interpretable"
            if calibrated
            else "ARM A OFF ITS CALIBRATION -- nothing above arm A is interpreted"
        ),
    ]
    return "\n".join(out)
